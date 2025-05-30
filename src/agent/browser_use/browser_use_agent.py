from __future__ import annotations

"""Agent implementation for running browser tasks with signal control."""  # (added module docstring describing purpose)

import asyncio
import logging
import os

# from lmnr.sdk.decorators import observe
from browser_use.agent.gif import create_history_gif
from browser_use.agent.service import Agent, AgentHookFunc
from browser_use.agent.views import (
    AgentHistoryList,
    AgentStepInfo,
)
from browser_use.telemetry.views import (
    AgentEndTelemetryEvent,
)
from browser_use.utils import time_execution_async
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SKIP_LLM_API_KEY_VERIFICATION = (
    os.environ.get("SKIP_LLM_API_KEY_VERIFICATION", "false").lower()[0] in "ty1"
)


class BrowserUseAgent(Agent):
    """Agent specializing in browser automation with pause/resume handling."""  # (expanded class docstring)
    @time_execution_async("--run (agent)")
    async def run(
        self,
        max_steps: int = 100,
        on_step_start: AgentHookFunc | None = None,
        on_step_end: AgentHookFunc | None = None,
    ) -> AgentHistoryList:
        """Run the agent until the task completes or a step limit is reached.

        Parameters
        ----------
        max_steps: int
            Maximum number of actions the agent will attempt before giving up.
        on_step_start: AgentHookFunc | None
            Optional callback executed before each step begins.
        on_step_end: AgentHookFunc | None
            Optional callback executed after each step completes.

        Returns
        -------
        AgentHistoryList
            Recorded history of agent steps and outputs.

        Signal handlers allow pausing or stopping with Ctrl+C so the browser
        state remains intact during manual inspection.
        """  # (expanded run docstring with parameters and rationale)

        loop = asyncio.get_event_loop()  # Event loop required for signal handling

        # Set up the Ctrl+C signal handler with callbacks specific to this agent
        from browser_use.utils import SignalHandler

        signal_handler = SignalHandler(
            loop=loop,
            pause_callback=self.pause,
            resume_callback=self.resume,
            custom_exit_callback=None,  # No special cleanup needed on forced exit
            exit_on_second_int=True,
        )
        signal_handler.register()  # Activate registered handlers

        # Wait for verification task to complete if it exists
        if hasattr(self, "_verification_task") and not self._verification_task.done():
            try:
                await self._verification_task
            except Exception:
                # Error already logged in the task
                pass

        try:
            self._log_agent_run()  # Telemetry hook for agent start

            # Execute initial actions if provided
            if self.initial_actions:
                result = await self.multi_act(
                    self.initial_actions, check_for_new_elements=False
                )
                self.state.last_result = result

            for step in range(max_steps):  # Iterate up to the step limit
                # Wait while paused via Ctrl+C
                while self.state.paused:
                    await asyncio.sleep(0.5)
                    if self.state.stopped:
                        break  # Break if user requested stop

                # Check if we should stop due to too many failures
                if self.state.consecutive_failures >= self.settings.max_failures:
                    logger.error(
                        f"❌ Stopping due to {self.settings.max_failures} consecutive failures"
                    )
                    break  # Abort on too many failures

                # Check control flags before each step
                if self.state.stopped:
                    logger.info("Agent stopped")
                    break  # Stop requested externally

                while self.state.paused:
                    await asyncio.sleep(0.2)  # Small delay to prevent CPU spinning
                    if self.state.stopped:  # Allow stopping while paused
                        break

                if on_step_start is not None:
                    await on_step_start(self)  # External callback before step

                step_info = AgentStepInfo(step_number=step, max_steps=max_steps)  # Metadata for this step
                await self.step(step_info)  # Perform single agent action

                if on_step_end is not None:
                    await on_step_end(self)  # Callback after step completes

                if self.state.history.is_done():
                    if self.settings.validate_output and step < max_steps - 1:
                        if not await self._validate_output():
                            continue

                    await self.log_completion()
                    break  # Task completed successfully
            else:
                logger.info("❌ Failed to complete task in maximum steps")  # Step limit reached

            return self.state.history

        except KeyboardInterrupt:
            # Handle direct KeyboardInterrupt just in case signal handler failed
            logger.info(
                "Got KeyboardInterrupt during execution, returning current history"
            )
            return self.state.history

        finally:
            # Unregister signal handlers before cleanup
            signal_handler.unregister()

            self.telemetry.capture(
                AgentEndTelemetryEvent(
                    agent_id=self.state.agent_id,
                    is_done=self.state.history.is_done(),
                    success=self.state.history.is_successful(),
                    steps=self.state.n_steps,
                    max_steps_reached=self.state.n_steps >= max_steps,
                    errors=self.state.history.errors(),
                    total_input_tokens=self.state.history.total_input_tokens(),
                    total_duration_seconds=self.state.history.total_duration_seconds(),
                )
            )

            await self.close()  # Close browser and other resources

            if self.settings.generate_gif:
                output_path: str = "agent_history.gif"
                if isinstance(self.settings.generate_gif, str):
                    output_path = self.settings.generate_gif

                create_history_gif(
                    task=self.task, history=self.state.history, output_path=output_path
                )  # Save GIF summarizing session

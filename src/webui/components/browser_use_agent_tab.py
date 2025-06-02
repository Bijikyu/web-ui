"""
Browser Use Agent Tab - Primary Browser Automation Interface and Execution Engine

This module creates the main user interface for browser automation tasks, serving as
the primary interaction point where users define, execute, and monitor browser automation
workflows. This is the core interface that most users will spend their time with,
making its design and functionality critical for overall user experience and success.

Core Interface Components:
1. Task Definition: Natural language input for describing automation goals
2. Execution Controls: Start, stop, pause, and resume automation tasks
3. Real-time Monitoring: Live progress updates, screenshots, and status information
4. Interactive Assistance: Human-in-the-loop capabilities for complex decision points
5. Result Display: Structured presentation of automation results and extracted data
6. Error Handling: Clear error reporting with suggested remediation steps
7. Session Management: Save, load, and repeat successful automation workflows

Design Philosophy:
- Natural Language First: Users describe tasks in plain English rather than programming syntax
- Visual Feedback: Rich visual indicators of automation progress and current state
- Human-in-the-Loop: Seamless escalation to human assistance when automation needs guidance
- Error Recovery: Graceful handling of failures with options for manual intervention
- Progressive Disclosure: Simple interface for basic tasks, advanced options for complex scenarios
- Real-time Updates: Live feedback keeps users engaged and informed during long-running tasks

Why This Interface is the Application's Center:
This tab represents the primary value proposition of the entire application:
- Task Accessibility: Makes browser automation accessible to non-programmers
- Workflow Efficiency: Reduces complex automation tasks to simple natural language descriptions
- Reliability Monitoring: Provides visibility into automation progress and potential issues
- Human Oversight: Enables human judgment for tasks requiring decision-making
- Result Verification: Allows users to validate automation results and make corrections

Key Technical Challenges Addressed:
1. Asynchronous Execution: Long-running browser tasks without blocking the interface
2. Progress Reporting: Meaningful progress updates for complex, multi-step automations
3. Error Recovery: Graceful handling of network failures, site changes, and unexpected content
4. Resource Management: Efficient browser instance management and cleanup
5. State Persistence: Maintaining task state across browser crashes and restarts
6. User Interaction: Handling user input requests during automated execution
7. Performance Optimization: Balancing automation speed with resource consumption

User Interaction Patterns:
- Task Submission: Users enter natural language task descriptions
- Progress Monitoring: Real-time updates show current automation step and progress
- Intervention Handling: Users respond to agent requests for clarification or assistance
- Result Review: Users examine automation results and provide feedback for improvement
- Workflow Iteration: Users refine and repeat automation tasks based on results

Real-World Usage Scenarios:
- Data Extraction: "Extract product prices from this e-commerce site"
- Form Automation: "Fill out this job application with my resume information"
- Testing Workflows: "Test the checkout process on our website"
- Research Tasks: "Gather contact information from company websites"
- Monitoring Activities: "Check for changes on competitor pricing pages"

Interface State Management:
The tab manages complex state including:
- Current automation task and progress
- Browser instance and automation agent lifecycle
- User interaction requests and responses
- Chat history for context and debugging
- Error states and recovery options
- Resource usage and performance metrics

This interface serves as the bridge between human intent and automated execution,
making its reliability, usability, and performance critical for user success.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import gradio as gr

# from browser_use.agent.service import Agent
from browser_use.agent.views import (
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState
from gradio.components import Component
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContextConfig
from src.controller.custom_controller import CustomController
from src.utils.agent_utils import initialize_llm  #(import initialize_llm utility)
from src.utils.browser_launch import build_browser_launch_options  # // import util for browser launch options
from src.webui.webui_manager import WebuiManager
from src.utils.utils import ensure_dir  # // import directory util
from src.webui.components.browser_settings_tab import close_browser  # // reuse browser closing helper

# Module-level logger for automation task execution and user interaction tracking
# This logging is essential for debugging automation failures and understanding user behavior
# Browser automation can fail in complex ways, requiring detailed execution logging
logger = logging.getLogger(__name__)


# --- Helper Functions --- (Defined at module level)


def _get_config_value(
    webui_manager: WebuiManager,
    comp_dict: Dict[gr.components.Component, Any],
    comp_id_suffix: str,
    default: Any = None,
) -> Any:
    """Safely get value from component dictionary using its ID suffix relative to the tab.

    This helper function abstracts the process of extracting configuration settings
    from a dictionary of UI components, using the component's ID suffix to uniquely
    identify it within the application.  It handles cases where the component might
    not be found, providing a default value and logging a warning to aid debugging.

    Args:
        webui_manager (WebuiManager): The application's central management instance.
        comp_dict (Dict[gr.components.Component, Any]): Dictionary mapping UI components to their values.
        comp_id_suffix (str): The unique identifier suffix for the component within the tab.
        default (Any, optional): The default value to return if the component is not found. Defaults to None.

    Returns:
        Any: The configuration value associated with the component, or the default value if not found.
    """
    # Assumes component ID format is "tab_name.comp_name"
    tab_name = "browser_use_agent"  # Hardcode or derive if needed
    comp_id = f"{tab_name}.{comp_id_suffix}"
    # Need to find the component object first using the ID from the manager
    try:
        comp = webui_manager.get_component_by_id(comp_id)
        return comp_dict.get(comp, default)
    except KeyError:
        # Try accessing settings tabs as well
        for prefix in ["agent_settings", "browser_settings"]:
            try:
                comp_id = f"{prefix}.{comp_id_suffix}"
                comp = webui_manager.get_component_by_id(comp_id)
                return comp_dict.get(comp, default)
            except KeyError:
                continue
        logger.warning(
            f"Component with suffix '{comp_id_suffix}' not found in manager for value lookup."
        )
        return default


def _format_agent_output(model_output: AgentOutput) -> str:
    """Formats AgentOutput for display in the chatbot using JSON.

    This function is responsible for converting the structured output of the agent
    (AgentOutput) into a human-readable JSON format suitable for display within the
    application's chatbot interface.  It handles potential errors during the
    formatting process, providing informative error messages when necessary.

    Args:
        model_output (AgentOutput): The structured output from the agent.

    Returns:
        str: A JSON string representation of the agent's output, formatted for display.
    """
    content = ""
    if model_output:
        try:
            # Directly use model_dump if actions and current_state are Pydantic models
            action_dump = [
                action.model_dump(exclude_none=True) for action in model_output.action
            ]

            state_dump = model_output.current_state.model_dump(exclude_none=True)
            model_output_dump = {
                "current_state": state_dump,
                "action": action_dump,
            }
            # Dump to JSON string with indentation
            json_string = json.dumps(model_output_dump, indent=4, ensure_ascii=False)
            # Wrap in <pre><code> for proper display in HTML
            content = f"<pre><code class='language-json'>{json_string}</code></pre>"

        except AttributeError as ae:
            logger.error(
                f"AttributeError during model dump: {ae}. Check if 'action' or 'current_state' or their items support 'model_dump'."
            )
            content = f"<pre><code>Error: Could not format agent output (AttributeError: {ae}).\nRaw output: {str(model_output)}</code></pre>"
        except Exception as e:
            logger.error(f"Error formatting agent output: {e}", exc_info=True)
            # Fallback to simple string representation on error
            content = f"<pre><code>Error formatting agent output.\nRaw output:\n{str(model_output)}</code></pre>"

    return content.strip()


# --- Updated Callback Implementation ---


async def _handle_new_step(
    webui_manager: WebuiManager, state: BrowserState, output: AgentOutput, step_num: int
):
    """Callback for each step taken by the agent, including screenshot display.

    This asynchronous function serves as a callback that is invoked each time the
    automation agent completes a step in its task execution.  It handles the display
    of screenshots, formatting of agent outputs, and updating the chat history
    within the WebUI.  Error handling ensures that failures in screenshot processing
    or output formatting do not disrupt the overall automation workflow.

    Args:
        webui_manager (WebuiManager): The application's central management instance.
        state (BrowserState): The current state of the browser.
        output (AgentOutput): The output generated by the agent at the current step.
        step_num (int): The step number that was just completed.
    """

    # Use the correct chat history attribute name from the user's code
    if not hasattr(webui_manager, "bu_chat_history"):
        logger.error(
            "Attribute 'bu_chat_history' not found in webui_manager! Cannot add chat message."
        )
        # Initialize it maybe? Or raise an error? For now, log and potentially skip chat update.
        webui_manager.bu_chat_history = []  # Initialize if missing (consider if this is the right place)
        # return # Or stop if this is critical
    logger.info(f"Step {step_num} completed.")  # step numbers now reflect actual agent steps

    # --- Screenshot Handling ---
    screenshot_html = ""
    # Ensure state.screenshot exists and is not empty before proceeding
    # Use getattr for safer access
    screenshot_data = getattr(state, "screenshot", None)
    if screenshot_data:
        try:
            # Basic validation: check if it looks like base64
            if (
                isinstance(screenshot_data, str) and len(screenshot_data) > 100
            ):  # Arbitrary length check
                # *** UPDATED STYLE: Removed centering, adjusted width ***
                img_tag = f'<img src="data:image/jpeg;base64,{screenshot_data}" alt="Step {step_num} Screenshot" style="max-width: 800px; max-height: 600px; object-fit:contain;" />'
                screenshot_html = (
                    img_tag + "<br/>"
                )  # Use <br/> for line break after inline-block image
            else:
                logger.warning(
                    f"Screenshot for step {step_num} seems invalid (type: {type(screenshot_data)}, len: {len(screenshot_data) if isinstance(screenshot_data, str) else 'N/A'})."
                )
                screenshot_html = "**[Invalid screenshot data]**<br/>"

        except Exception as e:
            logger.error(
                f"Error processing or formatting screenshot for step {step_num}: {e}",
                exc_info=True,
            )
            screenshot_html = "**[Error displaying screenshot]**<br/>"
    else:
        logger.debug(f"No screenshot available for step {step_num}.")

    # --- Format Agent Output ---
    formatted_output = _format_agent_output(output)  # Use the updated function

    # --- Combine and Append to Chat ---
    step_header = f"--- **Step {step_num}** ---"
    # Combine header, image (with line break), and JSON block
    final_content = step_header + "<br/>" + screenshot_html + formatted_output

    chat_message = {
        "role": "assistant",
        "content": final_content.strip(),  # Remove leading/trailing whitespace
    }

    # Append to the correct chat history list
    webui_manager.bu_chat_history.append(chat_message)

    await asyncio.sleep(0.05)


def _handle_done(webui_manager: WebuiManager, history: AgentHistoryList):
    """Callback when the agent finishes the task (success or failure).

    This function is called when the automation agent has completed its task,
    regardless of whether the task succeeded or failed. It generates a summary
    of the task execution, including duration, token usage, and any errors encountered,
    and adds this summary to the application's chat history.

    Args:
        webui_manager (WebuiManager): The application's central management instance.
        history (AgentHistoryList): The execution history of the agent's task.
    """
    logger.info(
        f"Agent task finished. Duration: {history.total_duration_seconds():.2f}s, Tokens: {history.total_input_tokens()}"
    )
    final_summary = "**Task Completed**\n"
    final_summary += f"- Duration: {history.total_duration_seconds():.2f} seconds\n"
    final_summary += f"- Total Input Tokens: {history.total_input_tokens()}\n"  # Or total tokens if available

    final_result = history.final_result()
    if final_result:
        final_summary += f"- Final Result: {final_result}\n"

    errors = history.errors()
    if errors and any(errors):
        final_summary += f"- **Errors:**\n```\n{errors}\n```\n"
    else:
        final_summary += "- Status: Success\n"

    webui_manager.bu_chat_history.append(
        {"role": "assistant", "content": final_summary}
    )


async def _ask_assistant_callback(
    webui_manager: WebuiManager, query: str, browser_context: BrowserContext
) -> Dict[str, Any]:
    """Callback triggered by the agent's ask_for_assistant action.

    This asynchronous function is invoked when the automation agent requires human
    assistance to proceed with its task. It adds a message to the chat history
    prompting the user for input, and then waits for the user to provide a response.

    Args:
        webui_manager (WebuiManager): The application's central management instance.
        query (str): The query or request for assistance from the agent.
        browser_context (BrowserContext): The current browser context.

    Returns:
        Dict[str, Any]: A dictionary containing the user's response.
    """
    logger.info("Agent requires assistance. Waiting for user input.")

    if not hasattr(webui_manager, "bu_chat_history"):
        logger.error("Chat history not found in webui_manager during ask_assistant!")  # (replace _chat_history check with bu_chat_history for correct attribute access)
        return {"response": "Internal Error: Cannot display help request."}

    webui_manager.bu_chat_history.append(
        {
            "role": "assistant",
            "content": f"**Need Help:** {query}\nPlease provide information or perform the required action in the browser, then type your response/confirmation below and click 'Submit Response'.",
        }
    )

    # Use state stored in webui_manager
    webui_manager.bu_response_event = asyncio.Event()
    webui_manager.bu_user_help_response = None  # Reset previous response

    try:
        logger.info("Waiting for user response event...")
        await asyncio.wait_for(
            webui_manager.bu_response_event.wait(), timeout=3600.0
        )  # Long timeout
        logger.info("User response event received.")
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for user assistance.")
        webui_manager.bu_chat_history.append(
            {
                "role": "assistant",
                "content": "**Timeout:** No response received. Trying to proceed.",
            }
        )
        webui_manager.bu_response_event = None  # Clear the event
        return {"response": "Timeout: User did not respond."}  # Inform the agent

    response = webui_manager.bu_user_help_response
    webui_manager.bu_chat_history.append(
        {"role": "user", "content": response}
    )  # Show user response in chat
    webui_manager.bu_response_event = (
        None  # Clear the event for the next potential request
    )
    return {"response": response}


# --- Core Agent Execution Logic --- (Needs access to webui_manager)


async def run_agent_task(
    webui_manager: WebuiManager, components: Dict[gr.components.Component, Any]
) -> AsyncGenerator[Dict[gr.components.Component, Any], None]:  # used as callback for Run button, yields UI updates
    """Handles the entire lifecycle of initializing and running the agent.

    This asynchronous generator function manages the complete execution cycle of the
    automation agent, from initialization to completion. It retrieves configuration
    settings from the UI, initializes the agent, runs the automation task, and
    streams updates back to the UI in real-time. It also handles pausing, stopping,
    and error recovery during the automation process.

    Args:
        webui_manager (WebuiManager): The application's central management instance.
        components (Dict[gr.components.Component, Any]): A dictionary of UI components and their current values.

    Yields:
        AsyncGenerator[Dict[gr.components.Component, Any], None]: A dictionary of UI component updates to be applied.
    """

    # --- Get Components ---
    # Need handles to specific UI components to update them
    user_input_comp = webui_manager.get_component_by_id("browser_use_agent.user_input")
    run_button_comp = webui_manager.get_component_by_id("browser_use_agent.run_button")
    stop_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.stop_button"
    )
    pause_resume_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.pause_resume_button"
    )
    clear_button_comp = webui_manager.get_component_by_id(
        "browser_use_agent.clear_button"
    )
    chatbot_comp = webui_manager.get_component_by_id("browser_use_agent.chatbot")
    history_file_comp = webui_manager.get_component_by_id(
        "browser_use_agent.agent_history_file"
    )
    gif_comp = webui_manager.get_component_by_id("browser_use_agent.recording_gif")
    browser_view_comp = webui_manager.get_component_by_id(
        "browser_use_agent.browser_view"
    )

    # --- 1. Get Task and Initial UI Update ---
    task = components.get(user_input_comp, "").strip()
    if not task:
        gr.Warning("Please enter a task.")
        yield {run_button_comp: gr.update(interactive=True)}
        return

    mcp_server_config_comp = webui_manager.id_to_component.get(  #(description of change & current functionality)
        "agent_settings.mcp_server_config"  #(description of change & current functionality)
    )
    mcp_server_config_str = (  #(description of change & current functionality)
        components.get(mcp_server_config_comp) if mcp_server_config_comp else None
    )
    if mcp_server_config_str:  #(description of change & current functionality)
        try:  #(description of change & current functionality)
            mcp_server_config = json.loads(mcp_server_config_str)  #(description of change & current functionality)
        except json.JSONDecodeError:  #(description of change & current functionality)
            err_msg = "**Setup Error:** invalid MCP config"  #(description of change & current functionality)
            yield {  #(description of change & current functionality)
                run_button_comp: gr.Button(interactive=True),  #(description of change & current functionality)
                chatbot_comp: gr.update(value=[{"role": "assistant", "content": err_msg}]),  #(description of change & current functionality)
            }
            return  #(description of change & current functionality)
    else:  #(description of change & current functionality)
        mcp_server_config = None  #(description of change & current functionality)

    # Set running state indirectly via _current_task
    webui_manager.bu_chat_history.append({"role": "user", "content": task})

    yield {
        user_input_comp: gr.Textbox(
            value="", interactive=False, placeholder="Agent is running..."
        ),
        run_button_comp: gr.Button(value="⏳ Running...", interactive=False),
        stop_button_comp: gr.Button(interactive=True),
        pause_resume_button_comp: gr.Button(value="⏸️ Pause", interactive=True),
        clear_button_comp: gr.Button(interactive=False),
        chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
        history_file_comp: gr.update(value=None),
        gif_comp: gr.update(value=None),
    }

    # --- Agent Settings ---
    # Access settings values using WebuiManager helper

    override_system_prompt = webui_manager.get_component_value(components, "agent_settings", "override_system_prompt") or None
    extend_system_prompt = webui_manager.get_component_value(components, "agent_settings", "extend_system_prompt") or None
    llm_provider_name = webui_manager.get_component_value(components, "agent_settings", "llm_provider", None)  # Default to None if not found
    llm_model_name = webui_manager.get_component_value(components, "agent_settings", "llm_model_name", None)
    llm_temperature = webui_manager.get_component_value(components, "agent_settings", "llm_temperature", 0.6)
    use_vision = webui_manager.get_component_value(components, "agent_settings", "use_vision", True)
    ollama_num_ctx = webui_manager.get_component_value(components, "agent_settings", "ollama_num_ctx", 16000)
    llm_base_url = webui_manager.get_component_value(components, "agent_settings", "llm_base_url") or None
    llm_api_key = webui_manager.get_component_value(components, "agent_settings", "llm_api_key") or None
    max_steps = webui_manager.get_component_value(components, "agent_settings", "max_steps", 100)
    max_actions = webui_manager.get_component_value(components, "agent_settings", "max_actions", 10)
    max_input_tokens = webui_manager.get_component_value(components, "agent_settings", "max_input_tokens", 128000)
    tool_calling_str = webui_manager.get_component_value(components, "agent_settings", "tool_calling_method", "auto")
    tool_calling_method = tool_calling_str if tool_calling_str != "None" else None
    mcp_server_config_comp = webui_manager.id_to_component.get(
        "agent_settings.mcp_server_config"
    )
    mcp_server_config_str = (
        components.get(mcp_server_config_comp) if mcp_server_config_comp else None
    )  #(description of change & current functionality)
    if mcp_server_config_str:  #(description of change & current functionality)
        try:  #(description of change & current functionality)
            mcp_server_config = json.loads(mcp_server_config_str)  #(description of change & current functionality)
        except json.JSONDecodeError:  #(description of change & current functionality)
            err_msg = "**Setup Error:** invalid MCP config"  #(description of change & current functionality)
            webui_manager.bu_chat_history.append({"role": "assistant", "content": err_msg})  #(description of change & current functionality)
            yield {
                run_button_comp: gr.Button(interactive=True),  #(description of change & current functionality)
                chatbot_comp: gr.update(value=webui_manager.bu_chat_history),  #(description of change & current functionality)
            }
            return  #(description of change & current functionality)
    else:  #(description of change & current functionality)
        mcp_server_config = None  #(description of change & current functionality)

    # Planner LLM Settings (Optional)
    planner_llm_provider_name = webui_manager.get_component_value(components, "agent_settings", "planner_llm_provider") or None
    planner_llm = None
    if planner_llm_provider_name:
        planner_llm_model_name = webui_manager.get_component_value(components, "agent_settings", "planner_llm_model_name")
        planner_llm_temperature = webui_manager.get_component_value(components, "agent_settings", "planner_llm_temperature", 0.6)
        planner_ollama_num_ctx = webui_manager.get_component_value(components, "agent_settings", "planner_ollama_num_ctx", 16000)
        planner_llm_base_url = webui_manager.get_component_value(components, "agent_settings", "planner_llm_base_url") or None
        planner_llm_api_key = webui_manager.get_component_value(components, "agent_settings", "planner_llm_api_key") or None
        planner_use_vision = webui_manager.get_component_value(components, "agent_settings", "planner_use_vision", False)

        planner_llm = await initialize_llm(  #(use shared initialize_llm utility)
            planner_llm_provider_name,
            planner_llm_model_name,
            planner_llm_temperature,
            planner_llm_base_url,
            planner_llm_api_key,
            planner_ollama_num_ctx if planner_llm_provider_name == "ollama" else None,
        )

    # --- Browser Settings ---
    # Access browser settings using WebuiManager helper

    browser_binary_path = webui_manager.get_component_value(components, "browser_settings", "browser_binary_path") or None
    browser_user_data_dir = webui_manager.get_component_value(components, "browser_settings", "browser_user_data_dir") or None
    use_own_browser = webui_manager.get_component_value(
        components, "browser_settings", "use_own_browser", False
    )  # Logic handled by CDP/WSS presence
    keep_browser_open = webui_manager.get_component_value(components, "browser_settings", "keep_browser_open", False)
    headless = webui_manager.get_component_value(components, "browser_settings", "headless", False)
    disable_security = webui_manager.get_component_value(components, "browser_settings", "disable_security", True)
    window_w = int(webui_manager.get_component_value(components, "browser_settings", "window_w", 1280))
    window_h = int(webui_manager.get_component_value(components, "browser_settings", "window_h", 1100))
    cdp_url = webui_manager.get_component_value(components, "browser_settings", "cdp_url") or None
    wss_url = webui_manager.get_component_value(components, "browser_settings", "wss_url") or None
    save_recording_path = webui_manager.get_component_value(components, "browser_settings", "save_recording_path") or None
    save_trace_path = webui_manager.get_component_value(components, "browser_settings", "save_trace_path") or None
    save_agent_history_path = webui_manager.get_component_value(
        components, "browser_settings", "save_agent_history_path", "./tmp/agent_history"
    )
    save_download_path = webui_manager.get_component_value(components, "browser_settings", "save_download_path", "./tmp/downloads")

    stream_vw = 70
    stream_vh = int(70 * window_h // window_w) if window_w else 0  # // default stream height to 0 when width is 0

    ensure_dir(save_agent_history_path)  # // ensure save history path
    if save_recording_path:
        ensure_dir(save_recording_path)  # // ensure recording path
    if save_trace_path:
        ensure_dir(save_trace_path)  # // ensure trace path
    if save_download_path:
        ensure_dir(save_download_path)  # // ensure download path

    # --- 2. Initialize LLM ---
    main_llm = await initialize_llm(  #(use shared initialize_llm utility)
        llm_provider_name,
        llm_model_name,
        llm_temperature,
        llm_base_url,
        llm_api_key,
        ollama_num_ctx if llm_provider_name == "ollama" else None,
    )

    if main_llm is None:  # // check that llm initialization succeeded
        err_msg = "**Setup Error:** LLM initialization failed"  # // error text for chatbot
        webui_manager.bu_chat_history.append({"role": "assistant", "content": err_msg})  # // log error to chat history
        yield {  # // reset UI buttons on init failure
            run_button_comp: gr.Button(value="▶️ Submit Task", interactive=True),  # // enable run button
            stop_button_comp: gr.Button(interactive=False),  # // disable stop button
            pause_resume_button_comp: gr.Button(interactive=False),  # // disable pause/resume
            clear_button_comp: gr.Button(interactive=False),  # // disable clear to avoid wiping history accidentally
            chatbot_comp: gr.update(value=webui_manager.bu_chat_history),  # // display error message
        }
        return  # // abort run when llm is missing

    # Pass the webui_manager instance to the callback when wrapping it
    async def ask_callback_wrapper(
        query: str, browser_context: BrowserContext
    ) -> Dict[str, Any]:  # thin wrapper to inject manager instance
        return await _ask_assistant_callback(webui_manager, query, browser_context)

    if not webui_manager.bu_controller:
        webui_manager.bu_controller = CustomController(
            ask_assistant_callback=ask_callback_wrapper  # controller uses wrapper for user prompts
        )
        await webui_manager.bu_controller.setup_mcp_client(mcp_server_config)

    # --- 4. Initialize Browser and Context ---
    should_close_browser_on_finish = not keep_browser_open

    try:
        # Close existing resources if not keeping open
        if not keep_browser_open:
            if webui_manager.bu_browser_context:
                logger.info("Closing previous browser context.")
                await webui_manager.bu_browser_context.close()
                webui_manager.bu_browser_context = None
            if webui_manager.bu_browser:
                logger.info("Closing previous browser.")
                await webui_manager.bu_browser.close()
                webui_manager.bu_browser = None

        # Create Browser if needed
        if not webui_manager.bu_browser:
            logger.info("Launching new browser instance.")
            browser_config = {  # // create config dictionary
                "window_width": window_w,
                "window_height": window_h,
                "user_data_dir": browser_user_data_dir,
                "use_own_browser": use_own_browser,
                "browser_binary_path": browser_binary_path,
            }
            browser_binary_path, extra_args = build_browser_launch_options(
                browser_config
            )  # // use util to build launch options
            webui_manager.bu_browser = CustomBrowser(
                config=BrowserConfig(
                    headless=headless,
                    disable_security=disable_security,
                    browser_binary_path=browser_binary_path,
                    extra_browser_args=extra_args,
                    wss_url=wss_url,
                    cdp_url=cdp_url,
                )
            )

        # Create Context if needed
        if not webui_manager.bu_browser_context:
            logger.info("Creating new browser context.")
            context_config = CustomBrowserContextConfig(
                trace_path=save_trace_path if save_trace_path else None,
                save_recording_path=save_recording_path
                if save_recording_path
                else None,
                save_downloads_path=save_download_path if save_download_path else None,
               window_width=window_w,
               window_height=window_h,
            )
            if not webui_manager.bu_browser:
                raise ValueError("Browser not initialized, cannot create context.")
            webui_manager.bu_browser_context = (
                await webui_manager.bu_browser.new_context(config=context_config)
            )

        # --- 5. Initialize or Update Agent ---
        webui_manager.bu_agent_task_id = str(uuid.uuid4())  # New ID for this task run
        ensure_dir(
            os.path.join(save_agent_history_path, webui_manager.bu_agent_task_id)
        )  # // ensure history task dir
        history_file = os.path.join(
            save_agent_history_path,
            webui_manager.bu_agent_task_id,
            f"{webui_manager.bu_agent_task_id}.json",
        )
        gif_path = os.path.join(
            save_agent_history_path,
            webui_manager.bu_agent_task_id,
            f"{webui_manager.bu_agent_task_id}.gif",
        )  # // path for generated GIF

    except Exception as e:  # // capture any setup errors
        logger.error(f"run_agent_task encountered error: {e}", exc_info=True)
        return

    # --- 6. Construct and run the agent ---  #(create agent and set callbacks)
    step_cb = lambda s, o, n: asyncio.create_task(  #(async step handling)
        _handle_new_step(webui_manager, s, o, n)
    )
    done_cb = lambda h: _handle_done(webui_manager, h)  #(final history summary)

    webui_manager.bu_agent = BrowserUseAgent(  # store agent instance for control
        task=task,
        llm=main_llm,
        browser=webui_manager.bu_browser,
        browser_context=webui_manager.bu_browser_context,
        controller=webui_manager.bu_controller,
        use_vision=use_vision,
        register_new_step_callback=step_cb,
        register_done_callback=done_cb,
    )

    agent_coro = webui_manager.bu_agent.run(max_steps=max_steps)  # create run coroutine
    task_handle = asyncio.create_task(agent_coro)  # schedule agent execution
    webui_manager.bu_current_task = task_handle  # track running task

    try:
        while not task_handle.done():
            await asyncio.sleep(0.1)
            yield {chatbot_comp: gr.update(value=webui_manager.bu_chat_history)}
        history = await task_handle
    finally:
        webui_manager.bu_current_task = None

    webui_manager.bu_agent.save_history(history_file)  # save history file

    if should_close_browser_on_finish:  # close browser if not keeping open
        await close_browser(webui_manager)

    yield {  # final UI state after run completes
        run_button_comp: gr.Button(value="▶️ Submit Task", interactive=True),
        stop_button_comp: gr.Button(interactive=False),
        pause_resume_button_comp: gr.Button(interactive=False),
        clear_button_comp: gr.Button(interactive=True),
        chatbot_comp: gr.update(value=webui_manager.bu_chat_history),
        history_file_comp: gr.update(value=history_file),
        gif_comp: gr.update(value=gif_path if os.path.exists(gif_path) else None),
    }

    return


async def handle_submit(webui_manager: WebuiManager, components: Dict[Component, Any]) -> AsyncGenerator[Dict[Component, Any], None]:
    """Launch the agent when not already running."""  # ensures only one task at a time
    if webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        yield {}
        return
    async for update in run_agent_task(webui_manager, components):
        yield update


async def handle_pause_resume(webui_manager: WebuiManager) -> Dict[Component, Any]:
    """Toggle the pause state of the running agent."""  # modifies pause button label
    pause_button = webui_manager.get_component_by_id("browser_use_agent.pause_resume_button")
    agent = webui_manager.bu_agent
    task = webui_manager.bu_current_task
    if not agent or not task or task.done():
        return {}
    if getattr(agent.state, "paused", False):
        agent.resume()
        return {pause_button: gr.update(value="⏸️ Pause", interactive=True)}
    agent.pause()
    return {pause_button: gr.update(value="▶️ Resume", interactive=True)}


async def handle_stop(webui_manager: WebuiManager) -> Dict[Component, Any]:
    """Stop the running agent and disable controls."""  # updates buttons when stopping
    run_button = webui_manager.get_component_by_id("browser_use_agent.run_button")
    stop_button = webui_manager.get_component_by_id("browser_use_agent.stop_button")
    pause_button = webui_manager.get_component_by_id("browser_use_agent.pause_resume_button")
    clear_button = webui_manager.get_component_by_id("browser_use_agent.clear_button")
    agent = webui_manager.bu_agent
    task = webui_manager.bu_current_task
    if agent and task and not task.done():
        agent.stop()
        return {
            stop_button: gr.update(interactive=False, value="⏹️ Stopping..."),
            pause_button: gr.update(interactive=False),
            run_button: gr.update(interactive=False),
        }
    return {
        run_button: gr.update(interactive=True),
        stop_button: gr.update(interactive=False),
        pause_button: gr.update(interactive=False),
        clear_button: gr.update(interactive=True),
    }


async def handle_clear(webui_manager: WebuiManager) -> Dict[Component, Any]:
    """Clear chat, cancel tasks and reset browser state."""  # resets all runtime info
    if webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        webui_manager.bu_current_task.cancel()
    await close_browser(webui_manager)
    if getattr(webui_manager, "bu_controller", None):
        await webui_manager.bu_controller.close_mcp_client()  # close remote client before reset
    webui_manager.bu_agent = None
    webui_manager.bu_controller = None  # drop controller after closing client
    webui_manager.bu_current_task = None
    webui_manager.bu_chat_history = []
    webui_manager.bu_response_event = None
    webui_manager.bu_user_help_response = None
    webui_manager.bu_agent_task_id = None
    run_button = webui_manager.get_component_by_id("browser_use_agent.run_button")
    stop_button = webui_manager.get_component_by_id("browser_use_agent.stop_button")
    pause_button = webui_manager.get_component_by_id("browser_use_agent.pause_resume_button")
    clear_button = webui_manager.get_component_by_id("browser_use_agent.clear_button")
    chatbot = webui_manager.get_component_by_id("browser_use_agent.chatbot")
    history_file = webui_manager.get_component_by_id("browser_use_agent.agent_history_file")
    gif = webui_manager.get_component_by_id("browser_use_agent.recording_gif")
    browser_view = webui_manager.get_component_by_id("browser_use_agent.browser_view")
    return {
        run_button: gr.update(value="▶️ Submit Task", interactive=True),
        stop_button: gr.update(interactive=False),
        pause_button: gr.update(interactive=False),
        clear_button: gr.update(interactive=True),
        chatbot: gr.update(value=[]),
        history_file: gr.update(value=None),
        gif: gr.update(value=None),
        browser_view: gr.update(value=None),
    }


async def handle_help_submit(webui_manager: WebuiManager, text: str) -> Dict[Component, Any]:  # // new handler for user help responses
    """Store help response and trigger waiting event."""  # // explain behavior
    webui_manager.bu_user_help_response = text  # // save response text
    event = getattr(webui_manager, "bu_response_event", None)  # // get waiting event if exists
    if event:  # // ensure event exists
        event.set()  # // resume ask_assistant callback
    help_input = webui_manager.get_component_by_id("browser_use_agent.help_response_input")  # // get textbox component
    return {help_input: gr.update(value="")}  # // clear the textbox after submit


def create_browser_use_agent_tab(webui_manager: WebuiManager):
    """Create the main browser use agent tab UI."""  # builds and wires components
    tab_components = {}
    with gr.Row():
        user_input = gr.Textbox(label="Task", lines=2, interactive=True)
        with gr.Column(scale=1):
            run_button = gr.Button("▶️ Submit Task", variant="primary")
            stop_button = gr.Button("⏹️ Stop", variant="stop", interactive=False)
            pause_button = gr.Button("⏸️ Pause", interactive=False)
            clear_button = gr.Button("Clear")
    help_input = gr.Textbox(label="Help Response", lines=2, interactive=True)  # // input for manual agent help
    help_button = gr.Button("Submit Response")  # // button submits help text
    chatbot = gr.Chatbot()
    browser_view = gr.HTML()
    history_file = gr.File(interactive=False)
    gif = gr.Image(interactive=False)
    tab_components.update(
        dict(
            user_input=user_input,
            run_button=run_button,
            stop_button=stop_button,
            pause_resume_button=pause_button,
            clear_button=clear_button,
            chatbot=chatbot,
            browser_view=browser_view,
            agent_history_file=history_file,
            recording_gif=gif,
            help_response_input=help_input,  # // register help response textbox
            help_submit_button=help_button,  # // register help submit button
        )
    )
    webui_manager.add_components("browser_use_agent", tab_components)
    webui_manager.init_browser_use_agent()

    tab_outputs = list(tab_components.values())
    all_inputs = list(webui_manager.get_components())  # // keep order for correct value mapping

    async def submit_wrapper(*vals) -> AsyncGenerator[Dict[Component, Any], None]:  # // build comps dict from ordered values
        comps = dict(zip(all_inputs, vals))  # // map components to values for handler
        async for upd in handle_submit(webui_manager, comps):
            yield upd

    run_button.click(submit_wrapper, inputs=all_inputs, outputs=tab_outputs)
    user_input.submit(submit_wrapper, inputs=all_inputs, outputs=tab_outputs)

    async def pause_wrapper() -> Dict[Component, Any]:
        return await handle_pause_resume(webui_manager)

    pause_button.click(pause_wrapper, outputs=[pause_button])

    async def stop_wrapper() -> Dict[Component, Any]:
        return await handle_stop(webui_manager)

    stop_button.click(stop_wrapper, outputs=tab_outputs)

    async def clear_wrapper() -> Dict[Component, Any]:
        return await handle_clear(webui_manager)

    clear_button.click(clear_wrapper, outputs=tab_outputs)

    async def help_wrapper(text: str) -> Dict[Component, Any]:
        return await handle_help_submit(webui_manager, text)  # // call help handler

    help_button.click(help_wrapper, inputs=[help_input], outputs=[help_input])  # // bind button to handler
    help_input.submit(help_wrapper, inputs=[help_input], outputs=[help_input])  # // submit on enter


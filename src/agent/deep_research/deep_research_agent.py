"""
Deep Research Agent - Specialized Browser Automation for Comprehensive Research

This module implements a sophisticated research automation system that extends
basic browser automation capabilities to conduct multi-faceted research tasks.
It orchestrates complex research workflows, manages parallel data gathering,
and generates structured reports from diverse web sources.

Key Design Principles:
- Workflow-based execution: Research follows structured phases (planning, gathering, analysis)
- Parallel processing: Multiple research queries execute simultaneously for efficiency
- State persistence: Research progress is saved to enable recovery from interruptions  
- Modular architecture: Each research phase is independently testable and maintainable
- Error resilience: Robust handling of network failures and site access issues

Why a specialized research agent vs. generic browser automation:
- Research requires structured planning and iterative refinement of search strategies
- Academic and business research needs citation tracking and source verification
- Long-running research tasks need progress persistence and resumption capabilities
- Research outputs require specific formatting and organization for downstream use
- Quality assessment of sources requires domain-specific evaluation criteria

The agent operates through distinct phases:
1. Planning Phase: Analyze research topic and generate targeted search strategies
2. Gathering Phase: Execute searches across multiple sources in parallel
3. Analysis Phase: Process, synthesize, and structure collected information
4. Reporting Phase: Generate formatted reports with citations and source verification

This architecture enables handling research tasks that may take hours to complete
while providing progress visibility and the ability to resume interrupted work.
"""
# The workflow flows through planning -> execution -> synthesis  #// clarifies overall flow

import asyncio
import json
import logging
import os
import threading
from src.utils.utils import ensure_dir  # // directory helper import
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from browser_use.browser.browser import BrowserConfig
from langchain_community.tools.file_management import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)

# Langchain imports
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool, Tool

# Langgraph imports
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContextConfig
from src.controller.custom_controller import CustomController
from src.utils.mcp_client import setup_mcp_client_and_tools
from src.utils.browser_launch import build_browser_launch_options  # import util for browser launch options
from src.utils.browser_cleanup import close_browser_resources  # reuse util for closing browser

# Configure logger for this module with research-specific context
# Using module-level logger enables fine-grained control over research operation logging
# This is essential for debugging long-running research tasks and tracking progress
logger = logging.getLogger(__name__)

# Constants
REPORT_FILENAME = "report.md"
PLAN_FILENAME = "research_plan.md"
SEARCH_INFO_FILENAME = "search_info.json"

_AGENT_STOP_FLAGS = {}
_BROWSER_AGENT_INSTANCES = {}


async def run_single_browser_task(
    task_query: str,
    task_id: str,
    llm: Any,  # Pass the main LLM
    browser_config: Dict[str, Any],
    stop_event: threading.Event,
    use_vision: bool = False,
) -> Dict[str, Any]:
    """Launch a headless browser session for one search query."""  #// clarifies role
    if not BrowserUseAgent:
        return {
            "query": task_query,
            "error": "BrowserUseAgent components not available.",
        }

    # --- Browser Setup ---
    # These should ideally come from the main agent's config
    headless = browser_config.get("headless", False)
    window_w = browser_config.get("window_width", 1280)
    window_h = browser_config.get("window_height", 1100)
    browser_binary_path = browser_config.get("browser_binary_path", None)
    wss_url = browser_config.get("wss_url", None)
    cdp_url = browser_config.get("cdp_url", None)
    disable_security = browser_config.get("disable_security", False)

    bu_browser = None
    bu_browser_context = None
    try:
        logger.info(f"Starting browser task for query: {task_query}")
        browser_binary_path, extra_args = build_browser_launch_options(browser_config)  # handles user data dir and custom browser

        bu_browser = CustomBrowser(
            config=BrowserConfig(
                headless=headless,
                disable_security=disable_security,
                browser_binary_path=browser_binary_path,
                extra_browser_args=extra_args,
                wss_url=wss_url,
                cdp_url=cdp_url,
            )
        )

        context_config = CustomBrowserContextConfig(
            save_downloads_path="./tmp/downloads",
            window_width=window_w,
            window_height=window_h,
            force_new_context=True,
        )
        bu_browser_context = await bu_browser.new_context(config=context_config)

        # Simple controller example, replace with your actual implementation if needed
        bu_controller = CustomController()

        # Construct the task prompt for BrowserUseAgent
        # Instruct it to find specific info and return title/URL
        bu_task_prompt = f"""
        Research Task: {task_query}
        Objective: Find relevant information answering the query.
        Output Requirements: For each relevant piece of information found, please provide:
        1. A concise summary of the information.
        2. The title of the source page or document.
        3. The URL of the source.
        Focus on accuracy and relevance. Avoid irrelevant details.
        PDF cannot directly extract _content, please try to download first, then using read_file, if you can't save or read, please try other methods.
        """

        bu_agent_instance = BrowserUseAgent(
            task=bu_task_prompt,
            llm=llm,  # Use the passed LLM
            browser=bu_browser,
            browser_context=bu_browser_context,
            controller=bu_controller,
            use_vision=use_vision,
            source="webui",
        )

        # Store instance for potential stop() call
        task_key = f"{task_id}_{uuid.uuid4()}"
        _BROWSER_AGENT_INSTANCES[task_key] = bu_agent_instance

        # --- Run with Stop Check ---
        # BrowserUseAgent needs to internally check a stop signal or have a stop method.
        # We simulate checking before starting and assume `run` might be interruptible
        # or have its own stop mechanism we can trigger via bu_agent_instance.stop().
        if stop_event.is_set():
            logger.info(f"Browser task for '{task_query}' cancelled before start.")
            return {"query": task_query, "result": None, "status": "cancelled"}

        # The run needs to be awaitable and ideally accept a stop signal or have a .stop() method
        # result = await bu_agent_instance.run(max_steps=max_steps) # Add max_steps if applicable
        # Let's assume a simplified run for now
        logger.info(f"Running BrowserUseAgent for: {task_query}")
        result = await bu_agent_instance.run()  # Assuming run is the main method
        logger.info(f"BrowserUseAgent finished for: {task_query}")

        final_data = result.final_result()

        if stop_event.is_set():
            logger.info(f"Browser task for '{task_query}' stopped during execution.")
            return {"query": task_query, "result": final_data, "status": "stopped"}  #// early termination info
        else:
            logger.info(f"Browser result for '{task_query}': {final_data}")
            return {"query": task_query, "result": final_data, "status": "completed"}  #// success result for caller

    except Exception as e:
        logger.error(
            f"Error during browser task for query '{task_query}': {e}", exc_info=True
        )
        return {"query": task_query, "error": str(e), "status": "failed"}  #// communicates error back
    finally:
        await close_browser_resources(  # close resources via util
            bu_browser,
            bu_browser_context,
        )

        if task_key in _BROWSER_AGENT_INSTANCES:
            del _BROWSER_AGENT_INSTANCES[task_key]


class BrowserSearchInput(BaseModel):
    queries: List[str] = Field(
        description="List of distinct search queries to find information relevant to the research task."
    )


async def _run_browser_search_tool(
    queries: List[str],
    task_id: str,  # Injected dependency
    llm: Any,  # Injected dependency
    browser_config: Dict[str, Any],
    stop_event: threading.Event,
    max_parallel_browsers: int = 1,
) -> List[Dict[str, Any]]:
    """Run multiple browser tasks concurrently and return their results."""  #// describes concurrency strategy

    # Limit queries just in case LLM ignores the description
    queries = queries[:max_parallel_browsers]
    logger.info(
        f"[Browser Tool {task_id}] Running search for {len(queries)} queries: {queries}"
    )

    results = []  #// holds individual query results
    semaphore = asyncio.Semaphore(max_parallel_browsers)

    async def task_wrapper(query):
        async with semaphore:
            if stop_event.is_set():
                logger.info(
                    f"[Browser Tool {task_id}] Skipping task due to stop signal: {query}"
                )
                return {"query": query, "result": None, "status": "cancelled"}
            # Pass necessary injected configs and the stop event
            return await run_single_browser_task(
                query,
                task_id,
                llm,  # Pass the main LLM (or a dedicated one if needed)
                browser_config,
                stop_event,
                # use_vision could be added here if needed
            )

    tasks = [task_wrapper(query) for query in queries]  #// launch concurrent tasks
    search_results = await asyncio.gather(*tasks, return_exceptions=True)  #// wait for all searches

    processed_results = []  #// normalized list of tool outputs
    for i, res in enumerate(search_results):
        query = queries[i]  # Get corresponding query
        if isinstance(res, Exception):
            logger.error(
                f"[Browser Tool {task_id}] Gather caught exception for query '{query}': {res}",
                exc_info=True,
            )
            processed_results.append(
                {"query": query, "error": str(res), "status": "failed"}
            )
        elif isinstance(res, dict):
            processed_results.append(res)
        else:
            logger.error(
                f"[Browser Tool {task_id}] Unexpected result type for query '{query}': {type(res)}"
            )
            processed_results.append(
                {"query": query, "error": "Unexpected result type", "status": "failed"}
            )

    logger.info(
        f"[Browser Tool {task_id}] Finished search. Results count: {len(processed_results)}"
    )
    return processed_results  #// send results back to execution node


def create_browser_search_tool(
    llm: Any,
    browser_config: Dict[str, Any],
    task_id: str,
    stop_event: threading.Event,
    max_parallel_browsers: int = 1,
) -> StructuredTool:
    """Return a StructuredTool wired with config and stop controls."""  #// explains binding
    # Use partial to bind the dependencies that aren't part of the LLM call arguments
    from functools import partial

    bound_tool_func = partial(
        _run_browser_search_tool,
        task_id=task_id,
        llm=llm,
        browser_config=browser_config,
        stop_event=stop_event,
        max_parallel_browsers=max_parallel_browsers,
    )  #// partial binds runtime dependencies

    return StructuredTool.from_function(  #// yields tool usable by LLM
        coroutine=bound_tool_func,
        name="parallel_browser_search",
        description=f"""Use this tool to actively search the web for information related to a specific research task or question.
It runs up to {max_parallel_browsers} searches in parallel using a browser agent for better results than simple scraping.
Provide a list of distinct search queries(up to {max_parallel_browsers}) that are likely to yield relevant information.""",
        args_schema=BrowserSearchInput,
    )


# --- Langgraph State Definition ---


class ResearchPlanItem(TypedDict):
    step: int
    task: str
    status: str  # "pending", "completed", "failed"
    queries: Optional[List[str]]  # Queries generated for this task
    result_summary: Optional[str]  # Optional brief summary after execution


class DeepResearchState(TypedDict):
    task_id: str
    topic: str
    research_plan: List[ResearchPlanItem]
    search_results: List[Dict[str, Any]]  # Stores results from browser_search_tool_func
    # messages: Sequence[BaseMessage] # History for ReAct-like steps within nodes
    llm: Any  # The LLM instance
    tools: List[Tool]
    output_dir: Path
    browser_config: Dict[str, Any]
    final_report: Optional[str]
    current_step_index: int  # To track progress through the plan
    stop_requested: bool  # Flag to signal termination
    # Add other state variables as needed
    error_message: Optional[str]  # To store errors

    messages: List[BaseMessage]


# --- Langgraph Nodes ---


def _load_previous_state(task_id: str, output_dir: str) -> Dict[str, Any]:  #// restores workflow from disk
    """Loads state from files if they exist."""
    state_updates = {}
    plan_file = os.path.join(output_dir, PLAN_FILENAME)
    search_file = os.path.join(output_dir, SEARCH_INFO_FILENAME)
    if os.path.exists(plan_file):
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                # Basic parsing, assumes markdown checklist format
                plan = []
                step = 1
                for line in f:
                    line = line.strip()
                    if line.startswith(("- [x]", "- [ ]")):
                        status = "completed" if line.startswith("- [x]") else "pending"
                        task = line[5:].strip()
                        plan.append(
                            ResearchPlanItem(
                                step=step,
                                task=task,
                                status=status,
                                queries=None,
                                result_summary=None,
                            )
                        )
                        step += 1
                state_updates["research_plan"] = plan
                # Determine next step index based on loaded plan
                next_step = next(
                    (i for i, item in enumerate(plan) if item["status"] == "pending"),
                    len(plan),
                )
                state_updates["current_step_index"] = next_step
                logger.info(
                    f"Loaded research plan from {plan_file}, next step index: {next_step}"
                )
        except Exception as e:
            logger.error(f"Failed to load or parse research plan {plan_file}: {e}")
            state_updates["error_message"] = f"Failed to load research plan: {e}"
    if os.path.exists(search_file):
        try:
            with open(search_file, "r", encoding="utf-8") as f:
                state_updates["search_results"] = json.load(f)
                logger.info(f"Loaded search results from {search_file}")
        except Exception as e:
            logger.error(f"Failed to load search results {search_file}: {e}")
            state_updates["error_message"] = f"Failed to load search results: {e}"
            # Decide if this is fatal or if we can continue without old results

    return state_updates


def _save_plan_to_md(plan: List[ResearchPlanItem], output_dir: str):  #// persists plan steps
    """Saves the research plan to a markdown checklist file."""
    plan_file = os.path.join(output_dir, PLAN_FILENAME)
    try:
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write("# Research Plan\n\n")
            for item in plan:
                marker = "- [x]" if item["status"] == "completed" else "- [ ]"
                f.write(f"{marker} {item['task']}\n")
        logger.info(f"Research plan saved to {plan_file}")
    except Exception as e:
        logger.error(f"Failed to save research plan to {plan_file}: {e}")


def _save_search_results_to_json(results: List[Dict[str, Any]], output_dir: str):  #// stores gathered data
    """Appends or overwrites search results to a JSON file."""
    search_file = os.path.join(output_dir, SEARCH_INFO_FILENAME)
    try:
        # Simple overwrite for now, could be append
        with open(search_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Search results saved to {search_file}")
    except Exception as e:
        logger.error(f"Failed to save search results to {search_file}: {e}")


def _save_report_to_md(report: str, output_dir: Path):  #// persists final synthesis
    """
    Saves the final research report to a markdown file in the specified output directory.

    This function handles the final step of the research process by persisting the
    generated report to disk. Markdown format is chosen for its readability,
    widespread support, and easy conversion to other formats.

    Args:
        report (str): The complete research report content in markdown format
        output_dir (Path): Directory where the report file should be saved

    Why this approach:
    - Markdown format ensures human readability and easy conversion
    - UTF-8 encoding supports international characters and symbols
    - Exception handling prevents crashes while providing diagnostic information
    - Separate function allows for easy testing and potential format extensions

    Error handling:
    - Catches all exceptions to prevent research pipeline failures
    - Logs errors with specific file paths for debugging
    - Continues execution even if file writing fails
    """
    report_file = os.path.join(output_dir, REPORT_FILENAME)
    try:
        # Use UTF-8 encoding to support international characters and symbols
        # This is crucial for research reports that may contain diverse content
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Final report saved to {report_file}")
    except Exception as e:
        # Log error but don't raise - report generation shouldn't fail due to file I/O
        logger.error(f"Failed to save final report to {report_file}: {e}")


async def planning_node(state: DeepResearchState) -> Dict[str, Any]:  #// builds or reloads plan
    """
    Core planning node for the deep research agent workflow.

    This function serves as the strategic brain of the research process, either
    generating a new research plan or resuming with an existing one. It's designed
    to handle both fresh research starts and recovery from interrupted sessions.

    Args:
        state (DeepResearchState): Current workflow state containing:
                                 - llm: Language model for plan generation
                                 - topic: Research subject
                                 - research_plan: Existing plan (if resuming)
                                 - search_results: Previous results (if any)
                                 - output_dir: Directory for saving files
                                 - stop_requested: Emergency stop flag

    Returns:
        Dict[str, Any]: Updated state with research plan and any status changes

    Why this design:
    - Async function supports long-running LLM operations without blocking
    - State-based architecture allows for workflow resumption and error recovery
    - Early exit on stop_requested prevents resource waste during cancellation
    - Separate handling for new vs. existing plans provides flexibility
    - File persistence ensures plans survive process restarts

    Plan generation vs. resumption logic:
    - New plans: Generated from scratch using LLM with topic context
    - Existing plans: Reused for consistency, with potential for future LLM review
    - This approach balances efficiency (reuse) with adaptability (potential updates)
    """
    logger.info("--- Entering Planning Node ---")

    # Check for cancellation request early to avoid unnecessary work
    # This is essential for responsive user experience during long research sessions
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping planning.")
        return {"stop_requested": True}

    # Extract required state components
    # These assignments make the code more readable and catch missing state early
    llm = state["llm"]
    topic = state["topic"]
    existing_plan = state.get("research_plan")
    existing_results = state.get("search_results")
    output_dir = state["output_dir"]

    # Handle resumption scenario: existing plan with progress made
    # This branch handles recovery from interrupted research sessions
    if existing_plan and state.get("current_step_index", 0) > 0:
        logger.info("Resuming with existing plan.")

        # TODO: Future enhancement - LLM could review and adapt existing plan
        # based on existing_results to optimize remaining research steps
        # For now, we maintain consistency by reusing the original plan

        # Ensure plan is persisted to disk for reference and debugging
        _save_plan_to_md(existing_plan, output_dir)

        # Return existing plan to continue workflow from where it left off
        return {"research_plan": existing_plan}

    # Generate new research plan for fresh research topics
    logger.info(f"Generating new research plan for topic: {topic}")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a meticulous research assistant. Your goal is to create a step-by-step research plan to thoroughly investigate a given topic.
        The plan should consist of clear, actionable research tasks or questions. Each step should logically build towards a comprehensive understanding.
        Format the output as a numbered list. Each item should represent a distinct research step or question.
        Example:
        1. Define the core concepts and terminology related to [Topic].
        2. Identify the key historical developments of [Topic].
        3. Analyze the current state-of-the-art and recent advancements in [Topic].
        4. Investigate the major challenges and limitations associated with [Topic].
        5. Explore the future trends and potential applications of [Topic].
        6. Summarize the findings and draw conclusions.

        Keep the plan focused and manageable. Aim for 5-10 detailed steps.
        """,
            ),
            ("human", f"Generate a research plan for the topic: {topic}"),
        ]
    )

    try:
        response = await llm.ainvoke(prompt.format_prompt(topic=topic).to_messages())
        plan_text = response.content

        # Parse the numbered list into the plan structure
        new_plan: List[ResearchPlanItem] = []
        for i, line in enumerate(plan_text.strip().split("\n")):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith(("*", "-"))):
                # Simple parsing: remove number/bullet and space
                task_text = (
                    line.split(".", 1)[-1].strip()
                    if line[0].isdigit()
                    else line[1:].strip()
                )
                if task_text:
                    new_plan.append(
                        ResearchPlanItem(
                            step=i + 1,
                            task=task_text,
                            status="pending",
                            queries=None,
                            result_summary=None,
                        )
                    )

        if not new_plan:
            logger.error("LLM failed to generate a valid plan structure.")
            return {"error_message": "Failed to generate research plan structure."}

        logger.info(f"Generated research plan with {len(new_plan)} steps.")
        _save_plan_to_md(new_plan, output_dir)

        return {
            "research_plan": new_plan,
            "current_step_index": 0,  # Start from the beginning
            "search_results": [],  # Initialize search results
        }

    except Exception as e:
        logger.error(f"Error during planning: {e}", exc_info=True)
        return {"error_message": f"LLM Error during planning: {e}"}


async def research_execution_node(state: DeepResearchState) -> Dict[str, Any]:  #// drives each research step
    """
    Executes the next step in the research plan by invoking the LLM with tools.
    The LLM decides which tool (e.g., browser search) to use and provides arguments.
    """
    logger.info("--- Entering Research Execution Node ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping research execution.")
        return {
            "stop_requested": True,
            "current_step_index": state["current_step_index"],
        }  # Keep index same

    plan = state["research_plan"]
    current_index = state["current_step_index"]
    llm = state["llm"]
    tools = state["tools"]  # Tools are now passed in state
    output_dir = str(state["output_dir"])
    task_id = state["task_id"]
    # Stop event is bound inside the tool function, no need to pass directly here

    if not plan or current_index >= len(plan):
        logger.info("Research plan complete or empty.")
        # This condition should ideally be caught by `should_continue` before reaching here
        return {}

    current_step = plan[current_index]
    if current_step["status"] == "completed":
        logger.info(f"Step {current_step['step']} already completed, skipping.")
        return {"current_step_index": current_index + 1}  # Move to next step

    logger.info(
        f"Executing research step {current_step['step']}: {current_step['task']}"
    )

    # Bind tools to the LLM for this call
    llm_with_tools = llm.bind_tools(tools)
    if state["messages"]:
        current_task_message = [
            HumanMessage(
                content=f"Research Task (Step {current_step['step']}): {current_step['task']}"
            )
        ]
        invocation_messages = state["messages"] + current_task_message
    else:
        current_task_message = [
            SystemMessage(
                content="You are a research assistant executing one step of a research plan. Use the available tools, especially the 'parallel_browser_search' tool, to gather information needed for the current task. Be precise with your search queries if using the browser tool."
            ),
            HumanMessage(
                content=f"Research Task (Step {current_step['step']}): {current_step['task']}"
            ),
        ]
        invocation_messages = current_task_message

    try:
        # Invoke the LLM, expecting it to make a tool call
        logger.info(f"Invoking LLM with tools for task: {current_step['task']}")
        ai_response: BaseMessage = await llm_with_tools.ainvoke(invocation_messages)
        logger.info("LLM invocation complete.")

        tool_results = []
        executed_tool_names = []

        if not isinstance(ai_response, AIMessage) or not ai_response.tool_calls:
            # LLM didn't call a tool. Maybe it answered directly? Or failed?
            logger.warning(
                f"LLM did not call any tool for step {current_step['step']}. Response: {ai_response.content[:100]}..."
            )
            # How to handle this? Mark step as failed? Or store the content?
            # Let's mark as failed for now, assuming a tool was expected.
            current_step["status"] = "failed"
            current_step["result_summary"] = "LLM did not use a tool as expected."
            _save_plan_to_md(plan, output_dir)
            return {
                "research_plan": plan,
                "current_step_index": current_index + 1,
                "error_message": f"LLM failed to call a tool for step {current_step['step']}.",
            }

        # Process tool calls
        for tool_call in ai_response.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id")  # Important for ToolMessage

            logger.info(f"LLM requested tool call: {tool_name} with args: {tool_args}")
            executed_tool_names.append(tool_name)

            # Find the corresponding tool instance
            selected_tool = next((t for t in tools if t.name == tool_name), None)

            if not selected_tool:
                logger.error(f"LLM called tool '{tool_name}' which is not available.")
                # Create a ToolMessage indicating the error
                tool_results.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found.",
                        tool_call_id=tool_call_id,
                    )
                )
                continue  # Skip to next tool call if any

            # Execute the tool
            try:
                # Stop check before executing the tool (tool itself also checks)
                stop_event = _AGENT_STOP_FLAGS.get(task_id)
                if stop_event and stop_event.is_set():
                    logger.info(f"Stop requested before executing tool: {tool_name}")
                    current_step["status"] = "pending"  # Not completed due to stop
                    _save_plan_to_md(plan, output_dir)
                    return {"stop_requested": True, "research_plan": plan}

                logger.info(f"Executing tool: {tool_name}")
                # Assuming tool functions handle async correctly
                tool_output = await selected_tool.ainvoke(tool_args)
                logger.info(f"Tool '{tool_name}' executed successfully.")
                browser_tool_called = "parallel_browser_search" in executed_tool_names
                # Append result to overall search results
                current_search_results = state.get("search_results", [])
                if browser_tool_called:  # Specific handling for browser tool output
                    current_search_results.extend(tool_output)
                else:  # Handle other tool outputs (e.g., file tools return strings)
                    # Store it associated with the step? Or a generic log?
                    # Let's just log it for now. Need better handling for diverse tool outputs.
                    logger.info(
                        f"Result from tool '{tool_name}': {str(tool_output)[:200]}..."
                    )

                # Store result for potential next LLM call (if we were doing multi-turn)
                tool_results.append(
                    ToolMessage(
                        content=json.dumps(tool_output), tool_call_id=tool_call_id
                    )
                )

            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                tool_results.append(
                    ToolMessage(
                        content=f"Error executing tool {tool_name}: {e}",
                        tool_call_id=tool_call_id,
                    )
                )
                # Also update overall state search_results with error?
                current_search_results = state.get("search_results", [])
                current_search_results.append(
                    {
                        "tool_name": tool_name,
                        "args": tool_args,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        # Basic check: Did the browser tool run at all? (More specific checks needed)
        browser_tool_called = "parallel_browser_search" in executed_tool_names
        # We might need a more nuanced status based on the *content* of tool_results
        step_failed = (
            any("Error:" in str(tr.content) for tr in tool_results)
            or not browser_tool_called
        )

        if step_failed:
            logger.warning(
                f"Step {current_step['step']} failed or did not yield results via browser search."
            )
            current_step["status"] = "failed"
            current_step["result_summary"] = (
                f"Tool execution failed or browser tool not used. Errors: {[tr.content for tr in tool_results if 'Error' in str(tr.content)]}"
            )
        else:
            logger.info(
                f"Step {current_step['step']} completed using tool(s): {executed_tool_names}."
            )
            current_step["status"] = "completed"

            current_step["result_summary"] = (
                f"Executed tool(s): {', '.join(executed_tool_names)}."
            )

        _save_plan_to_md(plan, output_dir)
        _save_search_results_to_json(current_search_results, output_dir)

        return {
            "research_plan": plan,
            "search_results": current_search_results,  # Update with new results
            "current_step_index": current_index + 1,
            "messages": state["messages"]
            + current_task_message
            + [ai_response]
            + tool_results,
            # Optionally return the tool_results messages if needed by downstream nodes
        }

    except Exception as e:
        logger.error(
            f"Unhandled error during research execution node for step {current_step['step']}: {e}",exc_info=True,
        )
        current_step["status"] = "failed"
        _save_plan_to_md(plan, output_dir)
        return {
            "research_plan": plan,
            "current_step_index": current_index + 1,  # Move on even if error?
            "error_message": f"Core Execution Error on step {current_step['step']}: {e}",
        }


async def synthesis_node(state: DeepResearchState) -> Dict[str, Any]:  #// compiles final report
    """Synthesizes the final report from the collected search results."""
    logger.info("--- Entering Synthesis Node ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping synthesis.")
        return {"stop_requested": True}

    llm = state["llm"]
    topic = state["topic"]
    search_results = state.get("search_results", [])
    output_dir = state["output_dir"]
    plan = state["research_plan"]  # Include plan for context

    if not search_results:
        logger.warning("No search results found to synthesize report.")
        report = f"# Research Report: {topic}\n\nNo information was gathered during the research process."
        _save_report_to_md(report, output_dir)
        return {"final_report": report}

    logger.info(
        f"Synthesizing report from {len(search_results)} collected search result entries."
    )

    # Prepare context for the LLM
    # Format search results nicely, maybe group by query or original plan step
    formatted_results = ""
    references = {}
    ref_count = 1
    for i, result_entry in enumerate(search_results):
        query = result_entry.get("query", "Unknown Query")
        status = result_entry.get("status", "unknown")
        result_data = result_entry.get(
            "result"
        )  # This should be the dict with summary, title, url
        error = result_entry.get("error")

        if status == "completed" and result_data:
            summary = result_data
            formatted_results += f'### Finding from Query: "{query}"\n'
            formatted_results += f"- **Summary:**\n{summary}\n"
            formatted_results += "---\n"

        elif status == "failed":
            formatted_results += f'### Failed Query: "{query}"\n'
            formatted_results += f"- **Error:** {error}\n"
            formatted_results += "---\n"
        # Ignore cancelled/other statuses for the report content

    # Prepare the research plan context
    plan_summary = "\nResearch Plan Followed:\n"
    for item in plan:
        marker = (
            "- [x]"
            if item["status"] == "completed"
            else "- [ ] (Failed)"
            if item["status"] == "failed"
            else "- [ ]"
        )
        plan_summary += f"{marker} {item['task']}\n"

    synthesis_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a professional researcher tasked with writing a comprehensive and well-structured report based on collected findings.
        The report should address the research topic thoroughly, synthesizing the information gathered from various sources.
        Structure the report logically:
        1.  **Introduction:** Briefly introduce the topic and the report's scope (mentioning the research plan followed is good).
        2.  **Main Body:** Discuss the key findings, organizing them thematically or according to the research plan steps. Analyze, compare, and contrast information from different sources where applicable. **Crucially, cite your sources using bracketed numbers [X] corresponding to the reference list.**
        3.  **Conclusion:** Summarize the main points and offer concluding thoughts or potential areas for further research.

        Ensure the tone is objective, professional, and analytical. Base the report **strictly** on the provided findings. Do not add external knowledge. If findings are contradictory or incomplete, acknowledge this.
        """,
            ),
            (
                "human",
                f"""
        **Research Topic:** {topic}

        {plan_summary}

        **Collected Findings:**
        ```
        {formatted_results}
        ```  # end markdown block for results
        """  # closes prompt string
            ),  # closes human message tuple
        ]  # closes messages list
    )  # create ChatPromptTemplate
    try:  # start llm invocation
        ai_response: BaseMessage = await llm.ainvoke(  # get synthesis from llm
            synthesis_prompt.format_prompt(  # fill template
                topic=topic,  # provide topic
                plan_summary=plan_summary,  # include plan summary
                formatted_results=formatted_results,  # include gathered findings
            ).to_messages()  # convert to messages
        )  # invoke llm
        report = ai_response.content  # capture report text
        _save_report_to_md(report, output_dir)  # save report to file
        return {"final_report": report}  # return final report
    except Exception as e:  # catch invocation errors
        logger.error(f"Error during synthesis: {e}", exc_info=True)  # log error details
        return {"error_message": f"Synthesis failed: {e}"}  # return error message

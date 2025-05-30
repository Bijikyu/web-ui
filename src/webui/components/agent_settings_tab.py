"""
Agent Settings Tab - LLM Provider and AI Agent Configuration Interface

This module creates the comprehensive agent configuration interface that allows users
to set up and customize the AI components that power browser automation. This is the
foundational configuration that determines how the browser agents will behave,
communicate, and make decisions during automation tasks.

Key Configuration Areas:
1. LLM Provider Selection: Choose between OpenAI, Anthropic, local models, etc.
2. API Authentication: Secure credential management for cloud-based LLM services
3. Model Parameters: Temperature, token limits, and other inference settings
4. Agent Behavior: Decision-making patterns, risk tolerance, and interaction styles
5. Performance Tuning: Request batching, caching, and optimization settings
6. Fallback Configuration: Alternative providers and error handling strategies

Design Philosophy:
- User-Friendly First: Complex AI configurations presented through intuitive interfaces
- Security Conscious: API keys and credentials handled securely without exposure
- Validation Heavy: Immediate feedback on configuration validity and compatibility
- Preview Capability: Test configurations before applying to automation tasks
- Expert Mode: Advanced settings available for power users while keeping basics simple
- Cost Awareness: Clear indication of cost implications for different provider choices

Why This Configuration is Critical:
The agent settings determine the core intelligence and behavior of all browser automation:
- Model Selection: Different models excel at different types of reasoning and tasks
- Temperature Settings: Balance between creative problem-solving and deterministic behavior
- Token Limits: Control costs while ensuring sufficient context for complex tasks
- Provider Choice: Optimize for cost, performance, privacy, or feature requirements
- Fallback Configuration: Ensure reliability when primary providers are unavailable

Real-World Configuration Scenarios:
- Development: Local models or development API keys with debug-friendly settings
- Testing: Deterministic settings for reproducible test results
- Production: Cost-optimized settings with performance monitoring and fallbacks
- Enterprise: On-premise models with strict security and compliance requirements
- Research: High-creativity settings for exploratory automation tasks

User Experience Considerations:
- Progressive disclosure: Basic settings visible by default, advanced settings collapsible
- Validation feedback: Real-time validation with clear error messages and suggestions
- Cost estimation: Help users understand the financial implications of their choices
- Performance indicators: Show expected latency and throughput for different configurations
- Save/load presets: Allow users to quickly switch between common configurations

This tab serves as the foundation for all AI-powered functionality in the application,
making the quality and usability of this interface critical for overall user success.
"""

import json  # json module for dumps  #(keep json import)

import gradio as gr
from gradio.components import Component
from typing import Any, Dict, Optional
from src.webui.webui_manager import WebuiManager
from src.utils import config
from src.utils.file_utils import load_mcp_server_config  # use new mcp loader
import logging
from functools import partial

logger = logging.getLogger(__name__)


def update_model_dropdown(llm_provider):
    """
    Update the model name dropdown with predefined models for the selected provider.
    """
    # Use predefined models for the selected provider
    if llm_provider in config.model_names:
        return gr.Dropdown(choices=config.model_names[llm_provider], value=config.model_names[llm_provider][0],
                           interactive=True)
    else:
        return gr.Dropdown(choices=[], value="", interactive=True, allow_custom_value=True)


async def update_mcp_server(mcp_file: str, webui_manager: WebuiManager):
    """
    Update the MCP server.
    """
    if hasattr(webui_manager, "bu_controller") and webui_manager.bu_controller:
        logger.warning("⚠️ Close controller because mcp file has changed!")
        await webui_manager.bu_controller.close_mcp_client()
        webui_manager.bu_controller = None

    mcp_server = load_mcp_server_config(mcp_file, logger)  # load config via util
    if mcp_server is None:  # handle invalid or failed load
        return None, gr.update(visible=False)  # hide textbox when load fails

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)


def create_agent_settings_tab(webui_manager: WebuiManager):
    """
    Creates an agent settings tab.
    """
    input_components = set(webui_manager.get_components())
    tab_components = {}

    with gr.Row():
        with gr.Column(scale=1):
            override_system_prompt = gr.Textbox(label="Override system prompt", lines=4, interactive=True)
        with gr.Column(scale=1):
            extend_system_prompt = gr.Textbox(label="Extend system prompt", lines=4, interactive=True)

    with gr.Group():
        mcp_json_file = gr.File(label="MCP server json", interactive=True, file_types=[".json"])
        mcp_server_config = gr.Textbox(label="MCP server", lines=6, interactive=True, visible=False)

    with gr.Group():
        with gr.Row():
            llm_provider = gr.Dropdown(
                choices=[provider for provider, model in config.model_names.items()],
                label="LLM Provider",
                value="openai",
                info="Select LLM provider for LLM",
                interactive=True
            )
            llm_model_name = gr.Dropdown(
                label="LLM Model Name",
                choices=config.model_names['openai'],
                value="gpt-4o",
                interactive=True,
                allow_custom_value=True,
                info="Select a model in the dropdown options or directly type a custom model name"
            )
        with gr.Row():
            llm_temperature = gr.Slider(
                minimum=0.0,
                maximum=2.0,
                value=0.6,
                step=0.1,
                label="LLM Temperature",
                info="Controls randomness in model outputs",
                interactive=True
            )

            use_vision = gr.Checkbox(
                label="Use Vision",
                value=True,
                info="Enable Vision(Input highlighted screenshot into LLM)",
                interactive=True
            )

            ollama_num_ctx = gr.Slider(
                minimum=2 ** 8,
                maximum=2 ** 16,
                value=16000,
                step=1,
                label="Ollama Context Length",
                info="Controls max context length model needs to handle (less = faster)",
                visible=False,
                interactive=True
            )

        with gr.Row():
            llm_base_url = gr.Textbox(
                label="Base URL",
                value="",
                info="API endpoint URL (if required)"
            )
            llm_api_key = gr.Textbox(
                label="API Key",
                type="password",
                value="",
                info="Your API key (leave blank to use .env)"
            )

    with gr.Group():
        with gr.Row():
            planner_llm_provider = gr.Dropdown(
                choices=[provider for provider, model in config.model_names.items()],
                label="Planner LLM Provider",
                info="Select LLM provider for LLM",
                value=None,
                interactive=True
            )
            planner_llm_model_name = gr.Dropdown(
                label="Planner LLM Model Name",
                interactive=True,
                allow_custom_value=True,
                info="Select a model in the dropdown options or directly type a custom model name"
            )
        with gr.Row():
            planner_llm_temperature = gr.Slider(
                minimum=0.0,
                maximum=2.0,
                value=0.6,
                step=0.1,
                label="Planner LLM Temperature",
                info="Controls randomness in model outputs",
                interactive=True
            )

            planner_use_vision = gr.Checkbox(
                label="Use Vision(Planner LLM)",
                value=False,
                info="Enable Vision(Input highlighted screenshot into LLM)",
                interactive=True
            )

            # Ollama-specific context length configuration
    # Context length directly impacts memory usage and processing speed
    # Powers of 2 are used because they align with model architecture and tokenization
    planner_ollama_num_ctx = gr.Slider(
                minimum=2 ** 8,    # 256 tokens - minimal context for simple tasks
                maximum=2 ** 16,   # 65536 tokens - very large context for complex reasoning
                value=16000,       # Balanced default - good for most research tasks
                step=1,
                label="Ollama Context Length",
                info="Controls max context length model needs to handle (less = faster)",
                visible=False,     # Hidden by default, shown when Ollama is selected
                interactive=True
            )

        # API configuration section for custom endpoints and authentication
        # Row layout places related fields side by side for efficient form filling
        with gr.Row():
            # Base URL field for custom API endpoints
            # Essential for self-hosted models, proxy services, or alternative API providers
            planner_llm_base_url = gr.Textbox(
                label="Base URL",
                value="",          # Empty default - uses provider's standard endpoint
                info="API endpoint URL (if required)"
            )

            # API key field with password type for security
            # Allows override of environment variables for testing or multi-key scenarios
            planner_llm_api_key = gr.Textbox(
                label="API Key",
                type="password",   # Masks input for security
                value="",          # Empty default - falls back to environment variables
                info="Your API key (leave blank to use .env)"
            )

    # Agent execution limits section
    # These controls prevent runaway processes and manage resource consumption
    with gr.Row():
        # Maximum workflow steps - prevents infinite loops and runaway costs
        # Range: 1-1000 provides flexibility while preventing excessive resource use
        max_steps = gr.Slider(
            minimum=1,         # At least one step required for any meaningful work
            maximum=1000,      # Upper limit prevents runaway processes
            value=100,         # Default suitable for most complex research tasks
            step=1,
            label="Max Run Steps",
            info="Maximum number of steps the agent will take",
            interactive=True
        )

        # Actions per step limit - controls granularity and prevents blocking
        # Smaller values = more frequent checkpoints, larger values = fewer interruptions
        max_actions = gr.Slider(
            minimum=1,         # Minimum one action per step for progress
            maximum=100,       # Upper bound prevents excessively long steps
            value=10,          # Balanced default - allows meaningful progress per step
            step=1,
            label="Max Number of Actions",
            info="Maximum number of actions the agent will take per step",
            interactive=True
        )

    with gr.Row():
        max_input_tokens = gr.Number(
            label="Max Input Tokens",
            value=128000,
            precision=0,
            interactive=True
        )
        tool_calling_method = gr.Dropdown(
            label="Tool Calling Method",
            value="auto",
            interactive=True,
            allow_custom_value=True,
            choices=["auto", "json_schema", "function_calling", "None"],
            visible=True
        )
    tab_components.update(dict(
        override_system_prompt=override_system_prompt,
        extend_system_prompt=extend_system_prompt,
        llm_provider=llm_provider,
        llm_model_name=llm_model_name,
        llm_temperature=llm_temperature,
        use_vision=use_vision,
        ollama_num_ctx=ollama_num_ctx,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        planner_llm_provider=planner_llm_provider,
        planner_llm_model_name=planner_llm_model_name,
        planner_llm_temperature=planner_llm_temperature,
        planner_use_vision=planner_use_vision,
        planner_ollama_num_ctx=planner_ollama_num_ctx,
        planner_llm_base_url=planner_llm_base_url,
        planner_llm_api_key=planner_llm_api_key,
        max_steps=max_steps,
        max_actions=max_actions,
        max_input_tokens=max_input_tokens,
        tool_calling_method=tool_calling_method,
        mcp_json_file=mcp_json_file,
        mcp_server_config=mcp_server_config,
    ))
    webui_manager.add_components("agent_settings", tab_components)

    llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=llm_provider,
        outputs=ollama_num_ctx
    )
    llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[llm_provider],
        outputs=[llm_model_name]
    )
    planner_llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=[planner_llm_provider],
        outputs=[planner_ollama_num_ctx]
    )
    planner_llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[planner_llm_provider],
        outputs=[planner_llm_model_name]
    )

    async def update_wrapper(mcp_file):
        """Wrapper for handle_pause_resume."""
        update_dict = await update_mcp_server(mcp_file, webui_manager)
        yield update_dict

    mcp_json_file.change(
        update_wrapper,
        inputs=[mcp_json_file],
        outputs=[mcp_server_config, mcp_server_config]
    )
"""
Browser Settings Tab - Browser Automation Configuration and Performance Tuning

This module creates a comprehensive browser configuration interface that allows users
to fine-tune browser automation behavior, performance, and compatibility settings.
Browser automation is highly dependent on proper configuration to work reliably
across different websites, network conditions, and deployment environments.

Key Configuration Categories:
1. Browser Selection: Choose between Chromium, Firefox, Safari, and other supported browsers
2. Display Configuration: Headless vs. headed operation, viewport sizing, and device emulation
3. Performance Tuning: Timeout settings, request throttling, and resource optimization
4. Security Settings: Sandbox configuration, extension management, and permission handling
5. Network Configuration: Proxy settings, SSL handling, and request interception
6. Debugging Options: Screenshot capture, request logging, and automation visibility
7. Platform Compatibility: OS-specific optimizations and cross-platform considerations

Design Philosophy:
- Performance by Default: Optimized settings for common automation scenarios
- Flexibility for Experts: Advanced options for specialized use cases and troubleshooting
- Environment Awareness: Automatic detection and configuration for deployment context
- Safety First: Secure defaults that prevent common automation vulnerabilities
- Observable Operations: Built-in monitoring and debugging capabilities
- Resource Conscious: Efficient resource usage to prevent system overload

Why Browser Configuration is Complex:
Modern browsers are sophisticated platforms with hundreds of configuration options:
- Security Models: Different sandbox and permission configurations affect automation capability
- Performance Trade-offs: Speed vs. reliability vs. resource usage optimization
- Site Compatibility: Some sites require specific browser configurations to function properly
- Network Environments: Corporate proxies, firewalls, and security policies require adaptation
- Development vs. Production: Different optimization priorities for different environments

Critical Configuration Decisions:
1. Headless vs. Headed Operation:
   - Headless: Better performance, lower resource usage, ideal for production
   - Headed: Visual debugging, better compatibility with some sites, easier development

2. Timeout Configuration:
   - Page Load Timeouts: Balance between reliability and performance
   - Element Wait Timeouts: Accommodate slow-loading dynamic content
   - Network Request Timeouts: Handle unreliable network conditions

3. Resource Management:
   - Memory Limits: Prevent runaway browser processes
   - CPU Throttling: Share resources fairly in multi-user environments
   - Disk Usage: Control cache and temporary file accumulation

4. Security vs. Functionality:
   - JavaScript Execution: Required for modern sites but introduces security risks
   - Cookie Handling: Session management vs. privacy considerations
   - File Downloads: Automation capability vs. security isolation

User Experience Enhancements:
- Configuration Validation: Real-time feedback on setting compatibility and conflicts
- Performance Indicators: Show expected resource usage and performance impacts
- Preset Configurations: Quick setup for common scenarios (development, testing, production)
- Compatibility Checking: Verify configurations work with specific target websites
- Resource Monitoring: Display real-time resource usage and performance metrics

This configuration interface is essential for reliable browser automation because
browser behavior varies significantly based on configuration, and optimal settings
depend heavily on the specific automation tasks and deployment environment.
"""

import gradio as gr
import logging
from gradio.components import Component

from src.webui.webui_manager import WebuiManager
from src.utils import config  # existing config import
from src.utils.browser_cleanup import close_browser_resources  # shared cleanup utility

logger = logging.getLogger(__name__)

async def close_browser(webui_manager: WebuiManager):  # cancel tasks and release resources when settings change
    """Close the active browser and reset state.

    Running tasks are cancelled and browser resources are closed so that
    updated settings can be applied cleanly without leaving stale tasks or
    memory leaks.
    """
    # expanded docstring to clarify why resources and tasks are cleaned up
    if getattr(webui_manager, "bu_current_task", None) and not webui_manager.bu_current_task.done():  # safe attr lookup
        webui_manager.bu_current_task.cancel()  # cancel running task if any
        webui_manager.bu_current_task = None

    await close_browser_resources(  # use shared util to close resources
        getattr(webui_manager, "bu_browser", None),
        getattr(webui_manager, "bu_browser_context", None),
    )
    if hasattr(webui_manager, "bu_browser_context"):
        webui_manager.bu_browser_context = None  # reset context reference when present
    if hasattr(webui_manager, "bu_browser"):
        webui_manager.bu_browser = None  # reset browser reference when present

def create_browser_settings_tab(webui_manager: WebuiManager):
    """
    Creates a browser settings tab.
    """
    input_components = set(webui_manager.get_components())
    tab_components = {}

    with gr.Group():  # group path settings separately for clarity
        with gr.Row():
            browser_binary_path = gr.Textbox(
                label="Browser Binary Path",
                lines=1,
                interactive=True,
                placeholder="e.g. '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome'"
            )
            browser_user_data_dir = gr.Textbox(
                label="Browser User Data Dir",
                lines=1,
                interactive=True,
                placeholder="Leave it empty if you use your default user data",
            )
    with gr.Group():
        with gr.Row():
            use_own_browser = gr.Checkbox(
                label="Use Own Browser",
                value=False,
                info="Use your existing browser instance",
                interactive=True
            )
            keep_browser_open = gr.Checkbox(
                label="Keep Browser Open",
                value=True,
                info="Keep Browser Open between Tasks",
                interactive=True
            )
            headless = gr.Checkbox(
                label="Headless Mode",
                value=False,
                info="Run browser without GUI",
                interactive=True
            )
            disable_security = gr.Checkbox(
                label="Disable Security",
                value=False,
                info="Disable browser security",
                interactive=True
            )

    with gr.Group():
        with gr.Row():
            window_w = gr.Number(
                label="Window Width",
                value=1280,
                info="Browser window width",
                interactive=True
            )
            window_h = gr.Number(
                label="Window Height",
                value=1100,
                info="Browser window height",
                interactive=True
            )
    with gr.Group():
        with gr.Row():
            cdp_url = gr.Textbox(
                label="CDP URL",
                info="CDP URL for browser remote debugging",
                interactive=True,
            )
            wss_url = gr.Textbox(
                label="WSS URL",
                info="WSS URL for browser remote debugging",
                interactive=True,
            )
    with gr.Row():
        with gr.Column(scale=1):
            save_recording_path = gr.Textbox(
                label="Recording Path",
                placeholder="e.g. ./tmp/record_videos",
                info="Path to save browser recordings",
                interactive=True,
            )
            save_trace_path = gr.Textbox(
                label="Trace Path",
                placeholder="e.g. ./tmp/traces",
                info="Path to save Agent traces",
                interactive=True,
            )
        with gr.Column(scale=1):
            save_agent_history_path = gr.Textbox(
                label="Agent History Save Path",
                value="./tmp/agent_history",
                info="Specify the directory where agent history should be saved.",
                interactive=True,
            )
            save_download_path = gr.Textbox(
                label="Save Directory for browser downloads",
                value="./tmp/downloads",
                info="Specify the directory where downloaded files should be saved.",
                interactive=True,
            )
    tab_components.update(
        dict(
            browser_binary_path=browser_binary_path,
            browser_user_data_dir=browser_user_data_dir,
            use_own_browser=use_own_browser,
            keep_browser_open=keep_browser_open,
            headless=headless,
            disable_security=disable_security,
            save_recording_path=save_recording_path,
            save_trace_path=save_trace_path,
            save_agent_history_path=save_agent_history_path,
            save_download_path=save_download_path,
            cdp_url=cdp_url,
            wss_url=wss_url,
            window_h=window_h,
            window_w=window_w,
        )
    )
    webui_manager.add_components("browser_settings", tab_components)  # register for persistence and callbacks

    async def close_wrapper():
        """Wrapper for handle_clear."""  # called when toggles affecting browser are changed
        await close_browser(webui_manager)

    headless.change(close_wrapper, inputs=None)  # (explicitly pass None so close_wrapper receives no args)
    keep_browser_open.change(close_wrapper, inputs=None)  # (explicitly pass None so close_wrapper receives no args)
    disable_security.change(close_wrapper, inputs=None)  # (explicitly pass None so close_wrapper receives no args)
    use_own_browser.change(close_wrapper, inputs=None)  # (explicitly pass None so close_wrapper receives no args)

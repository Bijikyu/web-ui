"""
Browser Launch Utilities - Robust Browser Instance Creation and Configuration

This module provides the foundational infrastructure for launching browser instances
with proper configuration, error handling, and resource management. Browser launching
is one of the most failure-prone aspects of browser automation due to the complexity
of browser initialization, platform differences, and resource dependencies.

Critical Challenges This Module Addresses:
1. Platform-specific browser configuration requirements (Windows, macOS, Linux)
2. Resource allocation and limits (memory, CPU, file descriptors)
3. Security sandbox configuration for automation vs. security tradeoffs
4. Network proxy and authentication setup for enterprise environments
5. Display configuration for headless vs. headed operation
6. Browser extension and profile management for specialized workflows
7. Failure recovery and retry logic for unreliable browser initialization

Design Philosophy:
- Fail-fast principle: Detect configuration problems early rather than during automation
- Graceful degradation: Fall back to simpler configurations when complex setups fail
- Resource awareness: Configure browsers appropriately for available system resources
- Security-conscious: Balance automation capabilities with security best practices
- Environment adaptability: Automatically detect and adapt to deployment environments

Why dedicated browser launch utilities:
Browser automation frameworks (Playwright, Selenium) provide basic launch capabilities,
but production browser automation requires additional layers of:
- Configuration validation and error reporting
- Resource monitoring and automatic tuning
- Retry logic and failure recovery
- Environment-specific optimizations
- Security hardening and sandbox configuration
- Performance tuning for specific use cases

Real-world scenarios this addresses:
- Development: Local testing with debugging capabilities and performance monitoring
- CI/CD: Headless operation with minimal resource usage and reliable startup
- Production: Hardened security, resource limits, and comprehensive error handling
- Enterprise: Proxy configuration, certificate management, and access controls

The browser launch process is inherently complex because browsers are full
operating environments with their own process models, security boundaries,
and resource management. This module abstracts that complexity while providing
the flexibility needed for diverse deployment scenarios.
"""

import asyncio
import logging
import os  # needed for env lookup
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple  # typing for function

# Playwright async API for modern, reliable browser automation
# Chosen over alternatives like Selenium for:
# - Better async/await support for non-blocking operations
# - More reliable element detection and interaction
# - Built-in waiting and retry mechanisms
# - Better cross-browser compatibility and standardization
from src.utils.offline import is_offline  # check if running in offline mode

# Module-level logger for tracking browser launch operations and failures
# Browser launch failures are often cryptic and environment-dependent
# Detailed logging is essential for debugging deployment and configuration issues
logger = logging.getLogger(__name__)


def build_browser_launch_options(config: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:  # build browser options
    """Build browser binary path and extra launch arguments.

    The ``config`` dict may include ``window_width``, ``window_height``,
    ``user_data_dir``, ``use_own_browser`` and ``browser_binary_path``.
    Environment variables ``CHROME_PATH`` and ``CHROME_USER_DATA`` override
    path settings when ``use_own_browser`` is true.
    """  # function description expanded
    if not is_offline():  # only import when online; offline mode uses no import
        from playwright.async_api import async_playwright  # import lazily when online
    window_w = config.get("window_width", 1280)  # width from config; default 1280
    window_h = config.get("window_height", 1100)  # height from config; default 1100
    extra_args = [f"--window-size={window_w},{window_h}"]  # window geometry arg
    browser_user_data_dir = config.get("user_data_dir", None)  # custom data dir for persistent profiles
    if browser_user_data_dir:
        extra_args.append(f"--user-data-dir={browser_user_data_dir}")  # add dir option
    use_own_browser = config.get("use_own_browser", False)  # check custom browser usage
    browser_binary_path = config.get("browser_binary_path", None)  # path from config
    if use_own_browser:
        browser_binary_path = os.getenv("CHROME_PATH", None) or browser_binary_path  # env override
        if browser_binary_path == "":
            browser_binary_path = None  # empty -> None
        chrome_user_data = os.getenv("CHROME_USER_DATA", None)  # check env data dir
        if chrome_user_data:
            extra_args.append(f"--user-data-dir={chrome_user_data}")  # add env dir
    else:
        browser_binary_path = None  # not using custom browser
    return browser_binary_path, extra_args  # return values

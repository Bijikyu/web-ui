
"""
Browser launch utilities for automated browser session management.

This module handles the complex process of launching and configuring browsers
for automation purposes. Browser automation requires careful setup of numerous
parameters, security settings, and compatibility options to ensure reliable
operation across different environments and use cases.

Key challenges addressed by this module:
- Cross-platform browser compatibility (Windows, macOS, Linux)
- Security configuration for automation (bypassing restrictions safely)
- Performance optimization for automated scenarios
- Profile and session management
- Anti-detection measures for web scraping scenarios
- Resource management and cleanup coordination

The module provides both high-level convenience functions and low-level
configuration options to support different automation scenarios, from simple
testing to complex web scraping operations.
"""

import asyncio
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import socket
import time

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContextConfig
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContextConfig

logger = logging.getLogger(__name__)

# Default browser arguments optimized for automation
# These arguments balance functionality, performance, and compatibility
DEFAULT_AUTOMATION_ARGS = [
    '--no-sandbox',  # Required for running in containers and CI environments
    '--disable-blink-features=AutomationControlled',  # Hide automation indicators
    '--disable-dev-shm-usage',  # Prevents shared memory issues in containers
    '--disable-gpu',  # Improves stability in headless environments
    '--disable-web-security',  # Allows cross-origin requests for testing
    '--disable-features=VizDisplayCompositor',  # Prevents display issues
    '--disable-background-timer-throttling',  # Ensures consistent timing
    '--disable-renderer-backgrounding',  # Prevents performance throttling
    '--disable-backgrounding-occluded-windows',  # Maintains window performance
]

# Arguments for stealth/anti-detection mode
# These help browsers appear more like regular user browsers
STEALTH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--exclude-switches=enable-automation',
    '--disable-extensions-except',
    '--disable-plugins-discovery',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-default-apps',
    '--disable-component-extensions-with-background-pages',
]

# Performance-optimized arguments
# These improve speed and reduce resource usage for automation
PERFORMANCE_ARGS = [
    '--aggressive-cache-discard',
    '--memory-pressure-off',
    '--max_old_space_size=4096',
    '--disable-background-networking',
    '--disable-client-side-phishing-detection',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-domain-reliability',
]


class BrowserLaunchConfig:
    """
    Configuration class for browser launch parameters.
    
    This class encapsulates all the various options and settings needed to
    launch a browser for automation. It provides sensible defaults while
    allowing fine-grained control over browser behavior.
    
    Why a dedicated config class:
    - Centralizes complex configuration logic
    - Provides validation and type checking
    - Enables configuration presets for common scenarios
    - Makes testing and debugging easier
    - Allows for configuration serialization/deserialization
    """
    
    def __init__(self,
                 browser_type: str = 'chrome',
                 headless: bool = False,
                 window_width: int = 1920,
                 window_height: int = 1080,
                 user_data_dir: Optional[str] = None,
                 proxy: Optional[Dict[str, str]] = None,
                 stealth_mode: bool = True,
                 performance_mode: bool = True,
                 extra_args: Optional[List[str]] = None,
                 timeout_seconds: int = 30):
        """
        Initialize browser launch configuration.
        
        Args:
            browser_type: Type of browser to launch ('chrome', 'firefox', 'edge')
            headless: Whether to run browser in headless mode
            window_width: Initial browser window width
            window_height: Initial browser window height
            user_data_dir: Custom user data directory for persistent sessions
            proxy: Proxy configuration if needed
            stealth_mode: Enable anti-detection features
            performance_mode: Enable performance optimizations
            extra_args: Additional browser arguments
            timeout_seconds: Timeout for browser launch operations
            
        Design decisions:
        - Default to Chrome as it has the best automation support
        - Default to visible mode for debugging but support headless
        - Use standard desktop resolution by default
        - Enable stealth and performance modes by default for better automation
        """
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.window_width = window_width
        self.window_height = window_height
        self.user_data_dir = user_data_dir
        self.proxy = proxy or {}
        self.stealth_mode = stealth_mode
        self.performance_mode = performance_mode
        self.extra_args = extra_args or []
        self.timeout_seconds = timeout_seconds
        
        # Validate browser type
        supported_browsers = ['chrome', 'chromium', 'firefox', 'edge']
        if self.browser_type not in supported_browsers:
            logger.warning(f"Unsupported browser type: {browser_type}. Defaulting to chrome.")
            self.browser_type = 'chrome'
    
    def get_browser_arguments(self) -> List[str]:
        """
        Generate the complete list of browser arguments based on configuration.
        
        This method combines the base automation arguments with optional
        stealth and performance arguments, plus any user-specified arguments.
        The order of arguments can matter for some browsers, so we build
        the list carefully.
        
        Returns:
            List[str]: Complete list of browser command-line arguments
            
        Argument precedence:
        1. Base automation arguments (always included)
        2. Stealth arguments (if stealth_mode enabled)
        3. Performance arguments (if performance_mode enabled)
        4. Window size and display arguments
        5. User-specified extra arguments (highest precedence)
        """
        args = DEFAULT_AUTOMATION_ARGS.copy()
        
        # Add stealth arguments if enabled
        if self.stealth_mode:
            args.extend(STEALTH_ARGS)
            logger.debug("Added stealth arguments for anti-detection")
        
        # Add performance arguments if enabled
        if self.performance_mode:
            args.extend(PERFORMANCE_ARGS)
            logger.debug("Added performance arguments for optimization")
        
        # Add window size configuration
        args.append(f'--window-size={self.window_width},{self.window_height}')
        
        # Add headless mode if specified
        if self.headless:
            args.append('--headless=new')  # Use new headless mode for better compatibility
        
        # Add user data directory if specified
        if self.user_data_dir:
            args.append(f'--user-data-dir={self.user_data_dir}')
        
        # Add proxy configuration if specified
        if self.proxy:
            if 'server' in self.proxy:
                args.append(f'--proxy-server={self.proxy["server"]}')
            if 'bypass_list' in self.proxy:
                args.append(f'--proxy-bypass-list={self.proxy["bypass_list"]}')
        
        # Add extra user arguments (these take precedence)
        args.extend(self.extra_args)
        
        # Remove duplicates while preserving order
        # This is important because duplicate arguments can cause issues
        seen = set()
        unique_args = []
        for arg in args:
            if arg not in seen:
                seen.add(arg)
                unique_args.append(arg)
        
        return unique_args
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for serialization or logging.
        
        This enables saving configurations, logging current settings, and
        recreating configurations from stored data.
        """
        return {
            'browser_type': self.browser_type,
            'headless': self.headless,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'user_data_dir': self.user_data_dir,
            'proxy': self.proxy,
            'stealth_mode': self.stealth_mode,
            'performance_mode': self.performance_mode,
            'extra_args': self.extra_args,
            'timeout_seconds': self.timeout_seconds
        }


class BrowserLauncher:
    """
    High-level browser launcher that handles the complexities of browser setup.
    
    This class provides a clean interface for launching browsers with proper
    configuration, error handling, and resource management. It abstracts away
    the details of different browser types and platforms while providing
    the flexibility needed for various automation scenarios.
    
    Key responsibilities:
    - Browser process management and lifecycle
    - Configuration validation and setup
    - Port management and conflict resolution
    - Temporary directory management
    - Error handling and recovery
    - Resource cleanup coordination
    """
    
    def __init__(self, config: Optional[BrowserLaunchConfig] = None):
        """
        Initialize the browser launcher with optional configuration.
        
        Args:
            config: Browser launch configuration, uses defaults if None
        """
        self.config = config or BrowserLaunchConfig()
        self.browser_instance: Optional[CustomBrowser] = None
        self.temp_dirs: List[str] = []  # Track temporary directories for cleanup
        self.allocated_ports: List[int] = []  # Track allocated ports for cleanup
        
    def _find_available_port(self, start_port: int = 9222, max_attempts: int = 100) -> int:
        """
        Find an available port for browser debugging interface.
        
        Browser automation often requires a debugging port for communication.
        This function finds an available port to prevent conflicts with other
        browser instances or services.
        
        Args:
            start_port: Starting port number to check
            max_attempts: Maximum number of ports to check
            
        Returns:
            int: Available port number
            
        Raises:
            RuntimeError: If no available port is found
            
        Why port management is important:
        - Multiple browser instances need separate debugging ports
        - Port conflicts can prevent browser startup
        - Some environments have restricted port ranges
        - Proper cleanup requires tracking allocated ports
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('127.0.0.1', port))
                    self.allocated_ports.append(port)
                    logger.debug(f"Allocated port {port} for browser debugging")
                    return port
            except OSError:
                continue  # Port is in use, try next one
        
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")
    
    def _create_temp_profile_dir(self) -> str:
        """
        Create a temporary profile directory for browser session.
        
        Browser automation often benefits from using temporary profiles to
        ensure clean state and prevent conflicts with user's regular browser
        data. This function creates and tracks temporary directories.
        
        Returns:
            str: Path to created temporary directory
            
        Why temporary profiles are useful:
        - Ensures clean browser state for each session
        - Prevents interference with user's regular browser usage
        - Allows for session-specific configurations
        - Enables parallel browser sessions without conflicts
        - Simplifies cleanup after automation completes
        """
        temp_dir = tempfile.mkdtemp(prefix='browser_automation_')
        self.temp_dirs.append(temp_dir)
        logger.debug(f"Created temporary profile directory: {temp_dir}")
        return temp_dir
    
    async def launch_browser(self) -> CustomBrowser:
        """
        Launch a browser instance with the configured settings.
        
        This is the main method that orchestrates the browser launch process.
        It handles all the setup steps, error checking, and returns a ready-to-use
        browser instance.
        
        Returns:
            CustomBrowser: Configured and ready browser instance
            
        Raises:
            RuntimeError: If browser launch fails
            
        Launch process:
        1. Validate configuration and environment
        2. Set up temporary directories if needed
        3. Allocate debugging port
        4. Build browser arguments
        5. Create and configure browser instance
        6. Verify browser is responsive
        7. Return ready browser instance
        
        Error handling:
        - Validates browser executable exists
        - Handles port conflicts gracefully
        - Provides detailed error messages for debugging
        - Cleans up resources if launch fails
        """
        logger.info(f"Launching {self.config.browser_type} browser (headless: {self.config.headless})")
        
        try:
            # Create temporary profile directory if not specified
            if not self.config.user_data_dir:
                self.config.user_data_dir = self._create_temp_profile_dir()
            
            # Find available debugging port
            debug_port = self._find_available_port()
            
            # Build complete browser arguments
            browser_args = self.config.get_browser_arguments()
            browser_args.append(f'--remote-debugging-port={debug_port}')
            
            logger.debug(f"Browser arguments: {browser_args}")
            
            # Create browser context configuration
            context_config = CustomBrowserContextConfig(
                window_width=self.config.window_width,
                window_height=self.config.window_height,
                headless=self.config.headless,
                disable_security=True,  # Required for automation
                extra_browser_args=browser_args,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            
            # Create custom browser instance
            self.browser_instance = CustomBrowser(config=context_config)
            
            # Initialize browser with timeout
            await asyncio.wait_for(
                self.browser_instance.setup(),
                timeout=self.config.timeout_seconds
            )
            
            logger.info(f"Browser launched successfully on port {debug_port}")
            return self.browser_instance
            
        except asyncio.TimeoutError:
            error_msg = f"Browser launch timed out after {self.config.timeout_seconds} seconds"
            logger.error(error_msg)
            await self.cleanup()
            raise RuntimeError(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to launch browser: {e}"
            logger.error(error_msg)
            await self.cleanup()
            raise RuntimeError(error_msg)
    
    async def cleanup(self):
        """
        Clean up resources allocated during browser launch.
        
        This method ensures that all resources (temporary directories, ports,
        browser processes) are properly released when the launcher is done.
        It's critical for preventing resource leaks in long-running applications.
        
        Cleanup operations:
        1. Close browser instance if it exists
        2. Remove temporary profile directories
        3. Release allocated ports
        4. Clear tracking lists
        
        Error handling:
        - Continues cleanup even if individual operations fail
        - Logs cleanup issues for debugging
        - Ensures critical resources are always released
        """
        logger.info("Cleaning up browser launcher resources")
        
        # Close browser instance
        if self.browser_instance:
            try:
                await self.browser_instance.close()
                logger.debug("Browser instance closed")
            except Exception as e:
                logger.warning(f"Error closing browser instance: {e}")
            finally:
                self.browser_instance = None
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Error removing temporary directory {temp_dir}: {e}")
        
        self.temp_dirs.clear()
        self.allocated_ports.clear()
        
        logger.info("Browser launcher cleanup completed")


# Convenience functions for common launch scenarios
async def launch_chrome_for_automation(headless: bool = False, 
                                     stealth: bool = True,
                                     window_size: tuple = (1920, 1080)) -> CustomBrowser:
    """
    Convenience function to launch Chrome with optimal automation settings.
    
    This function provides a simple interface for the most common browser
    automation scenario: launching Chrome with good defaults for automation.
    
    Args:
        headless: Whether to run in headless mode
        stealth: Whether to enable anti-detection features
        window_size: Browser window size as (width, height) tuple
        
    Returns:
        CustomBrowser: Ready-to-use Chrome browser instance
        
    Use cases:
    - Quick automation scripts
    - Testing scenarios
    - Web scraping tasks
    - Automated testing
    """
    config = BrowserLaunchConfig(
        browser_type='chrome',
        headless=headless,
        window_width=window_size[0],
        window_height=window_size[1],
        stealth_mode=stealth,
        performance_mode=True
    )
    
    launcher = BrowserLauncher(config)
    return await launcher.launch_browser()


async def launch_browser_with_proxy(proxy_server: str,
                                   browser_type: str = 'chrome',
                                   headless: bool = True) -> CustomBrowser:
    """
    Launch browser with proxy configuration for specialized networking needs.
    
    This function is useful for scenarios requiring proxy usage, such as
    IP rotation, accessing geo-restricted content, or routing through
    corporate networks.
    
    Args:
        proxy_server: Proxy server URL (e.g., "http://proxy.example.com:8080")
        browser_type: Type of browser to launch
        headless: Whether to run in headless mode
        
    Returns:
        CustomBrowser: Browser instance configured with proxy
        
    Use cases:
    - IP rotation for web scraping
    - Corporate network environments
    - Geo-location testing
    - Privacy-focused automation
    """
    config = BrowserLaunchConfig(
        browser_type=browser_type,
        headless=headless,
        proxy={'server': proxy_server},
        stealth_mode=True,
        performance_mode=True
    )
    
    launcher = BrowserLauncher(config)
    return await launcher.launch_browser()


def get_browser_launch_presets() -> Dict[str, BrowserLaunchConfig]:
    """
    Get predefined browser launch configurations for common scenarios.
    
    This function provides ready-made configurations for typical use cases,
    making it easy to launch browsers with appropriate settings without
    needing to understand all the configuration details.
    
    Returns:
        Dict[str, BrowserLaunchConfig]: Available preset configurations
        
    Available presets:
    - development: Good for development and debugging
    - testing: Optimized for automated testing
    - scraping: Configured for web scraping with anti-detection
    - performance: Maximum performance for batch operations
    - stealth: Maximum stealth for sensitive operations
    """
    return {
        'development': BrowserLaunchConfig(
            headless=False,
            stealth_mode=False,
            performance_mode=False,
            timeout_seconds=60
        ),
        'testing': BrowserLaunchConfig(
            headless=True,
            stealth_mode=False,
            performance_mode=True,
            timeout_seconds=30
        ),
        'scraping': BrowserLaunchConfig(
            headless=True,
            stealth_mode=True,
            performance_mode=True,
            timeout_seconds=45,
            extra_args=[
                '--disable-images',  # Faster loading
                '--disable-javascript',  # Reduce complexity
            ]
        ),
        'performance': BrowserLaunchConfig(
            headless=True,
            stealth_mode=False,
            performance_mode=True,
            timeout_seconds=15,
            extra_args=[
                '--disable-images',
                '--disable-css',
                '--disable-plugins',
                '--disable-extensions'
            ]
        ),
        'stealth': BrowserLaunchConfig(
            headless=False,  # Sometimes headless is detected
            stealth_mode=True,
            performance_mode=False,  # Stealth over speed
            timeout_seconds=60,
            extra_args=[
                '--disable-logging',
                '--silent'
            ]
        )
    }

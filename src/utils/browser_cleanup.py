"""
Browser Cleanup Utilities - Resource Management for Browser Automation

This module provides critical infrastructure for managing browser process lifecycles
and preventing resource leaks in long-running browser automation applications.
Browser automation can easily create orphaned processes, memory leaks, and file
descriptor exhaustion without proper cleanup management.

Critical Problems This Module Solves:
1. Orphaned browser processes that survive application crashes or improper shutdowns
2. Memory leaks from browser instances that aren't properly closed
3. File descriptor exhaustion from accumulated browser resources
4. Zombie processes that consume system resources indefinitely
5. Port conflicts from browsers that don't release network resources

Design Philosophy:
- Proactive cleanup: Don't wait for garbage collection, actively manage resources
- Graceful degradation: Attempt clean shutdown before forcing termination
- System-wide scope: Clean up processes even if they're orphaned from parent application
- Cross-platform compatibility: Handle platform differences in process management
- Defensive programming: Assume cleanup might fail and have fallback strategies

Why this is essential for browser automation:
- Browser processes are heavyweight and resource-intensive
- Chromium/Playwright browsers spawn multiple child processes that need coordination
- Network resources (ports, sockets) can be exhausted by improperly closed browsers
- Development cycles involve frequent restarts that can accumulate orphaned processes
- Production deployments need reliable cleanup to prevent resource exhaustion

Real-world consequences without proper cleanup:
- Development machines become unusable due to resource exhaustion
- Production servers crash due to memory/file descriptor limits
- CI/CD pipelines fail due to accumulated browser processes
- User machines experience performance degradation from hidden browser processes

This module uses platform-specific process management (psutil) because browser
cleanup requirements exceed what standard Python process management can handle.
"""

import asyncio
import logging
import psutil  # Platform-independent process and system utilities
import signal  # Unix signal handling for graceful process termination
from typing import List, Optional

# Module-level logger for tracking cleanup operations and failures
# Essential for debugging resource leaks and cleanup failures in production
# Cleanup failures are often silent and only manifest as resource exhaustion later
logger = logging.getLogger(__name__)

# Async function to close browser resources (context and browser)
async def close_browser_resources(browser, context):
    # Check if a browser context is provided
    if context:
        # Log the closing of the browser context
        logger.info("⚠️ Closing browser context when changing browser config.")  # log context closing
        # Attempt to close the browser context
        try:
            await context.close()
        # Handle any exceptions that occur during context closing
        except Exception as e:
            # Log the error if closing the context fails
            logger.error(f"Error closing context: {e}")
    # Check if a browser instance is provided
    if browser:
        # Log the closing of the browser
        logger.info("⚠️ Closing browser when changing browser config.")  # log browser closing
        # Attempt to close the browser
        try:
            await browser.close()
        # Handle any exceptions that occur during browser closing
        except Exception as e:
            # Log the error if closing the browser fails
            logger.error(f"Error closing browser: {e}")
`
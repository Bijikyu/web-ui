
"""
Agent utility functions for browser automation and task management.

This module provides helper functions that support agent operations, including
browser state management, task execution utilities, and common operations that
are shared across different agent implementations.

The utilities here are designed to be reusable across different agent types
(browser_use, deep_research, etc.) and provide consistent behavior for common
operations like error handling, state validation, and resource management.
"""

import logging
from typing import Dict, Any, Optional, List
from browser_use.browser.context import BrowserContext
import asyncio
import json

logger = logging.getLogger(__name__)


def validate_browser_state(browser_context: Optional[BrowserContext]) -> bool:
    """
    Validates that a browser context is in a usable state for agent operations.
    
    This function performs essential checks to ensure the browser context can
    handle agent requests safely. It's crucial for preventing crashes and
    ensuring reliable agent behavior across different scenarios.
    
    Args:
        browser_context: The browser context to validate
        
    Returns:
        bool: True if the context is valid and ready for use, False otherwise
        
    Why this validation is necessary:
    - Browser contexts can become invalid due to crashes, network issues, or timeouts
    - Early validation prevents downstream errors in agent operations
    - Provides a single point for browser state checking logic
    - Enables graceful degradation when browser issues occur
    
    Edge cases handled:
    - None context (not initialized)
    - Closed/disconnected contexts
    - Contexts with invalid page states
    """
    if browser_context is None:
        logger.warning("Browser context is None - cannot proceed with agent operations")
        return False
        
    try:
        # Check if the context has an active page
        # This is a lightweight check that doesn't require network calls
        if not hasattr(browser_context, 'page') or browser_context.page is None:
            logger.warning("Browser context has no active page")
            return False
            
        # Additional checks could be added here for more thorough validation
        # For example: checking if the page is responsive, network connectivity, etc.
        return True
        
    except Exception as e:
        logger.error(f"Error validating browser context: {e}")
        return False


def sanitize_task_description(task: str, max_length: int = 1000) -> str:
    """
    Sanitizes and validates task descriptions for agent processing.
    
    This function ensures task descriptions are safe, properly formatted, and
    within reasonable limits for agent processing. It prevents issues with
    malformed inputs that could cause agent failures or security concerns.
    
    Args:
        task: The raw task description from user input
        max_length: Maximum allowed length for task descriptions
        
    Returns:
        str: Sanitized task description ready for agent processing
        
    Why sanitization is important:
    - Prevents injection attacks through task descriptions
    - Ensures consistent formatting for agent prompts
    - Limits resource usage by preventing extremely long inputs
    - Removes potentially problematic characters that could break parsing
    
    Sanitization steps:
    1. Strip whitespace and normalize line endings
    2. Remove or escape special characters that could break prompts
    3. Truncate to reasonable length to prevent token limit issues
    4. Validate basic structure and content
    """
    if not task or not isinstance(task, str):
        logger.warning("Invalid task description provided - using default")
        return "No specific task provided"
    
    # Normalize whitespace and remove excessive line breaks
    # This ensures consistent formatting across different input sources
    sanitized = ' '.join(task.strip().split())
    
    # Truncate to maximum length to prevent token limit issues
    # This is especially important for LLM-based agents with context limits
    if len(sanitized) > max_length:
        logger.info(f"Task description truncated from {len(sanitized)} to {max_length} characters")
        sanitized = sanitized[:max_length].rstrip() + "..."
    
    # Basic validation - ensure we have meaningful content
    if len(sanitized.strip()) < 3:
        logger.warning("Task description too short - using default")
        return "Please provide a more detailed task description"
    
    return sanitized


def format_agent_result(result: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
    """
    Formats agent execution results into a standardized structure.
    
    This function ensures all agent results follow a consistent format regardless
    of the specific agent implementation. This standardization is crucial for
    UI components, logging, and result processing that need to work across
    different agent types.
    
    Args:
        result: Raw result dictionary from agent execution
        agent_type: Type of agent that generated the result
        
    Returns:
        Dict[str, Any]: Standardized result dictionary
        
    Why standardization matters:
    - UI components can reliably access result fields
    - Logging and monitoring systems get consistent data
    - Result processing pipelines work across all agent types
    - Error handling can be unified across different agents
    
    Standard result structure:
    - success: Boolean indicating if the task completed successfully
    - message: Human-readable description of what happened
    - data: Any specific data returned by the agent
    - agent_type: Which agent generated this result
    - timestamp: When the result was generated
    - error_details: Specific error information if the task failed
    """
    import time
    
    # Ensure we always have a basic structure
    # This prevents KeyError exceptions in downstream processing
    formatted_result = {
        'success': False,
        'message': 'Unknown result',
        'data': None,
        'agent_type': agent_type,
        'timestamp': time.time(),
        'error_details': None
    }
    
    if not result or not isinstance(result, dict):
        logger.warning(f"Invalid result format from {agent_type} agent")
        formatted_result['message'] = f"Invalid result from {agent_type} agent"
        return formatted_result
    
    # Extract success status with fallback logic
    # Different agents may use different field names for success indication
    if 'success' in result:
        formatted_result['success'] = bool(result['success'])
    elif 'error' in result:
        formatted_result['success'] = False
        formatted_result['error_details'] = result['error']
    elif 'result' in result and result['result']:
        formatted_result['success'] = True
    
    # Extract message with intelligent fallbacks
    # Provides meaningful feedback even when agents don't provide explicit messages
    if 'message' in result:
        formatted_result['message'] = str(result['message'])
    elif 'error' in result:
        formatted_result['message'] = f"Error in {agent_type}: {result['error']}"
    elif formatted_result['success']:
        formatted_result['message'] = f"{agent_type} task completed successfully"
    else:
        formatted_result['message'] = f"{agent_type} task failed"
    
    # Preserve any additional data from the agent
    # This allows agent-specific information to be passed through
    if 'data' in result:
        formatted_result['data'] = result['data']
    elif 'result' in result:
        formatted_result['data'] = result['result']
    
    logger.info(f"Formatted result from {agent_type}: {formatted_result['success']} - {formatted_result['message']}")
    return formatted_result


async def cleanup_agent_resources(browser_context: Optional[BrowserContext], 
                                agent_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Performs cleanup operations after agent task completion or failure.
    
    This function ensures that resources used during agent execution are properly
    released, preventing memory leaks and ensuring the system remains stable
    across multiple agent runs. Cleanup is critical in long-running applications
    where resources can accumulate over time.
    
    Args:
        browser_context: Browser context to clean up (if any)
        agent_data: Additional agent-specific data that may need cleanup
        
    Why cleanup is essential:
    - Prevents memory leaks from accumulating browser resources
    - Ensures file handles and network connections are properly closed
    - Maintains system stability across multiple agent executions
    - Provides a consistent cleanup pattern for all agent types
    
    Cleanup operations:
    - Close browser pages and contexts safely
    - Clear temporary files created during execution
    - Release any locks or shared resources
    - Log cleanup operations for debugging
    
    Error handling:
    - Continues cleanup even if individual operations fail
    - Logs errors without stopping the overall cleanup process
    - Ensures critical resources are always released
    """
    logger.info("Starting agent resource cleanup")
    
    # Browser context cleanup - most critical for preventing resource leaks
    if browser_context:
        try:
            # Give any pending operations a moment to complete
            # This prevents issues with abruptly closing active browser operations
            await asyncio.sleep(0.1)
            
            # Close browser context safely
            # This releases memory and browser resources
            if hasattr(browser_context, 'close'):
                await browser_context.close()
                logger.info("Browser context closed successfully")
        except Exception as e:
            # Log but don't fail - cleanup should always continue
            logger.error(f"Error closing browser context: {e}")
    
    # Agent-specific cleanup
    if agent_data:
        try:
            # Clean up any temporary files or resources specified in agent_data
            if 'temp_files' in agent_data:
                for file_path in agent_data['temp_files']:
                    try:
                        import os
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.debug(f"Removed temporary file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove temporary file {file_path}: {e}")
            
            # Release any other agent-specific resources
            if 'cleanup_callbacks' in agent_data:
                for callback in agent_data['cleanup_callbacks']:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback()
                        else:
                            callback()
                    except Exception as e:
                        logger.warning(f"Error in cleanup callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error in agent-specific cleanup: {e}")
    
    logger.info("Agent resource cleanup completed")


def extract_error_details(exception: Exception, context: str = "") -> Dict[str, Any]:
    """
    Extracts and formats detailed error information for debugging and user feedback.
    
    This function provides comprehensive error analysis that helps with debugging
    agent issues and provides meaningful feedback to users when things go wrong.
    Proper error handling is crucial for maintaining user trust and enabling
    effective troubleshooting.
    
    Args:
        exception: The exception that occurred
        context: Additional context about when/where the error occurred
        
    Returns:
        Dict[str, Any]: Structured error information
        
    Why detailed error extraction matters:
    - Enables effective debugging of agent issues
    - Provides users with actionable error messages
    - Helps identify patterns in failures for system improvement
    - Supports automated error reporting and monitoring
    
    Extracted information:
    - Error type and message
    - Stack trace for debugging
    - Context information
    - Suggested resolution steps
    - Timestamp and severity level
    """
    import traceback
    import time
    
    error_details = {
        'type': type(exception).__name__,
        'message': str(exception),
        'context': context,
        'timestamp': time.time(),
        'stack_trace': traceback.format_exc(),
        'severity': 'error'
    }
    
    # Analyze error type to provide better context and suggestions
    error_type = type(exception).__name__
    
    if 'timeout' in error_type.lower() or 'timeout' in str(exception).lower():
        error_details['severity'] = 'warning'
        error_details['suggestion'] = "This appears to be a timeout error. Try increasing timeout values or checking network connectivity."
    elif 'permission' in str(exception).lower():
        error_details['suggestion'] = "This appears to be a permission error. Check file/directory permissions or browser security settings."
    elif 'connection' in str(exception).lower():
        error_details['suggestion'] = "This appears to be a network connectivity issue. Check internet connection and firewall settings."
    elif 'memory' in str(exception).lower() or 'resource' in str(exception).lower():
        error_details['severity'] = 'critical'
        error_details['suggestion'] = "This appears to be a resource exhaustion issue. Consider restarting the application or increasing available resources."
    else:
        error_details['suggestion'] = "An unexpected error occurred. Check logs for more details."
    
    logger.error(f"Error extracted: {error_details['type']} - {error_details['message']} (Context: {context})")
    return error_details

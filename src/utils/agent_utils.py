"""
Agent Utilities - Core Helper Functions for Browser Agent Operations

This module provides essential utility functions that support browser agent operations
across the entire application. It serves as a centralized collection of commonly-needed
functionality that spans multiple agent types and operational contexts.

Key Responsibilities:
- Input validation and sanitization for agent parameters and user data
- Configuration parsing and validation for various agent types
- Common formatting and transformation functions used across agents
- Error handling helpers that provide consistent behavior across the application
- Performance monitoring utilities for agent operation analysis

Design Philosophy:
- DRY Principle: Eliminate code duplication across different agent implementations
- Single Responsibility: Each function has a clear, focused purpose
- Type Safety: Strong typing and validation to prevent runtime errors
- Error Resilience: Graceful handling of edge cases and invalid inputs
- Performance Conscious: Efficient implementations suitable for high-frequency use

Why centralized utilities vs. agent-specific helpers:
- Consistency: Same validation logic across all agent types prevents subtle bugs
- Maintainability: Single location for common functionality reduces maintenance burden
- Testability: Centralized functions are easier to unit test comprehensively
- Reusability: Functions can be shared between different agent implementations
- Performance: Shared implementations can be optimized once for all consumers

This module is imported by virtually every other module in the agent system,
so performance and reliability are critical considerations. All functions are
designed to be stateless and thread-safe for use in concurrent environments.
"""

import logging
import re
from typing import Any, Dict, List, Optional
import gradio as gr  # // import for warning UI when init fails
from . import llm_provider  # // allow model creation via provider utility

# Module-level logger for consistent logging across all utility functions
# This enables fine-grained control over utility function debugging and monitoring
# Essential for troubleshooting complex agent workflows that use multiple utilities
logger = logging.getLogger(__name__)


async def initialize_llm(
    provider: Optional[str],
    model_name: Optional[str],
    temperature: float,
    base_url: Optional[str],
    api_key: Optional[str],
    num_ctx: Optional[int] = None,
) -> Optional[Any]:
    """Return chat model or ``None`` when creation fails."""  # // docstring summarizing behavior
    logger.info(
        "initialize_llm is running with %s %s", provider, model_name
    )  # // log start of function
    if not provider or not model_name:
        return None  # // guard when fields missing
    try:
        model = llm_provider.get_llm_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            num_ctx=num_ctx,
        )  # // create model using provider utility
        logger.info("initialize_llm is returning %s", model)  # // log return value
        return model
    except Exception as err:
        logger.error("initialize_llm failed: %s", err)  # // log error details
        gr.Warning(f"LLM provider '{provider}' failed to initialize")  # // warn ui of failure
        return None

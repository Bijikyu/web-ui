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

# Module-level logger for consistent logging across all utility functions
# This enables fine-grained control over utility function debugging and monitoring
# Essential for troubleshooting complex agent workflows that use multiple utilities
logger = logging.getLogger(__name__)
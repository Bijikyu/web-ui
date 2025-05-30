PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "azure_openai": "Azure OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
    "google": "Google",
    "alibaba": "Alibaba",
    "moonshot": "MoonShot",
    "unbound": "Unbound AI",
    "ibm": "IBM"
}

# Predefined model names for common providers
model_names = {
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "o3-mini"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "google": ["gemini-2.0-flash", "gemini-2.0-flash-thinking-exp", "gemini-1.5-flash-latest",
               "gemini-1.5-flash-8b-latest", "gemini-2.0-flash-thinking-exp-01-21", "gemini-2.0-pro-exp-02-05",
               "gemini-2.5-pro-preview-03-25", "gemini-2.5-flash-preview-04-17"],
    "ollama": ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5-coder:14b", "qwen2.5-coder:32b", "llama2:7b",
               "deepseek-r1:14b", "deepseek-r1:32b"],
    "azure_openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "mistral": ["pixtral-large-latest", "mistral-large-latest", "mistral-small-latest", "ministral-8b-latest"],
    "alibaba": ["qwen-plus", "qwen-max", "qwen-vl-max", "qwen-vl-plus", "qwen-turbo", "qwen-long"],
    "moonshot": ["moonshot-v1-32k-vision-preview", "moonshot-v1-8k-vision-preview"],
    "unbound": ["gemini-2.0-flash", "gpt-4o-mini", "gpt-4o", "gpt-4.5-preview"],
    "siliconflow": [
        "deepseek-ai/DeepSeek-R1",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "deepseek-ai/DeepSeek-V2.5",
        "deepseek-ai/deepseek-vl2",
        "Qwen/Qwen2.5-72B-Instruct-128K",
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "Qwen/Qwen2.5-14B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        "Qwen/Qwen2-7B-Instruct",
        "Qwen/Qwen2-1.5B-Instruct",
        "Qwen/QwQ-32B-Preview",
        "Qwen/Qwen2-VL-72B-Instruct",
        "Qwen/Qwen2.5-VL-32B-Instruct",
        "Qwen/Qwen2.5-VL-72B-Instruct",
        "TeleAI/TeleChat2",
        "THUDM/glm-4-9b-chat",
        "Vendor-A/Qwen/Qwen2.5-72B-Instruct",
        "internlm/internlm2_5-7b-chat",
        "internlm/internlm2_5-20b-chat",
        "Pro/Qwen/Qwen2.5-7B-Instruct",
        "Pro/Qwen/Qwen2-7B-Instruct",
        "Pro/Qwen/Qwen2-1.5B-Instruct",
        "Pro/THUDM/chatglm3-6b",
        "Pro/THUDM/glm-4-9b-chat",
    ],
    "ibm": ["ibm/granite-vision-3.1-2b-preview", "meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
            "meta-llama/llama-3-2-90b-vision-instruct"]
}
"""
Configuration Management - Centralized Application Settings and Environment Handling

This module provides robust configuration management for the Browser Agent WebUI,
handling the complex requirements of modern applications that must operate across
diverse environments while maintaining security, flexibility, and maintainability.

Configuration Challenges Addressed:
1. Environment-specific settings (development, staging, production)
2. Secure secret management (API keys, database credentials, authentication tokens)
3. Feature flag management for gradual rollouts and A/B testing
4. User preference persistence across sessions
5. Default value management with environment-specific overrides
6. Configuration validation to prevent runtime failures
7. Dynamic configuration updates without application restart

Design Philosophy:
- Security by default: Sensitive data never appears in logs or version control
- Environment awareness: Automatic detection and adaptation to deployment context
- Validation first: Catch configuration errors before they cause runtime failures
- Hierarchical overrides: Default → Environment → User → Runtime precedence
- Type safety: Strong typing prevents configuration-related bugs
- Audit trail: Track configuration changes for debugging and compliance

Why centralized configuration management:
- Consistency: All modules use the same configuration loading and validation logic
- Security: Centralized secret handling prevents accidental exposure
- Maintainability: Single location for configuration schema and validation rules
- Debugging: Centralized logging and error handling for configuration issues
- Testing: Consistent configuration mocking and override mechanisms

Configuration Sources (in precedence order):
1. Runtime overrides (command-line arguments, API calls)
2. User preferences (saved in WebUI settings)
3. Environment variables (deployment-specific settings)
4. Configuration files (defaults and environment-specific overrides)
5. Hardcoded defaults (fallback values for essential settings)

This layered approach enables:
- Development: Local configuration files with debugging enabled
- CI/CD: Environment variables for test-specific settings
- Production: Secure secret injection without file system dependencies
- User customization: Persistent preferences that survive application updates

The module is designed to fail fast on configuration errors during application
startup rather than allowing invalid configurations to cause runtime failures.
This approach makes deployment issues immediately visible and debuggable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Module-level logger for configuration loading, validation, and error reporting
# Configuration errors are often environmental and require detailed context for debugging
# This logger helps track configuration resolution across different sources and environments
logger = logging.getLogger(__name__)

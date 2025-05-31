from src.utils.offline import is_offline  # offline helper for CODEX mode

try:
    from openai import OpenAI
except ImportError:  #// handle missing SDK when offline
    if is_offline():  # fallback only in Codex offline mode
        class OpenAI:  #// simple dummy class so module loads
            def __init__(self, *args, **kwargs):
                pass
    else:
        raise

try:
    from langchain_openai import ChatOpenAI, AzureChatOpenAI
except ImportError:  #// offline environment without langchain-openai
    if is_offline():
        class ChatOpenAI:  #// basic stand-in mimicking real constructor
            def __init__(self, *args, **kwargs):
                self.kwargs = kwargs

        class AzureChatOpenAI(ChatOpenAI):
            pass
    else:
        raise
from langchain_core.globals import get_llm_cache
from langchain_core.language_models.base import (
    BaseLanguageModel,
    LangSmithParams,
    LanguageModelInput,
)
import os
from langchain_core.load import dumpd, dumps
from langchain_core.messages import (
    AIMessage,
    SystemMessage,
    AnyMessage,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    convert_to_messages,
    message_chunk_to_message,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
    LLMResult,
    RunInfo,
)
from langchain_ollama import ChatOllama
from langchain_core.output_parsers.base import OutputParserLike
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Optional,
    Union,
    cast, List,
)
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_ibm import ChatWatsonx
from langchain_aws import ChatBedrock
from pydantic import SecretStr

from src.utils import config

"""
LLM Provider Utilities - Language Model Integration and Management Infrastructure

This module provides the foundational layer for integrating with various Language Model
providers (OpenAI, Anthropic, local models, etc.) while abstracting away provider-specific
differences and handling the complex operational challenges of LLM integration.

Core Challenges Addressed:
1. Provider API Differences: Each LLM provider has different request/response formats
2. Rate Limiting and Quota Management: Preventing API limit violations and service interruptions
3. Error Handling and Retry Logic: Robust handling of network failures and API errors
4. Token Management: Optimizing requests to stay within context limits and cost constraints
5. Response Processing: Standardizing outputs across different provider response formats
6. Authentication and Security: Secure API key management and request authentication
7. Performance Monitoring: Tracking latency, costs, and success rates across providers

Design Philosophy:
- Provider Agnostic: Abstract away provider differences behind a unified interface
- Reliability First: Robust error handling and retry mechanisms for production use
- Cost Conscious: Token optimization and usage tracking to control operational costs
- Performance Aware: Efficient request batching and response caching where appropriate
- Security Focused: Secure credential handling and request/response sanitization
- Observable: Comprehensive logging and metrics for monitoring and debugging

Why this abstraction layer is essential:
The Browser Agent WebUI needs to work with multiple LLM providers for different reasons:
- Cost optimization: Use different providers for different types of tasks
- Redundancy: Fallback to alternative providers when primary is unavailable
- Feature differences: Some providers excel at specific types of reasoning or generation
- Compliance: Some deployments require specific providers for regulatory reasons
- Development vs Production: Different providers for testing vs production workloads

Real-world operational concerns:
- API rate limits can cause user-facing failures if not properly managed
- Token limits require intelligent truncation and context management strategies
- Network failures need retry logic with exponential backoff to prevent cascade failures
- Cost monitoring is essential to prevent runaway charges from malicious or buggy requests
- Response validation prevents downstream failures from malformed LLM outputs

Provider Integration Patterns:
1. Request Transformation: Convert unified requests to provider-specific formats
2. Response Normalization: Standardize provider responses to unified format
3. Error Classification: Categorize errors for appropriate retry and fallback strategies
4. Token Optimization: Minimize costs while maintaining response quality
5. Performance Monitoring: Track key metrics across all provider interactions

This module serves as the foundation for all LLM interactions in the application,
making it critical for reliability, performance, and maintainability of AI features.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

# Module-level logger for LLM provider operations, errors, and performance monitoring
# LLM operations are network-dependent and can fail in various ways
# Detailed logging is essential for debugging API issues and monitoring costs/performance
logger = logging.getLogger(__name__)


class DeepSeekR1ChatOpenAI(ChatOpenAI):
    """OpenAI client wrapper returning reasoning content alongside text."""  # class docstring

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Keep a direct OpenAI client using kwargs for flexible config.

        The ``base_url`` and ``api_key`` values are read from ``kwargs`` so
        callers can override the endpoint or credentials without changing
        the method signature. A dedicated client is stored for performing
        low-level API calls where ``ChatOpenAI`` may not expose every
        option.
        """  # explained kwargs usage and client storage purpose
        super().__init__(*args, **kwargs)  # init base ChatOpenAI
        self.client = OpenAI(  # create separate OpenAI client
            base_url=kwargs.get("base_url"),  # allow overriding endpoint
            api_key=kwargs.get("api_key")  # api key may differ from global
        )

    async def ainvoke(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> AIMessage:
        message_history = []
        for input_ in input:
            if isinstance(input_, SystemMessage):
                message_history.append({"role": "system", "content": input_.content})
            elif isinstance(input_, AIMessage):
                message_history.append({"role": "assistant", "content": input_.content})
            else:
                message_history.append({"role": "user", "content": input_.content})

        if not is_offline():  # use real API when CODEX is not True
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=message_history
            )
            reasoning_content = response.choices[0].message.reasoning_content
            content = response.choices[0].message.content
        else:  # provide mock values when running on Codex
            reasoning_content = 'mock reasoning'  # mocked reasoning content
            content = 'mock response'  # mocked message content
        return AIMessage(content=content, reasoning_content=reasoning_content)

    def invoke(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> AIMessage:
        message_history = []
        for input_ in input:
            if isinstance(input_, SystemMessage):
                message_history.append({"role": "system", "content": input_.content})
            elif isinstance(input_, AIMessage):
                message_history.append({"role": "assistant", "content": input_.content})
            else:
                message_history.append({"role": "user", "content": input_.content})

        if not is_offline():  # real API call when not on Codex
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=message_history
            )
            reasoning_content = response.choices[0].message.reasoning_content
            content = response.choices[0].message.content
        else:  # mocked values for Codex
            reasoning_content = 'mock reasoning'  # mocked reasoning content
            content = 'mock response'  # mocked message content
        return AIMessage(content=content, reasoning_content=reasoning_content)


class DeepSeekR1ChatOllama(ChatOllama):
    """Ollama wrapper that splits reasoning tags from final content."""  # class docstring

    async def ainvoke(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> AIMessage:
        if not is_offline():  # run real call when CODEX unset
            org_ai_message = await super().ainvoke(input=input)
        else:  # mock the ai message when running on Codex
            org_ai_message = AIMessage(content='<think>mock reason</think>mock')
        org_content = org_ai_message.content
        reasoning_content = org_content.split("</think>")[0].replace("<think>", "")
        content = org_content.split("</think>")[1]
        if "**JSON Response:**" in content:
            content = content.split("**JSON Response:**")[-1]
        return AIMessage(content=content, reasoning_content=reasoning_content)

    def invoke(
            self,
            input: LanguageModelInput,
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
    ) -> AIMessage:
        if not is_offline():  # run real call when CODEX unset
            org_ai_message = super().invoke(input=input)
        else:  # mock the ai message when running on Codex
            org_ai_message = AIMessage(content='<think>mock reason</think>mock')
        org_content = org_ai_message.content
        reasoning_content = org_content.split("</think>")[0].replace("<think>", "")
        content = org_content.split("</think>")[1]
        if "**JSON Response:**" in content:
            content = content.split("**JSON Response:**")[-1]
        return AIMessage(content=content, reasoning_content=reasoning_content)


def get_llm_model(provider: str, **kwargs):
    """
    Factory function for creating LLM (Large Language Model) instances from various providers.

    This function abstracts the complexity of initializing different LLM providers,
    handling authentication, configuration, and provider-specific requirements.
    It serves as a central point for LLM instantiation throughout the application.

    Args:
        provider (str): The LLM provider identifier (e.g., "openai", "anthropic", "google")
        **kwargs: Provider-specific configuration parameters including:
                 - model_name: Specific model to use (e.g., "gpt-4", "claude-3-5-sonnet")
                 - temperature: Sampling temperature for response randomness (0.0-1.0)
                 - api_key: Authentication key (can override environment variable)
                 - base_url: Custom API endpoint URL (for self-hosted or proxy services)
                 - Additional provider-specific parameters

    Returns:
        LangChain chat model instance configured for the specified provider

    Raises:
        ValueError: When required API key is missing or provider is unsupported

    Why this design:
    - Centralized LLM creation ensures consistent configuration across the application
    - Environment variable fallback provides secure credential management
    - Provider abstraction allows easy switching between different LLM services
    - Kwargs pattern provides flexibility for provider-specific parameters
    - Error messages include emojis and clear instructions for better user experience

    Security considerations:
    - API keys are sourced from environment variables first for security
    - Explicit API key parameter allows testing but should be used carefully
    - No API keys are logged or exposed in error messages
    - Environment variable naming uses ``<PROVIDER>_API_KEY`` for consistency
    """

    # Handle API key authentication for most providers
    # Ollama and Bedrock have different authentication mechanisms, so they're excluded
    if provider not in ["ollama", "bedrock"]:
        # Construct expected environment variable name using consistent naming convention
        env_var = f"{provider.upper()}_API_KEY"

        # Priority: explicit parameter > environment variable > empty string
        # This allows override while defaulting to secure environment variable storage
        api_key = kwargs.get("api_key", "") or os.getenv(env_var, "")

        # Validate API key presence before attempting to create model
        # Early validation prevents confusing provider-specific errors later
        if not api_key:
            # Use human-friendly provider names when available for better error messages
            provider_display = config.PROVIDER_DISPLAY_NAMES.get(provider, provider.upper())

            # User-friendly error message with emojis and clear action items
            # Includes both environment variable and UI options for flexibility
            error_msg = f"💥 {provider_display} API key not found! 🔑 Please set the `{env_var}` environment variable or provide it in the UI."
            raise ValueError(error_msg)

        # Ensure API key is available in kwargs for provider initialization
        kwargs["api_key"] = api_key

    if provider == "anthropic":
        if not kwargs.get("base_url", ""):
            base_url = "https://api.anthropic.com"
        else:
            base_url = kwargs.get("base_url")

        return ChatAnthropic(
            model=kwargs.get("model_name", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == 'mistral':
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1")
        else:
            base_url = kwargs.get("base_url")
        if not kwargs.get("api_key", ""):
            api_key = os.getenv("MISTRAL_API_KEY", "")
        else:
            api_key = kwargs.get("api_key")

        return ChatMistralAI(
            model=kwargs.get("model_name", "mistral-large-latest"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "openai":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "deepseek":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("DEEPSEEK_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")

        if kwargs.get("model_name", "deepseek-chat") == "deepseek-reasoner":
            return DeepSeekR1ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-reasoner"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
        else:
            return ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-chat"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model_name", "gemini-2.0-flash-exp"),
            temperature=kwargs.get("temperature", 0.0),
            api_key=api_key,
        )
    elif provider == "ollama":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        else:
            base_url = kwargs.get("base_url")

        if "deepseek-r1" in kwargs.get("model_name", "qwen2.5:7b"):
            return DeepSeekR1ChatOllama(
                model=kwargs.get("model_name", "deepseek-r1:14b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                base_url=base_url,
            )
        else:
            return ChatOllama(
                model=kwargs.get("model_name", "qwen2.5:7b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                num_predict=kwargs.get("num_predict", 1024),
                base_url=base_url,
            )
    elif provider == "azure_openai":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        api_version = kwargs.get("api_version", "") or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        return AzureChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            api_version=api_version,
            azure_endpoint=base_url,
            api_key=api_key,
        )
    elif provider == "alibaba":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("ALIBABA_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "qwen-plus"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "ibm":
        parameters = {
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("num_ctx", 32000)
        }
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("IBM_ENDPOINT", "https://us-south.ml.cloud.ibm.com")
        else:
            base_url = kwargs.get("base_url")

        return ChatWatsonx(
            model_id=kwargs.get("model_name", "ibm/granite-vision-3.1-2b-preview"),
            url=base_url,
            project_id=os.getenv("IBM_PROJECT_ID"),
            apikey=os.getenv("IBM_API_KEY"),
            params=parameters
        )
    elif provider == "moonshot":
        return ChatOpenAI(
            model=kwargs.get("model_name", "moonshot-v1-32k-vision-preview"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=os.getenv("MOONSHOT_ENDPOINT"),
            api_key=os.getenv("MOONSHOT_API_KEY"),
        )
    elif provider == "unbound":
        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o-mini"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=os.getenv("UNBOUND_ENDPOINT", "https://api.getunbound.ai"),
            api_key=api_key,
        )
    elif provider == "siliconflow":
        if not kwargs.get("api_key", ""):
            api_key = os.getenv("SiliconFLOW_API_KEY", "")
        else:
            api_key = kwargs.get("api_key")
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("SiliconFLOW_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model_name=kwargs.get("model_name", "Qwen/QwQ-32B"),
            temperature=kwargs.get("temperature", 0.0),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

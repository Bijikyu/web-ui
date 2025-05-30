import types
import sys

# Stub gradio and langchain_core modules for import
sys.modules.setdefault('gradio', types.ModuleType('gradio'))
grado = sys.modules['gradio']
setattr(grado, 'Warning', lambda *a, **k: None)
sys.modules.setdefault('langchain_core', types.ModuleType('langchain_core'))
sys.modules.setdefault('langchain_core.language_models', types.ModuleType('langchain_core.language_models'))
chat_mod = types.ModuleType('langchain_core.language_models.chat_models')
chat_mod.BaseChatModel = type('BaseChatModel', (), {})
sys.modules.setdefault('langchain_core.language_models.chat_models', chat_mod)
llm_stub = types.ModuleType('src.utils.llm_provider')
llm_stub.get_llm_model = lambda *a, **k: None
sys.modules.setdefault('src.utils.llm_provider', llm_stub)

sys.path.append('.')

import asyncio
from unittest.mock import patch

from src.utils.agent_utils import initialize_llm


def test_initialize_llm_missing_fields():
    """Return None when provider or model fields are missing."""  #(added docstring summarizing test intent)
    # missing provider or model returns None
    result = asyncio.run(initialize_llm(None, 'm', 0.5, None, None))
    assert result is None
    result = asyncio.run(initialize_llm('p', None, 0.5, None, None))
    assert result is None


def test_initialize_llm_success():
    """Successfully initialize LLM and verify parameter passing."""  #(added docstring summarizing test intent)
    # successful initialization returns model
    mock_model = object()
    with patch('src.utils.agent_utils.llm_provider.get_llm_model', return_value=mock_model) as get_model:
        result = asyncio.run(initialize_llm('openai', 'gpt', 0.3, 'url', 'key'))
    get_model.assert_called_once_with(
        provider='openai',
        model_name='gpt',
        temperature=0.3,
        base_url='url',
        api_key='key',
        num_ctx=None,
    )
    assert result is mock_model


def test_initialize_llm_exception():
    """Return None and log errors when LLM initialization fails."""  #(added docstring summarizing test intent)
    # errors during creation are logged and None returned
    with patch('src.utils.agent_utils.llm_provider.get_llm_model', side_effect=Exception('boom')):
        with patch('src.utils.agent_utils.logger') as log:
            with patch('src.utils.agent_utils.gr.Warning') as warn:
                result = asyncio.run(initialize_llm('openai', 'gpt', 0.3, None, 'key'))
                log.error.assert_called()
                warn.assert_called()
    assert result is None

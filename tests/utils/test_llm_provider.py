import sys
import types
import importlib
import pytest

sys.path.append('.')  # (allow src imports)


class Dummy:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def stub_module(name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod


# Stub external modules so llm_provider imports without network packages
stub_module('openai', {'OpenAI': Dummy})  # (create fake OpenAI class)
stub_module('langchain_openai', {'ChatOpenAI': Dummy, 'AzureChatOpenAI': Dummy})  # (fake openai classes)
stub_module('langchain_ollama', {'ChatOllama': Dummy})  # (fake ollama class)
stub_module('langchain_anthropic', {'ChatAnthropic': Dummy})  # (fake anthropic)
stub_module('langchain_mistralai', {'ChatMistralAI': Dummy})  # (fake mistral)
stub_module('langchain_google_genai', {'ChatGoogleGenerativeAI': Dummy})  # (fake google)
stub_module('langchain_ibm', {'ChatWatsonx': Dummy})  # (fake ibm)
stub_module('langchain_aws', {'ChatBedrock': Dummy})  # (fake aws)
stub_module('pydantic', {'SecretStr': Dummy})  # (fake SecretStr class)

stub_module('langchain_core.globals', {'get_llm_cache': lambda: None})  # (fake util)
stub_module(
    'langchain_core.language_models.base',
    {
        'BaseLanguageModel': Dummy,
        'LangSmithParams': Dummy,
        'LanguageModelInput': list,
    },
)  # (fake base classes)
stub_module('langchain_core.load', {'dumpd': lambda *a, **k: {}, 'dumps': lambda *a, **k: ''})  # (fake dumps)
stub_module(
    'langchain_core.messages',
    {
        'AIMessage': Dummy,
        'SystemMessage': Dummy,
        'AnyMessage': Dummy,
        'BaseMessage': Dummy,
        'BaseMessageChunk': Dummy,
        'HumanMessage': Dummy,
        'convert_to_messages': lambda x: x,
        'message_chunk_to_message': lambda x: x,
    },
)  # (fake messages)
stub_module(
    'langchain_core.outputs',
    {
        'ChatGeneration': Dummy,
        'ChatGenerationChunk': Dummy,
        'ChatResult': Dummy,
        'LLMResult': Dummy,
        'RunInfo': Dummy,
    },
)  # (fake outputs)
stub_module('langchain_core.output_parsers.base', {'OutputParserLike': Dummy})  # (fake parser)
stub_module('langchain_core.runnables', {'Runnable': Dummy, 'RunnableConfig': Dummy})  # (fake runnables)
stub_module('langchain_core.tools', {'BaseTool': Dummy})  # (fake tools)

llm_provider = importlib.import_module('src.utils.llm_provider')  # (import target module)


def test_openai_requires_key(monkeypatch):
    """Ensure an API key is required for OpenAI provider."""  #(added docstring summarizing test intent)
    # missing API key raises error
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)  # (clear env var)
    with pytest.raises(ValueError):  # (expect error)
        llm_provider.get_llm_model('openai')  # (call provider)


def test_openai_custom_params(monkeypatch):
    """Custom parameters should override OpenAI defaults."""  #(added docstring summarizing test intent)
    # custom params override defaults
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')  # (set env var)
    model = llm_provider.get_llm_model(
        'openai', base_url='http://api', temperature=0.5
    )  # (create openai model)
    assert isinstance(model, llm_provider.ChatOpenAI)  # (instance check)
    assert model.kwargs['base_url'] == 'http://api'  # (verify base_url)
    assert model.kwargs['temperature'] == 0.5  # (verify temperature)


def test_ollama_custom_params(monkeypatch):
    """Ollama provider should honor provided override parameters."""  #(added docstring summarizing test intent)
    # ollama provider honors overrides
    monkeypatch.delenv('OLLAMA_ENDPOINT', raising=False)  # (clear env var)
    model = llm_provider.get_llm_model(
        'ollama', base_url='http://ollama', temperature=0.1
    )  # (create ollama model)
    assert isinstance(model, llm_provider.ChatOllama)  # (instance check)
    assert model.kwargs['base_url'] == 'http://ollama'  # (verify base_url)
    assert model.kwargs['temperature'] == 0.1  # (verify temperature)


def test_anthropic_requires_key(monkeypatch):
    """Anthropic provider should raise when API key missing."""  #(added docstring summarizing test intent)
    # anthropic needs API key
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)  #(description of change & current functionality)
    with pytest.raises(ValueError):  #(description of change & current functionality)
        llm_provider.get_llm_model('anthropic')  #(description of change & current functionality)


def test_anthropic_custom_params(monkeypatch):
    """Anthropic provider should accept and use custom parameters."""  #(added docstring summarizing test intent)
    # anthropic with overrides works
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'ant-test')  #(description of change & current functionality)
    model = llm_provider.get_llm_model(  #(description of change & current functionality)
        'anthropic', base_url='https://anthropic', temperature=0.2  #(description of change & current functionality)
    )  #(description of change & current functionality)
    assert isinstance(model, llm_provider.ChatAnthropic)  #(description of change & current functionality)
    assert model.kwargs['base_url'] == 'https://anthropic'  #(description of change & current functionality)
    assert model.kwargs['temperature'] == 0.2  #(description of change & current functionality)


def test_ollama_no_key(monkeypatch):
    """Ollama provider works without an explicit API key."""  #(added docstring summarizing test intent)
    # ollama works without explicit key
    monkeypatch.delenv('OLLAMA_ENDPOINT', raising=False)  #(description of change & current functionality)
    model = llm_provider.get_llm_model('ollama')  #(description of change & current functionality)
    assert isinstance(model, llm_provider.ChatOllama)  #(description of change & current functionality)

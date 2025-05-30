import sys
import types
import importlib
import asyncio
import json

sys.path.append('.')

class Dummy:
    def __init__(self, *a, **k):
        self.args = a
        self.kwargs = k


def stub_module(monkeypatch, name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def load_agent_settings_tab(monkeypatch):
    stubs = [
        ('openai', {'OpenAI': Dummy}),
        ('langchain_openai', {'ChatOpenAI': Dummy, 'AzureChatOpenAI': Dummy}),
        ('langchain_ollama', {'ChatOllama': Dummy}),
        ('langchain_anthropic', {'ChatAnthropic': Dummy}),
        ('langchain_mistralai', {'ChatMistralAI': Dummy}),
        ('langchain_google_genai', {'ChatGoogleGenerativeAI': Dummy}),
        ('langchain_ibm', {'ChatWatsonx': Dummy}),
        ('langchain_aws', {'ChatBedrock': Dummy}),
        ('pydantic', {'SecretStr': Dummy}),
        ('langchain_core.globals', {'get_llm_cache': lambda: None}),
        ('langchain_core.language_models.base', {
            'BaseLanguageModel': Dummy,
            'LangSmithParams': Dummy,
            'LanguageModelInput': list,
        }),
        ('langchain_core.load', {'dumpd': lambda *a, **k: {}, 'dumps': lambda *a, **k: ''}),
        ('langchain_core.messages', {
            'AIMessage': Dummy,
            'SystemMessage': Dummy,
            'AnyMessage': Dummy,
            'BaseMessage': Dummy,
            'BaseMessageChunk': Dummy,
            'HumanMessage': Dummy,
            'convert_to_messages': lambda x: x,
            'message_chunk_to_message': lambda x: x,
        }),
        ('langchain_core.outputs', {
            'ChatGeneration': Dummy,
            'ChatGenerationChunk': Dummy,
            'ChatResult': Dummy,
            'LLMResult': Dummy,
            'RunInfo': Dummy,
        }),
        ('langchain_core.output_parsers.base', {'OutputParserLike': Dummy}),
        ('langchain_core.runnables', {'Runnable': Dummy, 'RunnableConfig': Dummy}),
        ('langchain_core.tools', {'BaseTool': Dummy}),
    ]
    for name, attrs in stubs:
        stub_module(monkeypatch, name, attrs)

    gradio = stub_module(monkeypatch, 'gradio')
    components = stub_module(monkeypatch, 'gradio.components')

    class DummyDropdown:
        def __init__(self, choices=None, value=None, interactive=True, allow_custom_value=False):
            self.choices = choices
            self.value = value
            self.interactive = interactive
            self.allow_custom_value = allow_custom_value

    class DummyUpdate(dict):
        pass

    class DummyButton:  # for other tests patching
        pass

    class DummyFile:
        pass

    def update(**kwargs):
        return DummyUpdate(kwargs)

    components.Component = DummyDropdown
    gradio.Dropdown = DummyDropdown
    gradio.update = update
    gradio.components = components
    gradio.Button = DummyButton
    gradio.File = DummyFile

    sys.modules.pop('src.webui.components.agent_settings_tab', None)
    return importlib.import_module('src.webui.components.agent_settings_tab')


class DummyController:
    def __init__(self):
        self.closed = False

    async def close_mcp_client(self):
        self.closed = True


class DummyManager:
    def __init__(self, controller=None):
        self.bu_controller = controller


def test_update_model_dropdown_known(monkeypatch):
    """Selecting a known provider populates the model dropdown."""  #(added docstring summarizing test intent)
    # provider known -> dropdown populated
    mod = load_agent_settings_tab(monkeypatch)
    dd = mod.update_model_dropdown('openai')
    assert dd.choices == mod.config.model_names['openai']
    assert dd.value == mod.config.model_names['openai'][0]
    assert dd.interactive


def test_update_model_dropdown_unknown(monkeypatch):
    """Unknown provider yields an empty, customisable dropdown."""  #(added docstring summarizing test intent)
    # unknown provider -> empty dropdown
    mod = load_agent_settings_tab(monkeypatch)
    dd = mod.update_model_dropdown('foo')
    assert dd.choices == []
    assert dd.value == ''
    assert dd.allow_custom_value


def test_update_mcp_server_invalid(monkeypatch, tmp_path):
    """Hide MCP config UI when file does not exist."""  #(added docstring summarizing test intent)
    # invalid path hides config
    mod = load_agent_settings_tab(monkeypatch)
    mgr = DummyManager()
    result = asyncio.run(mod.update_mcp_server(str(tmp_path / 'no.json'), mgr))
    assert result == (None, mod.gr.update(visible=False))


def test_update_mcp_server_valid(monkeypatch, tmp_path):
    """Load MCP server configuration from JSON file."""  #(added docstring summarizing test intent)
    # valid path loads config JSON
    mod = load_agent_settings_tab(monkeypatch)
    data = {'a': 1}
    json_file = tmp_path / 'cfg.json'
    json_file.write_text(json.dumps(data))
    ctrl = DummyController()
    mgr = DummyManager(ctrl)
    text, upd = asyncio.run(mod.update_mcp_server(str(json_file), mgr))
    assert text == json.dumps(data, indent=2)
    assert upd == mod.gr.update(visible=True)
    assert ctrl.closed
    assert mgr.bu_controller is None

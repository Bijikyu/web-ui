import importlib
import sys
import types
import json
import pytest

sys.path.append(".")  # allow src imports


def install_stubs():
    """Add stub modules so the browser use tab imports without heavy deps."""  #(added docstring explaining helper purpose)
    gradio_mod = types.ModuleType("gradio")
    comps_mod = types.ModuleType("gradio.components")
    class Component:
        pass
    comps_mod.Component = Component
    gradio_mod.components = comps_mod
    themes_mod = types.ModuleType("gradio.themes")
    for name in ["Default", "Soft", "Monochrome", "Glass", "Origin", "Citrus", "Ocean", "Base"]:
        setattr(themes_mod, name, type(name, (), {}))
    gradio_mod.themes = themes_mod

    modules = {
        "gradio": gradio_mod,
        "gradio.components": comps_mod,
        "gradio.themes": themes_mod,
        "browser_use": types.ModuleType("browser_use"),
        "browser_use.browser": types.ModuleType("browser_use.browser"),
        "browser_use.agent": types.ModuleType("browser_use.agent"),
        "browser_use.agent.views": types.ModuleType("browser_use.agent.views"),
        "browser_use.browser.browser": types.ModuleType("browser_use.browser.browser"),
        "browser_use.browser.context": types.ModuleType("browser_use.browser.context"),
        "browser_use.browser.views": types.ModuleType("browser_use.browser.views"),
        "src.agent.browser_use.browser_use_agent": types.ModuleType("src.agent.browser_use.browser_use_agent"),
        "src.browser.custom_browser": types.ModuleType("src.browser.custom_browser"),
        "src.browser.custom_context": types.ModuleType("src.browser.custom_context"),
        "src.controller.custom_controller": types.ModuleType("src.controller.custom_controller"),
        "src.utils.agent_utils": types.ModuleType("src.utils.agent_utils"),
        "src.utils.browser_launch": types.ModuleType("src.utils.browser_launch"),
        "src.webui.webui_manager": types.ModuleType("src.webui.webui_manager"),
        "langchain_core.language_models.chat_models": types.ModuleType("langchain_core.language_models.chat_models"),
    }

    modules["browser_use.agent.views"].AgentHistoryList = type("AgentHistoryList", (), {})
    modules["browser_use.agent.views"].AgentOutput = type("AgentOutput", (), {})
    modules["browser_use.browser.browser"].BrowserConfig = type("BrowserConfig", (), {})
    modules["browser_use.browser.context"].BrowserContext = type("BrowserContext", (), {})
    modules["browser_use.browser.views"].BrowserState = type("BrowserState", (), {})
    modules["src.agent.browser_use.browser_use_agent"].BrowserUseAgent = type("BrowserUseAgent", (), {})
    modules["src.browser.custom_browser"].CustomBrowser = type("CustomBrowser", (), {})
    modules["src.browser.custom_context"].CustomBrowserContextConfig = type("CustomBrowserContextConfig", (), {})
    modules["src.controller.custom_controller"].CustomController = type("CustomController", (), {})
    modules["src.utils.agent_utils"].initialize_llm = lambda *a, **k: None
    modules["src.utils.browser_launch"].build_browser_launch_options = lambda *a, **k: (None, [])

    class DummyWebuiManager:
        def __init__(self):
            self.comps = {}
        def get_component_by_id(self, cid):
            return self.comps[cid]
    modules["src.webui.webui_manager"].WebuiManager = DummyWebuiManager
    modules["langchain_core.language_models.chat_models"].BaseChatModel = type("BaseChatModel", (), {})

    original = {}
    for name, mod in modules.items():
        original[name] = sys.modules.get(name)
        sys.modules[name] = mod
    return original, DummyWebuiManager


def remove_stubs(original):
    """Restore original modules replaced by install_stubs."""  #(added docstring describing cleanup)
    for name, mod in original.items():
        if mod is not None:
            sys.modules[name] = mod
    sys.modules.pop("src.webui.components.browser_use_agent_tab", None)


@pytest.fixture
def helpers_module():
    original, DummyWebuiManager = install_stubs()
    module = importlib.import_module("src.webui.components.browser_use_agent_tab")
    yield module, DummyWebuiManager
    remove_stubs(original)


class DummyComponent:
    pass


class Dumpable:
    def __init__(self, data):
        self.data = data
    def model_dump(self, exclude_none=True):
        return {"data": self.data}


class AgentOutputLike:
    def __init__(self, action, current_state):
        self.action = action
        self.current_state = current_state


def test_get_config_value_primary_tab(helpers_module):
    """Retrieve configuration value from the active tab components."""  #(added docstring summarizing test intent)
    # fetch value from primary tab
    mod, WebuiManager = helpers_module
    manager = WebuiManager()
    comp = DummyComponent()
    manager.comps = {"browser_use_agent.test": comp}
    comp_dict = {comp: 42}
    assert mod._get_config_value(manager, comp_dict, "test", "def") == 42


def test_get_config_value_fallback_tabs(helpers_module):
    """Look for configuration values in alternate tabs when absent."""  #(added docstring summarizing test intent)
    # fallback to other tabs when missing
    mod, WebuiManager = helpers_module
    manager = WebuiManager()
    comp = DummyComponent()
    manager.comps = {"agent_settings.test": comp}
    comp_dict = {comp: "ok"}
    assert mod._get_config_value(manager, comp_dict, "test", None) == "ok"


def test_get_config_value_default(helpers_module):
    """Return provided default when value is missing in all tabs."""  #(added docstring summarizing test intent)
    # use provided default when absent
    mod, WebuiManager = helpers_module
    manager = WebuiManager()
    manager.comps = {}
    assert mod._get_config_value(manager, {}, "missing", "dft") == "dft"


def test_format_agent_output_json(helpers_module):
    """Convert AgentOutput object to formatted JSON markup."""  #(added docstring summarizing test intent)
    # format AgentOutput to JSON block
    mod, _ = helpers_module
    ao = AgentOutputLike([Dumpable("a")], Dumpable("s"))
    res = mod._format_agent_output(ao)
    prefix = "<pre><code class='language-json'>"
    suffix = "</code></pre>"
    assert res.startswith(prefix) and res.endswith(suffix)
    data = json.loads(res[len(prefix):-len(suffix)])
    assert data == {"current_state": {"data": "s"}, "action": [{"data": "a"}]}


def test_format_agent_output_attribute_error(helpers_module):
    """Handle objects without model_dump when formatting output."""  #(added docstring summarizing test intent)
    # handle objects lacking model_dump
    mod, _ = helpers_module
    class NoDump:
        pass
    ao = AgentOutputLike([NoDump()], NoDump())
    res = mod._format_agent_output(ao)
    assert "Could not format agent output" in res
    assert "Raw output" in res

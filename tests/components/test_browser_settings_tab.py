import types
import sys
import asyncio
import pytest

sys.path.append(".")  # allow importing src modules

# Stub browser_use package to satisfy imports
browser_use = types.ModuleType("browser_use")
browser_mod = types.ModuleType("browser_use.browser")
browser_browser = types.ModuleType("browser_use.browser.browser")
browser_context = types.ModuleType("browser_use.browser.context")
agent_mod = types.ModuleType("browser_use.agent")
agent_service = types.ModuleType("browser_use.agent.service")
agent_views = types.ModuleType("browser_use.agent.views")

class Browser:
    pass

class BrowserContext:
    pass

class Agent:
    pass

browser_browser.Browser = Browser
browser_browser.IN_DOCKER = False
class BrowserContextConfig:
    pass

class BrowserContextState:
    pass

browser_context.BrowserContext = BrowserContext
browser_context.BrowserContextConfig = BrowserContextConfig
browser_context.BrowserContextState = BrowserContextState
agent_service.Agent = Agent

sys.modules.setdefault("browser_use", browser_use)
sys.modules.setdefault("browser_use.browser", browser_mod)
sys.modules.setdefault("browser_use.browser.browser", browser_browser)
sys.modules.setdefault("browser_use.browser.context", browser_context)
sys.modules.setdefault("browser_use.agent", agent_mod)
sys.modules.setdefault("browser_use.agent.service", agent_service)
sys.modules.setdefault("browser_use.agent.views", agent_views)

# Stub patchright.async_api module for browser imports
patchright_async = types.ModuleType("patchright.async_api")

class PWBrowser:
    pass

class PWBrowserContext:
    pass

class Playwright:
    pass

async def async_playwright():
    class Dummy:
        async def __aenter__(self):
            return Playwright()
        async def __aexit__(self, exc_type, exc, tb):
            pass
    return Dummy()

patchright_async.Browser = PWBrowser
patchright_async.BrowserContext = PWBrowserContext
patchright_async.Playwright = Playwright
patchright_async.async_playwright = async_playwright

sys.modules.setdefault("patchright.async_api", patchright_async)

# Stub additional browser_use modules referenced during import
chrome_mod = types.ModuleType("browser_use.browser.chrome")
chrome_mod.CHROME_ARGS = []
chrome_mod.CHROME_DETERMINISTIC_RENDERING_ARGS = []
chrome_mod.CHROME_DISABLE_SECURITY_ARGS = []
chrome_mod.CHROME_DOCKER_ARGS = []
chrome_mod.CHROME_HEADLESS_ARGS = []

screen_res_mod = types.ModuleType("browser_use.browser.utils.screen_resolution")
def get_screen_resolution():
    return {"width": 1920, "height": 1080}
def get_window_adjustments():
    return (0, 0)
screen_res_mod.get_screen_resolution = get_screen_resolution
screen_res_mod.get_window_adjustments = get_window_adjustments

utils_mod = types.ModuleType("browser_use.utils")
async def time_execution_async(*args, **kwargs):
    pass
utils_mod.time_execution_async = time_execution_async

sys.modules.setdefault("browser_use.browser.chrome", chrome_mod)
sys.modules.setdefault("browser_use.browser.utils.screen_resolution", screen_res_mod)
sys.modules.setdefault("browser_use.utils", utils_mod)

# Minimal pydantic stub with BaseModel for imports
pydantic_stub = types.ModuleType("pydantic")
class BaseModel:
    pass
pydantic_stub.BaseModel = BaseModel
sys.modules.setdefault("pydantic", pydantic_stub)

# Minimal WebuiManager stub to avoid heavy dependencies
webui_manager_mod = types.ModuleType("src.webui.webui_manager")

class WebuiManager:
    def __init__(self):
        self.id_to_component = {}
        self.component_to_id = {}
        self.init_browser_use_agent()

    def init_browser_use_agent(self):
        self.bu_agent = None
        self.bu_browser = None
        self.bu_browser_context = None
        self.bu_controller = None
        self.bu_chat_history = []
        self.bu_response_event = None
        self.bu_user_help_response = None
        self.bu_current_task = None
        self.bu_agent_task_id = None

    def add_components(self, tab_name, components_dict):
        for name, comp in components_dict.items():
            comp_id = f"{tab_name}.{name}"
            self.id_to_component[comp_id] = comp
            self.component_to_id[comp] = comp_id

    def get_components(self):
        return list(self.id_to_component.values())

    def get_component_by_id(self, comp_id):
        return self.id_to_component[comp_id]

    def get_id_by_component(self, comp):
        return self.component_to_id[comp]

webui_manager_mod.WebuiManager = WebuiManager
sys.modules.setdefault("src.webui.webui_manager", webui_manager_mod)
# Build minimal gradio stubs for component creation
stub = types.ModuleType("gradio")
components = types.ModuleType("gradio.components")

class DummyComp:
    def __init__(self, *args, **kwargs):
        self.fn = None
    def change(self, fn):
        self.fn = fn

class Checkbox(DummyComp):
    pass
class Textbox(DummyComp):
    pass
class Number(DummyComp):
    pass
class Group:
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
class Row(Group):
    pass
class Column(Group):
    pass

components.Component = DummyComp
stub.Checkbox = Checkbox
stub.Textbox = Textbox
stub.Number = Number
stub.Group = Group
stub.Row = Row
stub.Column = Column
stub.components = components

sys.modules.setdefault("gradio", stub)
sys.modules.setdefault("gradio.components", components)

from src.webui.components import browser_settings_tab
from src.webui.webui_manager import WebuiManager

class FakeTask:
    def __init__(self):
        self.cancel_called = False
    def cancel(self):
        self.cancel_called = True
    def done(self):
        return False

def test_checkbox_change_triggers_cleanup(monkeypatch):
    manager = WebuiManager()
    manager.init_browser_use_agent()

    async def fake_cleanup(browser, context):
        fake_cleanup.called = True
    fake_cleanup.called = False

    monkeypatch.setattr(browser_settings_tab, "close_browser_resources", fake_cleanup)

    browser_settings_tab.create_browser_settings_tab(manager)

    manager.bu_browser = object()
    manager.bu_browser_context = object()
    manager.bu_current_task = FakeTask()

    checkboxes = [
        manager.get_component_by_id("browser_settings.headless"),
        manager.get_component_by_id("browser_settings.keep_browser_open"),
        manager.get_component_by_id("browser_settings.disable_security"),
        manager.get_component_by_id("browser_settings.use_own_browser"),
    ]

    for cb in checkboxes:
        asyncio.run(cb.fn())
        assert fake_cleanup.called
        assert manager.bu_browser is None
        assert manager.bu_browser_context is None
        assert manager.bu_current_task is None
        fake_cleanup.called = False
        manager.bu_browser = object()
        manager.bu_browser_context = object()
        manager.bu_current_task = FakeTask()

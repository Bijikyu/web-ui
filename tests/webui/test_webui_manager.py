import json
import shutil
import sys
import types

sys.path.append(".")

class DummyComponent:
    def __init__(self, value=None, interactive=True):
        self.value = value
        self.interactive = interactive


class DummyButton(DummyComponent):
    pass


class DummyFile(DummyComponent):
    pass


class DummyChatbot(DummyComponent):
    pass

gradio = types.ModuleType("gradio")
components_module = types.ModuleType("gradio.components")
setattr(components_module, "Component", DummyComponent)
setattr(gradio, "components", components_module)
setattr(gradio, "Button", DummyButton)
setattr(gradio, "File", DummyFile)
sys.modules["gradio"] = gradio
sys.modules["gradio.components"] = components_module

# Stub external browser_use package
browser_use = types.ModuleType("browser_use")
browser_use.browser = types.ModuleType("browser_use.browser")
browser_use.browser.browser = types.ModuleType("browser_use.browser.browser")
browser_use.browser.context = types.ModuleType("browser_use.browser.context")
browser_use.agent = types.ModuleType("browser_use.agent")
browser_use.agent.service = types.ModuleType("browser_use.agent.service")
setattr(browser_use.browser.browser, "Browser", object)
setattr(browser_use.browser.context, "BrowserContext", object)
setattr(browser_use.agent.service, "Agent", object)
sys.modules["browser_use"] = browser_use
sys.modules["browser_use.browser"] = browser_use.browser
sys.modules["browser_use.browser.browser"] = browser_use.browser.browser
sys.modules["browser_use.browser.context"] = browser_use.browser.context
sys.modules["browser_use.agent"] = browser_use.agent
sys.modules["browser_use.agent.service"] = browser_use.agent.service

# Stub internal modules to avoid heavy dependencies
custom_browser = types.ModuleType("src.browser.custom_browser")
class CustomBrowser: ...
custom_browser.CustomBrowser = CustomBrowser
sys.modules["src.browser.custom_browser"] = custom_browser

custom_context = types.ModuleType("src.browser.custom_context")
class CustomBrowserContext: ...
custom_context.CustomBrowserContext = CustomBrowserContext
sys.modules["src.browser.custom_context"] = custom_context

custom_controller = types.ModuleType("src.controller.custom_controller")
class CustomController: ...
custom_controller.CustomController = CustomController
sys.modules["src.controller.custom_controller"] = custom_controller

deep_agent = types.ModuleType("src.agent.deep_research.deep_research_agent")
class DeepResearchAgent: ...
deep_agent.DeepResearchAgent = DeepResearchAgent
sys.modules["src.agent.deep_research.deep_research_agent"] = deep_agent

import pytest

from src.webui.webui_manager import WebuiManager


@pytest.fixture(autouse=True)
def patch_gradio(monkeypatch):
    from src import webui
    if webui.webui_manager is None:
        pytest.skip("webui_manager unavailable", allow_module_level=True)  # (skip if gradio missing)
    monkeypatch.setattr(webui.webui_manager.gr, "Button", DummyButton)
    monkeypatch.setattr(webui.webui_manager.gr, "File", DummyFile)
    yield


def test_add_get_and_value(tmp_path):
    manager = WebuiManager(settings_save_dir=str(tmp_path))
    comp = DummyComponent()
    manager.add_components("tab", {"input": comp})

    assert manager.get_component_by_id("tab.input") is comp
    assert manager.get_component_value({comp: "val"}, "tab", "input") == "val"


def test_save_and_load(tmp_path):
    manager = WebuiManager(settings_save_dir=str(tmp_path))
    comp = DummyComponent()
    button = DummyButton()
    file_comp = DummyFile()
    status = DummyComponent(interactive=False)
    manager.add_components("settings", {"comp": comp, "button": button, "file": file_comp})
    manager.add_components("load_save_config", {"config_status": status})

    config_path = manager.save_config({comp: "value", button: "", file_comp: "", status: ""})
    with open(config_path) as fr:
        data = json.load(fr)
    assert data == {"settings.comp": "value"}

    update = next(manager.load_config(config_path))
    assert isinstance(update[comp], DummyComponent)
    assert update[comp].value == "value"
    assert status in update
    assert str(config_path) in update[status].value


def test_get_most_recent_invalid_path(tmp_path):
    path = tmp_path / "missing"
    manager = WebuiManager(settings_save_dir=str(path))
    shutil.rmtree(path)
    assert manager.get_most_recent_config() is None


def test_get_most_recent_no_files(tmp_path):
    manager = WebuiManager(settings_save_dir=str(tmp_path))
    assert manager.get_most_recent_config() is None

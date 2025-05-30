import importlib
import sys
import types
import asyncio
sys.path.append(".")


def load_tab(monkeypatch):
    # gradio stubs
    gradio = types.ModuleType("gradio")
    comps = types.ModuleType("gradio.components")

    class DummyComponent:
        def __init__(self, value=None, interactive=True, placeholder=None):
            self.value = value
            self.interactive = interactive
            self.placeholder = placeholder

    class DummyUpdate(dict):
        pass

    def update(**kwargs):
        return DummyUpdate(kwargs)

    class DummyButton(DummyComponent):
        pass

    class DummyTextbox(DummyComponent):
        pass

    class DummyChatbot(DummyComponent):
        pass

    class DummyFile(DummyComponent):
        pass

    class DummyImage(DummyComponent):
        pass

    class DummyHTML(DummyComponent):
        pass

    comps.Component = DummyComponent
    gradio.components = comps
    gradio.update = update
    gradio.Warning = lambda *a, **k: None
    gradio.Info = lambda *a, **k: None
    gradio.Error = lambda *a, **k: None
    gradio.Button = DummyButton
    gradio.Textbox = DummyTextbox
    gradio.Chatbot = DummyChatbot
    gradio.File = DummyFile
    gradio.Image = DummyImage
    gradio.HTML = DummyHTML

    monkeypatch.setitem(sys.modules, "gradio", gradio)
    monkeypatch.setitem(sys.modules, "gradio.components", comps)

    # minimal external stubs required for import
    monkeypatch.setitem(sys.modules, "browser_use", types.ModuleType("browser_use"))
    monkeypatch.setitem(sys.modules, "requests", types.ModuleType("requests"))

    browser_pkg = types.ModuleType("browser_use.browser")
    browser_browser = types.ModuleType("browser_use.browser.browser")
    browser_browser.BrowserConfig = type("BrowserConfig", (), {})
    browser_context = types.ModuleType("browser_use.browser.context")
    browser_context.BrowserContext = type("BrowserContext", (), {})
    browser_views = types.ModuleType("browser_use.browser.views")
    browser_views.BrowserState = type("BrowserState", (), {})
    monkeypatch.setitem(sys.modules, "browser_use.browser", browser_pkg)
    monkeypatch.setitem(sys.modules, "browser_use.browser.browser", browser_browser)
    monkeypatch.setitem(sys.modules, "browser_use.browser.context", browser_context)
    monkeypatch.setitem(sys.modules, "browser_use.browser.views", browser_views)
    views_mod = types.ModuleType("browser_use.agent.views")
    views_mod.AgentHistoryList = type("AgentHistoryList", (), {})
    views_mod.AgentOutput = type("AgentOutput", (), {})
    monkeypatch.setitem(sys.modules, "browser_use.agent", types.ModuleType("browser_use.agent"))
    monkeypatch.setitem(sys.modules, "browser_use.agent.views", views_mod)

    # internal stubs
    agent_mod = types.ModuleType("src.agent.browser_use.browser_use_agent")

    class DummyAgent:
        def __init__(self):
            self.state = types.SimpleNamespace(paused=False, stopped=False)
        def pause(self):
            self.state.paused = True
        def resume(self):
            self.state.paused = False
        def stop(self):
            self.state.stopped = True

    agent_mod.BrowserUseAgent = DummyAgent
    monkeypatch.setitem(sys.modules, "src.agent.browser_use.browser_use_agent", agent_mod)

    controller_mod = types.ModuleType("src.controller.custom_controller")
    class DummyController:
        def __init__(self):
            self.closed = False
        async def close_mcp_client(self):
            self.closed = True
    controller_mod.CustomController = DummyController
    monkeypatch.setitem(sys.modules, "src.controller.custom_controller", controller_mod)

    custom_browser_mod = types.ModuleType("src.browser.custom_browser")
    custom_browser_mod.CustomBrowser = type("CustomBrowser", (), {})
    monkeypatch.setitem(sys.modules, "src.browser.custom_browser", custom_browser_mod)
    custom_context_mod = types.ModuleType("src.browser.custom_context")
    custom_context_mod.CustomBrowserContextConfig = type("CustomBrowserContextConfig", (), {})
    monkeypatch.setitem(sys.modules, "src.browser.custom_context", custom_context_mod)

    utils_mod = types.ModuleType("src.utils.agent_utils")
    async def initialize_llm(*a, **k):
        return None
    utils_mod.initialize_llm = initialize_llm
    monkeypatch.setitem(sys.modules, "src.utils.agent_utils", utils_mod)

    launch_mod = types.ModuleType("src.utils.browser_launch")
    launch_mod.build_browser_launch_options = lambda *a, **k: (None, [])
    monkeypatch.setitem(sys.modules, "src.utils.browser_launch", launch_mod)

    manager_mod = types.ModuleType("src.webui.webui_manager")
    class DummyManager:
        def __init__(self):
            self.components = {}
            self.bu_agent = None
            self.bu_current_task = None
            self.bu_response_event = None
            self.bu_user_help_response = None
            self.bu_controller = None
            self.bu_chat_history = []
            self.bu_agent_task_id = None
        def get_component_by_id(self, cid):
            return self.components[cid]
    manager_mod.WebuiManager = DummyManager
    monkeypatch.setitem(sys.modules, "src.webui.webui_manager", manager_mod)

    lc_mod = types.ModuleType("langchain_core.language_models.chat_models")
    lc_mod.BaseChatModel = type("BaseChatModel", (), {})
    monkeypatch.setitem(sys.modules, "langchain_core.language_models.chat_models", lc_mod)

    sys.modules.pop("src.webui.components.browser_use_agent_tab", None)
    mod = importlib.import_module("src.webui.components.browser_use_agent_tab")
    return mod, DummyManager, DummyController


def make_manager(mod, Manager):
    mgr = Manager()
    comps = {
        "browser_use_agent.user_input": mod.gr.Textbox(),
        "browser_use_agent.run_button": mod.gr.Button(),
        "browser_use_agent.stop_button": mod.gr.Button(),
        "browser_use_agent.pause_resume_button": mod.gr.Button(),
        "browser_use_agent.clear_button": mod.gr.Button(),
        "browser_use_agent.chatbot": mod.gr.Chatbot(),
        "browser_use_agent.agent_history_file": mod.gr.File(),
        "browser_use_agent.recording_gif": mod.gr.Image(),
        "browser_use_agent.browser_view": mod.gr.HTML(),
    }
    mgr.components = comps
    return mgr, comps

async def collect(gen):
    res = []
    async for item in gen:
        res.append(item)
    return res

def test_handle_submit_running(monkeypatch):  # ignore input when task running
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    class DummyTask:
        def done(self):
            return False
    mgr.bu_current_task = DummyTask()
    async def runner():
        return await collect(mod.handle_submit(mgr, {comps["browser_use_agent.user_input"]: "hi"}))
    results = asyncio.run(runner())
    assert results == [{}]


def test_handle_submit_new_task(monkeypatch):  # submitting text starts agent
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    async def fake_run(m, c):
        yield {"ok": True}
    monkeypatch.setattr(mod, "run_agent_task", fake_run)
    async def runner():
        return await collect(mod.handle_submit(mgr, {comps["browser_use_agent.user_input"]: "do"}))
    results = asyncio.run(runner())
    assert results == [{"ok": True}]


def test_handle_pause_resume(monkeypatch):  # toggle pause state of running agent
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    mgr.bu_agent = mod.BrowserUseAgent()
    class DummyTask:
        def done(self):
            return False
    mgr.bu_current_task = DummyTask()
    res = asyncio.run(mod.handle_pause_resume(mgr))
    pb = comps["browser_use_agent.pause_resume_button"]
    assert res[pb] == mod.gr.update(value="▶️ Resume", interactive=True)
    assert mgr.bu_agent.state.paused


def test_handle_pause_resume_no_task(monkeypatch):  # pause ignored when no task
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, _ = make_manager(mod, Manager)
    res = asyncio.run(mod.handle_pause_resume(mgr))
    assert res == {}


def test_handle_stop_running(monkeypatch):  # stop button halts agent
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    mgr.bu_agent = mod.BrowserUseAgent()
    class DummyTask:
        def done(self):
            return False
    mgr.bu_current_task = DummyTask()
    res = asyncio.run(mod.handle_stop(mgr))
    assert mgr.bu_agent.state.stopped
    sb = comps["browser_use_agent.stop_button"]
    rb = comps["browser_use_agent.run_button"]
    pb = comps["browser_use_agent.pause_resume_button"]
    assert res[sb] == mod.gr.update(interactive=False, value="⏹️ Stopping...")
    assert res[pb] == mod.gr.update(interactive=False)
    assert res[rb] == mod.gr.update(interactive=False)


def test_handle_stop_no_task(monkeypatch):  # stop without active task resets UI
    mod, Manager, _ = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    res = asyncio.run(mod.handle_stop(mgr))
    rb = comps["browser_use_agent.run_button"]
    sb = comps["browser_use_agent.stop_button"]
    pb = comps["browser_use_agent.pause_resume_button"]
    cb = comps["browser_use_agent.clear_button"]
    assert res[rb] == mod.gr.update(interactive=True)
    assert res[sb] == mod.gr.update(interactive=False)
    assert res[pb] == mod.gr.update(interactive=False)
    assert res[cb] == mod.gr.update(interactive=True)


def test_handle_clear(monkeypatch):  # clear button cancels task and resets state
    mod, Manager, Controller = load_tab(monkeypatch)
    mgr, comps = make_manager(mod, Manager)
    mgr.bu_agent = mod.BrowserUseAgent()
    mgr.bu_controller = Controller()
    async def runner():
        async def dummy():
            await asyncio.sleep(0)
        mgr.bu_current_task = asyncio.create_task(dummy())
        return await mod.handle_clear(mgr)
    res = asyncio.run(runner())
    assert mgr.bu_controller is None
    assert mgr.bu_agent is None
    assert mgr.bu_current_task is None
    assert mgr.bu_chat_history == []
    rb = comps["browser_use_agent.run_button"]
    assert res[rb] == mod.gr.update(value="▶️ Submit Task", interactive=True)
    assert mgr.bu_response_event is None
    assert mgr.bu_user_help_response is None
    assert mgr.bu_agent_task_id is None
    assert hasattr(mgr, "bu_controller")


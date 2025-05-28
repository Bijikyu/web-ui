import sys
import types
import asyncio
import importlib

sys.path.append(".")


class DummyComponent:
    def __init__(self, value=None, interactive=True, visible=True, placeholder=None, label=None):
        self.value = value
        self.interactive = interactive
        self.visible = visible
        self.placeholder = placeholder
        self.label = label


class DummyButton(DummyComponent):
    pass


class DummyTextbox(DummyComponent):
    pass


class DummyFile(DummyComponent):
    pass


class DummyMarkdown(DummyComponent):
    pass


class DummyNumber(DummyComponent):
    pass


def preload_stubs():
    gradio = types.ModuleType("gradio")
    comps = types.ModuleType("gradio.components")
    setattr(comps, "Component", DummyComponent)
    gradio.components = comps
    for name, cls in {
        "Button": DummyButton,
        "Textbox": DummyTextbox,
        "File": DummyFile,
        "Markdown": DummyMarkdown,
        "Number": DummyNumber,
    }.items():
        setattr(gradio, name, cls)

    def update(**kwargs):
        return DummyComponent(**kwargs)

    gradio.update = update
    gradio.Warning = lambda *a, **k: None
    gradio.Info = lambda *a, **k: None
    gradio.Error = lambda *a, **k: None
    sys.modules.setdefault("gradio", gradio)
    sys.modules.setdefault("gradio.components", comps)

    browser_use = types.ModuleType("browser_use")
    browser_use.browser = types.ModuleType("browser_use.browser")
    browser_use.browser.browser = types.ModuleType("browser_use.browser.browser")
    browser_use.browser.context = types.ModuleType("browser_use.browser.context")
    browser_use.browser.views = types.ModuleType("browser_use.browser.views")
    browser_use.agent = types.ModuleType("browser_use.agent")
    browser_use.agent.views = types.ModuleType("browser_use.agent.views")
    browser_use.agent.service = types.ModuleType("browser_use.agent.service")
    browser_use.agent.service.Agent = object
    sys.modules.setdefault("browser_use", browser_use)
    sys.modules.setdefault("browser_use.browser", browser_use.browser)
    sys.modules.setdefault("browser_use.browser.browser", browser_use.browser.browser)
    sys.modules.setdefault("browser_use.browser.context", browser_use.browser.context)
    sys.modules.setdefault("browser_use.browser.views", browser_use.browser.views)
    sys.modules.setdefault("browser_use.agent", browser_use.agent)
    sys.modules.setdefault("browser_use.agent.views", browser_use.agent.views)
    sys.modules.setdefault("browser_use.agent.service", browser_use.agent.service)

    custom_browser = types.ModuleType("src.browser.custom_browser")
    class CustomBrowser: ...
    custom_browser.CustomBrowser = CustomBrowser
    sys.modules.setdefault("src.browser.custom_browser", custom_browser)

    custom_context = types.ModuleType("src.browser.custom_context")
    class CustomBrowserContext: ...
    class CustomBrowserContextConfig: ...
    custom_context.CustomBrowserContext = CustomBrowserContext
    custom_context.CustomBrowserContextConfig = CustomBrowserContextConfig
    sys.modules.setdefault("src.browser.custom_context", custom_context)

    custom_controller = types.ModuleType("src.controller.custom_controller")
    class CustomController: ...
    custom_controller.CustomController = CustomController
    sys.modules.setdefault("src.controller.custom_controller", custom_controller)


preload_stubs()


def setup_stubs():
    modules = {}
    sys.modules.setdefault("requests", types.ModuleType("requests"))

    modules["gradio"] = sys.modules["gradio"]
    modules["gradio.components"] = sys.modules["gradio.components"]
    modules["browser_use"] = sys.modules["browser_use"]
    modules["browser_use.browser"] = sys.modules["browser_use.browser"]
    modules["browser_use.browser.browser"] = sys.modules["browser_use.browser.browser"]
    modules["browser_use.browser.context"] = sys.modules["browser_use.browser.context"]
    modules["browser_use.browser.views"] = sys.modules["browser_use.browser.views"]
    modules["browser_use.agent"] = sys.modules["browser_use.agent"]
    modules["browser_use.agent.views"] = sys.modules["browser_use.agent.views"]
    modules["browser_use.agent.service"] = sys.modules["browser_use.agent.service"]
    modules["src.browser.custom_browser"] = sys.modules["src.browser.custom_browser"]
    modules["src.browser.custom_context"] = sys.modules["src.browser.custom_context"]
    modules["src.controller.custom_controller"] = sys.modules["src.controller.custom_controller"]

    class BrowserConfig:
        def __init__(self, **kwargs):
            pass

    class BrowserContext:
        async def close(self):
            pass

    class BrowserState:
        def __init__(self):
            self.screenshot = "b64"

    class AgentHistoryList:
        def total_duration_seconds(self):
            return 0.0

        def total_input_tokens(self):
            return 0

        def final_result(self):
            return "done"

        def errors(self):
            return []

    class DummyAction:
        def model_dump(self, exclude_none=True):
            return {"a": 1}

    class DummyState:
        def model_dump(self, exclude_none=True):
            return {"s": 1}

    class AgentOutput:
        def __init__(self):
            self.action = [DummyAction()]
            self.current_state = DummyState()

    browser_use = sys.modules["browser_use"]
    browser_use.browser.browser.Browser = object
    browser_use.browser.browser.BrowserConfig = BrowserConfig
    browser_use.browser.context.BrowserContext = BrowserContext
    browser_use.browser.views.BrowserState = BrowserState
    browser_use.agent.views.AgentHistoryList = AgentHistoryList
    browser_use.agent.views.AgentOutput = AgentOutput

    deep_agent = types.ModuleType("src.agent.deep_research.deep_research_agent")

    class DeepResearchAgent:
        def __init__(self, llm=None, browser_config=None, mcp_server_config=None):
            self.current_task_id = None
            self.stopped = False

        async def run(self, *a, **k):
            self.current_task_id = "123"
            await asyncio.sleep(0)
            return {"status": "ok", "task_id": self.current_task_id, "report": "# Done"}

        async def stop(self):
            self.stopped = True

    deep_agent.DeepResearchAgent = DeepResearchAgent
    sys.modules["src.agent.deep_research.deep_research_agent"] = deep_agent
    modules["src.agent.deep_research.deep_research_agent"] = deep_agent

    lc_models = types.ModuleType("langchain_core.language_models.chat_models")
    class BaseChatModel: ...
    lc_models.BaseChatModel = BaseChatModel
    sys.modules["langchain_core.language_models.chat_models"] = lc_models
    modules["langchain_core.language_models.chat_models"] = lc_models

    utils_module = types.ModuleType("src.utils.agent_utils")
    async def initialize_llm(*a, **k):
        return object()
    utils_module.initialize_llm = initialize_llm
    sys.modules["src.utils.agent_utils"] = utils_module
    modules["src.utils.agent_utils"] = utils_module

    return modules


def teardown_stubs(modules):
    for name in modules:
        sys.modules.pop(name, None)



def test_run_deep_research_simple(tmp_path, monkeypatch):
    modules = setup_stubs()
    orig_manager = sys.modules.pop("src.webui.webui_manager", None)
    orig_tab = sys.modules.pop("src.webui.components.deep_research_agent_tab", None)
    WebuiManager = importlib.import_module("src.webui.webui_manager").WebuiManager
    dr_tab = importlib.import_module("src.webui.components.deep_research_agent_tab")

    monkeypatch.setattr(dr_tab.os.path, "exists", lambda p: False)
    monkeypatch.setattr(dr_tab.os.path, "getmtime", lambda p: 0)
    monkeypatch.setattr("src.utils.utils.ensure_dir", lambda p: None)

    original_sleep = asyncio.sleep

    async def quick_sleep(_=0):
        await original_sleep(0)
    monkeypatch.setattr(dr_tab.asyncio, "sleep", quick_sleep)

    async def runner():
        manager = WebuiManager(settings_save_dir=str(tmp_path))
        manager.init_deep_research_agent()

        research_task = modules["gradio"].Textbox()
        resume_task_id = modules["gradio"].Textbox()
        parallel_num = modules["gradio"].Number()
        save_dir = modules["gradio"].Textbox()
        start_button = modules["gradio"].Button()
        stop_button = modules["gradio"].Button()
        markdown_display = modules["gradio"].Markdown()
        markdown_download = modules["gradio"].File()
        mcp_conf = modules["gradio"].Textbox()

        manager.add_components(
            "deep_research_agent",
            {
                "research_task": research_task,
                "resume_task_id": resume_task_id,
                "parallel_num": parallel_num,
                "max_query": save_dir,
                "start_button": start_button,
                "stop_button": stop_button,
                "markdown_display": markdown_display,
                "markdown_download": markdown_download,
                "mcp_server_config": mcp_conf,
            },
        )

        comps = {research_task: "topic", resume_task_id: "", parallel_num: 1, save_dir: str(tmp_path)}
        updates = [u async for u in dr_tab.run_deep_research(manager, comps)]

        assert not updates[0][start_button].interactive
        assert updates[0][stop_button].interactive

        report_update = updates[-2]
        assert report_update[markdown_display].value == "# Done"

        final = updates[-1]
        assert final[start_button].interactive
        assert not final[stop_button].interactive
        assert not final[markdown_download].interactive
        assert manager.dr_current_task is None
        assert manager.dr_task_id is None

    asyncio.run(runner())
    for name, mod in {
        "src.webui.webui_manager": orig_manager,
        "src.webui.components.deep_research_agent_tab": orig_tab,
    }.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    teardown_stubs(modules)

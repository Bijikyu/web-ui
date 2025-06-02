import sys
import types
import asyncio

sys.path.append(".")


def setup_stubs():
    """Insert gradio and browser_use stubs so the run tab imports cleanly."""  #(added docstring explaining helper purpose)
    modules = {}
    sys.modules.setdefault("requests", types.ModuleType("requests"))  # stub requests for manager import

    class DummyComponent:
        def __init__(self, value=None, interactive=True, visible=True, placeholder=None):
            self.value = value
            self.interactive = interactive
            self.visible = visible
            self.placeholder = placeholder

    class DummyButton(DummyComponent):
        pass

    class DummyTextbox(DummyComponent):
        pass

    class DummyFile(DummyComponent):
        pass

    class DummyImage(DummyComponent):
        pass

    class DummyHTML(DummyComponent):
        pass

    class DummyChatbot(DummyComponent):
        pass

    gradio = types.ModuleType("gradio")
    components_module = types.ModuleType("gradio.components")
    setattr(components_module, "Component", DummyComponent)
    gradio.components = components_module
    for name, cls in {
        "Button": DummyButton,
        "Textbox": DummyTextbox,
        "File": DummyFile,
        "Image": DummyImage,
        "HTML": DummyHTML,
        "Chatbot": DummyChatbot,
    }.items():
        setattr(gradio, name, cls)

    def update(**kwargs):
        return DummyComponent(**kwargs)

    gradio.update = update
    gradio.Warning = lambda *a, **k: None
    gradio.Info = lambda *a, **k: None
    gradio.Error = lambda *a, **k: None
    modules["gradio"] = gradio
    modules["gradio.components"] = components_module

    browser_use = types.ModuleType("browser_use")
    browser_use.browser = types.ModuleType("browser_use.browser")
    browser_use.browser.browser = types.ModuleType("browser_use.browser.browser")
    browser_use.browser.context = types.ModuleType("browser_use.browser.context")
    browser_use.browser.views = types.ModuleType("browser_use.browser.views")
    browser_use.agent = types.ModuleType("browser_use.agent")
    browser_use.agent.views = types.ModuleType("browser_use.agent.views")
    browser_use.agent.service = types.ModuleType("browser_use.agent.service")

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

    browser_use.browser.browser.Browser = object
    browser_use.browser.browser.BrowserConfig = BrowserConfig
    browser_use.browser.context.BrowserContext = BrowserContext
    browser_use.browser.views.BrowserState = BrowserState
    browser_use.agent.views.AgentHistoryList = AgentHistoryList
    browser_use.agent.views.AgentOutput = AgentOutput
    class Agent: ...
    browser_use.agent.service.Agent = Agent

    modules.update(
        {
            "browser_use": browser_use,
            "browser_use.browser": browser_use.browser,
            "browser_use.browser.browser": browser_use.browser.browser,
            "browser_use.browser.context": browser_use.browser.context,
            "browser_use.browser.views": browser_use.browser.views,
            "browser_use.agent": browser_use.agent,
            "browser_use.agent.views": browser_use.agent.views,
            "browser_use.agent.service": browser_use.agent.service,
        }
    )

    custom_browser = types.ModuleType("src.browser.custom_browser")
    custom_context = types.ModuleType("src.browser.custom_context")
    custom_controller = types.ModuleType("src.controller.custom_controller")

    class CustomBrowser:
        def __init__(self, config=None):
            self.config = config

        async def new_context(self, config=None):
            return CustomBrowserContext(config=config, browser=self)

        async def close(self):
            pass

    class CustomBrowserContext(BrowserContext):
        def __init__(self, config=None, browser=None):
            self.config = config
            self.browser = browser

        async def take_screenshot(self):
            return "b64"

        async def close(self):
            pass

    class CustomBrowserContextConfig:
        def __init__(self, **kwargs):
            pass

    class CustomController:
        def __init__(self, ask_assistant_callback=None):
            self.ask_callback = ask_assistant_callback

        async def setup_mcp_client(self, config):
            pass

    custom_browser.CustomBrowser = CustomBrowser
    custom_context.CustomBrowserContext = CustomBrowserContext
    custom_context.CustomBrowserContextConfig = CustomBrowserContextConfig
    custom_controller.CustomController = CustomController

    modules.update(
        {
            "src.browser.custom_browser": custom_browser,
            "src.browser.custom_context": custom_context,
            "src.controller.custom_controller": custom_controller,
        }
    )

    deep_agent = types.ModuleType("src.agent.deep_research.deep_research_agent")
    class DeepResearchAgent: ...
    deep_agent.DeepResearchAgent = DeepResearchAgent
    modules["src.agent.deep_research.deep_research_agent"] = deep_agent

    lc_models = types.ModuleType("langchain_core.language_models.chat_models")
    class BaseChatModel: ...
    lc_models.BaseChatModel = BaseChatModel
    modules["langchain_core.language_models.chat_models"] = lc_models

    agent_module = types.ModuleType("src.agent.browser_use.browser_use_agent")

    class BrowserUseAgent:
        def __init__(self, register_new_step_callback=None, register_done_callback=None, **kwargs):
            self.register_new_step_callback = register_new_step_callback
            self.register_done_callback = register_done_callback
            self.state = types.SimpleNamespace(paused=False, stopped=False, agent_id=None)
            self.settings = types.SimpleNamespace(generate_gif=None)

        def add_new_task(self, task):
            pass

        async def run(self, max_steps=1):
            await self.register_new_step_callback(BrowserState(), AgentOutput(), 1)
            history = AgentHistoryList()
            self.register_done_callback(history)
            return history

        def save_history(self, path):
            pass

    agent_module.BrowserUseAgent = BrowserUseAgent
    modules["src.agent.browser_use.browser_use_agent"] = agent_module

    utils_module = types.ModuleType("src.utils.agent_utils")
    async def initialize_llm(*a, **k):
        return object()
    utils_module.initialize_llm = initialize_llm
    modules["src.utils.agent_utils"] = utils_module

    for name, mod in modules.items():
        sys.modules[name] = mod
    return modules


def teardown_stubs(modules):
    """Remove previously inserted stub modules from sys.modules."""  #(added docstring describing cleanup)
    for name in modules:
        sys.modules.pop(name, None)


import importlib


def test_run_agent_task_simple(tmp_path):
    """Execute a basic browser agent task and expect success."""  #(added docstring summarizing test intent)
    # run agent task successfully with input
    modules = setup_stubs()
    orig_manager = sys.modules.pop("src.webui.webui_manager", None)
    orig_tab = sys.modules.pop("src.webui.components.browser_use_agent_tab", None)
    WebuiManager = importlib.import_module("src.webui.webui_manager").WebuiManager
    bu_tab = importlib.import_module("src.webui.components.browser_use_agent_tab")

    async def runner():
        manager = WebuiManager(settings_save_dir=str(tmp_path))
        manager.init_browser_use_agent()

        user_input = modules["gradio"].Textbox()
        run_button = modules["gradio"].Button()
        stop_button = modules["gradio"].Button()
        pause_button = modules["gradio"].Button()
        clear_button = modules["gradio"].Button()
        chatbot = modules["gradio"].Chatbot()
        history_file = modules["gradio"].File()
        gif = modules["gradio"].Image()
        browser_view = modules["gradio"].HTML()
        keep_open = modules["gradio"].Button()

        manager.add_components(
            "browser_use_agent",
            {
                "user_input": user_input,
                "run_button": run_button,
                "stop_button": stop_button,
                "pause_resume_button": pause_button,
                "clear_button": clear_button,
                "chatbot": chatbot,
                "agent_history_file": history_file,
                "recording_gif": gif,
                "browser_view": browser_view,
            },
        )
        manager.add_components("browser_settings", {"keep_browser_open": keep_open})

        components = {user_input: "do task", keep_open: True}

        updates = [u async for u in bu_tab.run_agent_task(manager, components)]

        assert manager.bu_browser is not None
        assert manager.bu_browser_context is not None
        assert len(manager.bu_chat_history) > 2

        final_update = updates[-1]
        assert final_update[run_button].interactive
        assert not final_update[stop_button].interactive
        assert not final_update[pause_button].interactive
        assert final_update[clear_button].interactive
        assert final_update[chatbot].value == manager.bu_chat_history

    asyncio.run(runner())
    for name, mod in {
        "src.webui.webui_manager": orig_manager,
        "src.webui.components.browser_use_agent_tab": orig_tab,
    }.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    teardown_stubs(modules)


def test_run_agent_task_missing_input(tmp_path):
    """Submitting empty input should not start an agent task."""  #(added docstring summarizing test intent)
    # empty input should not start agent
    modules = setup_stubs()
    orig_manager = sys.modules.pop("src.webui.webui_manager", None)
    orig_tab = sys.modules.pop("src.webui.components.browser_use_agent_tab", None)
    WebuiManager = importlib.import_module("src.webui.webui_manager").WebuiManager
    bu_tab = importlib.import_module("src.webui.components.browser_use_agent_tab")

    async def runner():
        manager = WebuiManager(settings_save_dir=str(tmp_path))
        manager.init_browser_use_agent()

        user_input = modules["gradio"].Textbox()
        run_button = modules["gradio"].Button()
        stop_button = modules["gradio"].Button()
        pause_button = modules["gradio"].Button()
        clear_button = modules["gradio"].Button()
        chatbot = modules["gradio"].Chatbot()
        history_file = modules["gradio"].File()
        gif = modules["gradio"].Image()
        browser_view = modules["gradio"].HTML()
        keep_open = modules["gradio"].Button()

        manager.add_components(
            "browser_use_agent",
            {
                "user_input": user_input,
                "run_button": run_button,
                "stop_button": stop_button,
                "pause_resume_button": pause_button,
                "clear_button": clear_button,
                "chatbot": chatbot,
                "agent_history_file": history_file,
                "recording_gif": gif,
                "browser_view": browser_view,
            },
        )
        manager.add_components("browser_settings", {"keep_browser_open": keep_open})

        components = {user_input: "", keep_open: True}

        updates = [u async for u in bu_tab.run_agent_task(manager, components)]

        assert len(updates) == 1
        assert updates[0][run_button].interactive
        assert manager.bu_browser is None
        assert manager.bu_browser_context is None
        assert manager.bu_chat_history == []

    asyncio.run(runner())
    for name, mod in {
        "src.webui.webui_manager": orig_manager,
        "src.webui.components.browser_use_agent_tab": orig_tab,
    }.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    teardown_stubs(modules)


def test_run_agent_task_invalid_mcp_config(tmp_path):
    """Invalid MCP configuration should surface an error message."""  #(added docstring summarizing test intent)
    # invalid MCP config shows error message
    modules = setup_stubs()
    orig_manager = sys.modules.pop("src.webui.webui_manager", None)
    orig_tab = sys.modules.pop("src.webui.components.browser_use_agent_tab", None)
    WebuiManager = importlib.import_module("src.webui.webui_manager").WebuiManager
    bu_tab = importlib.import_module("src.webui.components.browser_use_agent_tab")

    async def runner():
        manager = WebuiManager(settings_save_dir=str(tmp_path))
        manager.init_browser_use_agent()

        user_input = modules["gradio"].Textbox()
        run_button = modules["gradio"].Button()
        stop_button = modules["gradio"].Button()
        pause_button = modules["gradio"].Button()
        clear_button = modules["gradio"].Button()
        chatbot = modules["gradio"].Chatbot()
        history_file = modules["gradio"].File()
        gif = modules["gradio"].Image()
        browser_view = modules["gradio"].HTML()
        keep_open = modules["gradio"].Button()
        mcp_conf = modules["gradio"].Textbox()

        manager.add_components(
            "browser_use_agent",
            {
                "user_input": user_input,
                "run_button": run_button,
                "stop_button": stop_button,
                "pause_resume_button": pause_button,
                "clear_button": clear_button,
                "chatbot": chatbot,
                "agent_history_file": history_file,
                "recording_gif": gif,
                "browser_view": browser_view,
            },
        )
        manager.add_components("browser_settings", {"keep_browser_open": keep_open})
        manager.add_components("agent_settings", {"mcp_server_config": mcp_conf})

        components = {user_input: "do", keep_open: True, mcp_conf: "{bad json"}

        updates = [u async for u in bu_tab.run_agent_task(manager, components)]

        assert len(updates) == 2  # MCP config error occurs after initial state update
        msg = updates[-1][chatbot].value[-1]["content"]
        assert msg.startswith("**Setup Error:**")

    asyncio.run(runner())
    for name, mod in {
        "src.webui.webui_manager": orig_manager,
        "src.webui.components.browser_use_agent_tab": orig_tab,
    }.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    teardown_stubs(modules)


def test_run_agent_task_context_error(tmp_path):
    """Browser context failures should surface an error message."""  #(description of change & current functionality)
    modules = setup_stubs()
    orig_manager = sys.modules.pop("src.webui.webui_manager", None)
    orig_tab = sys.modules.pop("src.webui.components.browser_use_agent_tab", None)
    WebuiManager = importlib.import_module("src.webui.webui_manager").WebuiManager
    bu_tab = importlib.import_module("src.webui.components.browser_use_agent_tab")

    async def fail_ctx(self, config=None):
        raise RuntimeError("boom")

    modules["src.browser.custom_browser"].CustomBrowser.new_context = fail_ctx
    async def dummy_close(self):
        pass
    modules["src.controller.custom_controller"].CustomController.close_mcp_client = dummy_close

    async def runner():
        manager = WebuiManager(settings_save_dir=str(tmp_path))
        manager.init_browser_use_agent()

        user_input = modules["gradio"].Textbox()
        run_button = modules["gradio"].Button()
        stop_button = modules["gradio"].Button()
        pause_button = modules["gradio"].Button()
        clear_button = modules["gradio"].Button()
        chatbot = modules["gradio"].Chatbot()
        history_file = modules["gradio"].File()
        gif = modules["gradio"].Image()
        browser_view = modules["gradio"].HTML()
        keep_open = modules["gradio"].Button()

        manager.add_components(
            "browser_use_agent",
            {
                "user_input": user_input,
                "run_button": run_button,
                "stop_button": stop_button,
                "pause_resume_button": pause_button,
                "clear_button": clear_button,
                "chatbot": chatbot,
                "agent_history_file": history_file,
                "recording_gif": gif,
                "browser_view": browser_view,
            },
        )
        manager.add_components("browser_settings", {"keep_browser_open": keep_open})

        components = {user_input: "do", keep_open: True}

        updates = [u async for u in bu_tab.run_agent_task(manager, components)]

        assert len(updates) == 2
        update = updates[-1]
        assert update[run_button].interactive
        assert not update[stop_button].interactive
        assert not update[pause_button].interactive
        assert update[chatbot].value[-1]["content"].startswith("**Setup Error:**")

    asyncio.run(runner())
    for name, mod in {
        "src.webui.webui_manager": orig_manager,
        "src.webui.components.browser_use_agent_tab": orig_tab,
    }.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod
    teardown_stubs(modules)

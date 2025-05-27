import sys
import types
import asyncio

sys.path.append(".")
def setup_stubs():
    modules = {
        'browser_use': types.ModuleType('browser_use'),
        'browser_use.agent': types.ModuleType('browser_use.agent'),
        'browser_use.agent.gif': types.ModuleType('browser_use.agent.gif'),
        'browser_use.agent.service': types.ModuleType('browser_use.agent.service'),
        'browser_use.agent.views': types.ModuleType('browser_use.agent.views'),
        'browser_use.telemetry': types.ModuleType('browser_use.telemetry'),
        'browser_use.telemetry.views': types.ModuleType('browser_use.telemetry.views'),
        'browser_use.utils': types.ModuleType('browser_use.utils'),
        'dotenv': types.ModuleType('dotenv'),
        'src.browser': types.ModuleType('src.browser'),
        'src.browser.custom_browser': types.ModuleType('src.browser.custom_browser'),
        'src.browser.custom_context': types.ModuleType('src.browser.custom_context'),
        'src.controller': types.ModuleType('src.controller'),
        'src.controller.custom_controller': types.ModuleType('src.controller.custom_controller'),
    }

    modules['browser_use.agent.gif'].create_history_gif = lambda *a, **k: None

    class Agent:
        def __init__(self, *a, **k):
            self.state = types.SimpleNamespace(
                paused=False,
                stopped=False,
                consecutive_failures=0,
                history=AgentHistoryList(),
                n_steps=0,
                agent_id='id',
                last_result=None,
            )
            self.settings = types.SimpleNamespace(
                max_failures=1,
                validate_output=False,
                generate_gif=False,
            )
            self.telemetry = types.SimpleNamespace(capture=lambda *a, **k: None)
            self.task = 'task'
            self.initial_actions = None

        async def pause(self):
            self.state.paused = True

        async def resume(self):
            self.state.paused = False

        async def multi_act(self, *a, **k):
            self.state.last_result = 'multi'

        async def step(self, step_info):
            self.state.n_steps += 1

        async def log_completion(self):
            pass

        async def _validate_output(self):
            return True

        def _log_agent_run(self):
            pass

        async def close(self):
            pass

    modules['browser_use.agent.service'].Agent = Agent
    modules['browser_use.agent.service'].AgentHookFunc = None

    class AgentHistoryList:
        def __init__(self):
            self._done = False
        def is_done(self):
            return self._done
        def is_successful(self):
            return self._done
        def errors(self):
            return []
        def total_input_tokens(self):
            return 0
        def total_duration_seconds(self):
            return 0
    class AgentStepInfo:
        def __init__(self, step_number=0, max_steps=0):
            self.step_number = step_number
            self.max_steps = max_steps
    modules['browser_use.agent.views'].AgentHistoryList = AgentHistoryList
    modules['browser_use.agent.views'].AgentStepInfo = AgentStepInfo
    modules['browser_use.agent.views'].AgentOutput = type('AgentOutput', (), {})

    class AgentEndTelemetryEvent:
        def __init__(self, *a, **k):
            pass
    modules['browser_use.telemetry.views'].AgentEndTelemetryEvent = AgentEndTelemetryEvent

    def time_execution_async(*a, **k):
        def decorator(fn):
            return fn
        return decorator
    class SignalHandler:
        def __init__(self, *a, **k):
            pass
        def register(self):
            pass
        def unregister(self):
            pass
    modules['browser_use.utils'].time_execution_async = time_execution_async
    modules['browser_use.utils'].SignalHandler = SignalHandler
    modules['dotenv'].load_dotenv = lambda *a, **k: None

    modules['src.browser.custom_browser'].CustomBrowser = type('CustomBrowser', (), {})
    modules['src.browser.custom_context'].CustomBrowserContext = type('CustomBrowserContext', (), {})
    modules['src.browser.custom_context'].CustomBrowserContextConfig = type('CustomBrowserContextConfig', (), {})
    modules['src.controller.custom_controller'].CustomController = type('CustomController', (), {})

    for name, mod in modules.items():
        sys.modules[name] = mod
    return modules.keys()


def test_run_stops_when_done(monkeypatch):
    mods = setup_stubs()
    import importlib.util, os
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'agent', 'browser_use', 'browser_use_agent.py')
    spec = importlib.util.spec_from_file_location('src.agent.browser_use.browser_use_agent', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['src.agent.browser_use.browser_use_agent'] = module
    BrowserUseAgent = module.BrowserUseAgent
    agent = BrowserUseAgent()

    async def fake_step(info):
        agent.state.history._done = True
    monkeypatch.setattr(agent, 'step', fake_step)

    history = asyncio.run(agent.run(max_steps=5))
    assert history.is_done()
    for m in mods:
        sys.modules.pop(m, None)


def test_keyboard_interrupt(monkeypatch):
    mods = setup_stubs()
    import importlib.util, os
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'agent', 'browser_use', 'browser_use_agent.py')
    spec = importlib.util.spec_from_file_location('src.agent.browser_use.browser_use_agent', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['src.agent.browser_use.browser_use_agent'] = module
    BrowserUseAgent = module.BrowserUseAgent
    agent = BrowserUseAgent()

    async def raise_interrupt(info):
        raise KeyboardInterrupt
    monkeypatch.setattr(agent, 'step', raise_interrupt)

    history = asyncio.run(agent.run(max_steps=5))
    assert history is agent.state.history
    for m in mods:
        sys.modules.pop(m, None)

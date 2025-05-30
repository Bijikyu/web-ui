import asyncio
import importlib
import sys
import types

sys.path.append('.')


def test_register_and_close(monkeypatch):
    """Verify action registration and proper cleanup of MCP client."""  #(added docstring summarizing test intent)
    # ensure actions register and MCP client closes
    # create stubs for external dependencies
    pydantic_stub = types.ModuleType('pydantic')
    class BaseModel:  # simple BaseModel stub
        pass
    pydantic_stub.BaseModel = BaseModel

    agent_views = types.ModuleType('browser_use.agent.views')
    class ActionResult(BaseModel):
        def __init__(self, extracted_content=None, include_in_memory=False, error=None):
            self.extracted_content = extracted_content
            self.include_in_memory = include_in_memory
            self.error = error
    class ActionModel(BaseModel):
        pass
    agent_views.ActionResult = ActionResult
    agent_views.ActionModel = ActionModel

    context_mod = types.ModuleType('browser_use.browser.context')
    context_mod.BrowserContext = type('BrowserContext', (), {})

    registry_service = types.ModuleType('browser_use.controller.registry.service')
    class RegisteredAction:
        def __init__(self, name, description, function, param_model):
            self.name = name
            self.description = description
            self.function = function
            self.param_model = param_model
    class Actions:
        def __init__(self):
            self.actions = {}
    class Registry:
        def __init__(self):
            self.registry = Actions()
        def action(self, description):
            def decorator(fn):
                self.registry.actions[fn.__name__] = RegisteredAction(fn.__name__, description, fn, None)
                return fn
            return decorator
    registry_service.Registry = Registry
    registry_service.RegisteredAction = RegisteredAction

    controller_service = types.ModuleType('browser_use.controller.service')
    class Controller:
        def __init__(self, *a, **k):
            self.registry = Registry()
    controller_service.Controller = Controller
    controller_service.DoneAction = type('DoneAction', (), {})

    views_mod = types.ModuleType('browser_use.controller.views')
    for n in [
        'ClickElementAction','DoneAction','ExtractPageContentAction','GoToUrlAction',
        'InputTextAction','OpenTabAction','ScrollAction','SearchGoogleAction','SendKeysAction','SwitchTabAction']:
        setattr(views_mod, n, type(n, (), {}))

    utils_mod = types.ModuleType('browser_use.utils')
    def time_execution_sync(*a, **k):
        def decorator(fn):
            return fn
        return decorator
    utils_mod.time_execution_sync = time_execution_sync

    main_extractor = types.ModuleType('main_content_extractor')
    main_extractor.MainContentExtractor = type('MainContentExtractor', (), {})

    chat_mod = types.ModuleType('langchain_core.language_models.chat_models')
    chat_mod.BaseChatModel = type('BaseChatModel', (), {})

    mcp_stub = types.ModuleType('src.utils.mcp_client')
    class StubClient:
        def __init__(self, cfg):
            self.cfg = cfg
            self.server_name_to_tools = {}
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
    MultiServerMCPClient = StubClient
    async def setup_mcp_client_and_tools(cfg):
        client = mcp_stub.MultiServerMCPClient(cfg)
        await client.__aenter__()
        return client
    mcp_stub.MultiServerMCPClient = StubClient
    mcp_stub.setup_mcp_client_and_tools = setup_mcp_client_and_tools
    mcp_stub.create_tool_param_model = lambda tool: 'model'

    modules = {
        'pydantic': pydantic_stub,
        'browser_use.agent.views': agent_views,
        'browser_use.browser.context': context_mod,
        'browser_use.controller.registry.service': registry_service,
        'browser_use.controller.service': controller_service,
        'browser_use.controller.views': views_mod,
        'browser_use.utils': utils_mod,
        'main_content_extractor': main_extractor,
        'langchain_core.language_models.chat_models': chat_mod,
        'src.utils.mcp_client': mcp_stub,
    }
    for name, mod in modules.items():
        sys.modules[name] = mod

    real_utils = importlib.import_module('src.utils')
    setattr(real_utils, 'mcp_client', mcp_stub)
    sys.modules.pop('src.controller.custom_controller', None)
    custom_controller = importlib.import_module('src.controller.custom_controller')
    CustomController = custom_controller.CustomController

    class FakeTool:
        def __init__(self):
            self.name = 'tool'
            self.description = 'desc'
            self.args_schema = None
        async def ainvoke(self, params):
            return params

    class FakeClient(StubClient):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.entered = False
            self.exited = False
            self.server_name_to_tools = {'srv': [FakeTool()]}
        async def __aenter__(self):
            self.entered = True
            return self
        async def __aexit__(self, exc_type, exc, tb):
            self.exited = True

    monkeypatch.setattr(mcp_stub, 'MultiServerMCPClient', FakeClient)
    monkeypatch.setattr(custom_controller, 'create_tool_param_model', lambda t: 'model')

    controller = CustomController()
    asyncio.run(controller.setup_mcp_client({'mcpServers': {}}))
    actions = controller.registry.registry.actions
    assert 'mcp.srv.tool' in actions
    action = actions['mcp.srv.tool']
    assert action.function is controller.mcp_client.server_name_to_tools['srv'][0]
    assert action.param_model == 'model'
    assert controller.mcp_client.entered
    asyncio.run(controller.close_mcp_client())
    assert controller.mcp_client.exited

    sys.modules.pop('src.controller.custom_controller', None)
    sys.modules.pop('src.utils.mcp_client', None)
    if hasattr(real_utils, 'mcp_client'):
        delattr(real_utils, 'mcp_client')

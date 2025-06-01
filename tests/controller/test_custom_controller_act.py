import importlib
import sys
import types
import asyncio
import pytest

sys.path.append('.')


def load_controller(monkeypatch):
    """Import CustomController with stub modules."""  # (helper loads controller)
    # stub modules required for import
    pydantic_stub = types.ModuleType('pydantic')
    class BaseModel:  # minimal BaseModel
        pass
    pydantic_stub.BaseModel = BaseModel
    sys.modules['pydantic'] = pydantic_stub

    views_mod = types.ModuleType('browser_use.agent.views')
    class ActionResult(BaseModel):
        def __init__(self, extracted_content=None, include_in_memory=False, error=None):
            self.extracted_content = extracted_content
            self.include_in_memory = include_in_memory
            self.error = error
    class ActionModel(BaseModel):
        def __init__(self, **data):
            self._data = data
        def model_dump(self, exclude_unset=True):
            return self._data
    views_mod.ActionResult = ActionResult
    views_mod.ActionModel = ActionModel
    sys.modules['browser_use.agent.views'] = views_mod

    context_mod = types.ModuleType('browser_use.browser.context')
    context_mod.BrowserContext = type('BrowserContext', (), {})
    sys.modules['browser_use.browser.context'] = context_mod

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
    sys.modules['browser_use.controller.registry.service'] = registry_service

    controller_service = types.ModuleType('browser_use.controller.service')
    class Controller:
        def __init__(self, *a, **k):
            self.registry = Registry()
    controller_service.Controller = Controller
    controller_service.DoneAction = type('DoneAction', (), {})
    sys.modules['browser_use.controller.service'] = controller_service

    ctrl_views = types.ModuleType('browser_use.controller.views')
    for name in [
        'ClickElementAction', 'DoneAction', 'ExtractPageContentAction', 'GoToUrlAction',
        'InputTextAction', 'OpenTabAction', 'ScrollAction', 'SearchGoogleAction',
        'SendKeysAction', 'SwitchTabAction']:
        setattr(ctrl_views, name, type(name, (), {}))
    sys.modules['browser_use.controller.views'] = ctrl_views

    utils_mod = types.ModuleType('browser_use.utils')
    def time_execution_sync(*a, **k):
        def decorator(fn):
            return fn
        return decorator
    utils_mod.time_execution_sync = time_execution_sync
    sys.modules['browser_use.utils'] = utils_mod

    mcp_stub = types.ModuleType('src.utils.mcp_client')
    mcp_stub.create_tool_param_model = lambda tool: 'model'
    async def setup_mcp_client_and_tools(cfg):
        return None
    mcp_stub.setup_mcp_client_and_tools = setup_mcp_client_and_tools
    sys.modules['src.utils.mcp_client'] = mcp_stub

    main_extractor = types.ModuleType('main_content_extractor')
    main_extractor.MainContentExtractor = type('MainContentExtractor', (), {})
    sys.modules['main_content_extractor'] = main_extractor

    chat_mod = types.ModuleType('langchain_core.language_models.chat_models')
    chat_mod.BaseChatModel = type('BaseChatModel', (), {})
    sys.modules['langchain_core.language_models.chat_models'] = chat_mod

    sys.modules.pop('src.controller.custom_controller', None)
    custom_controller = importlib.import_module('src.controller.custom_controller')
    CustomController = custom_controller.CustomController

    controller = CustomController()
    return controller, ActionResult, ActionModel


def test_act_invalid_return(monkeypatch):
    """act should raise ValueError when action returns unsupported type."""  # (verify ValueError path)
    controller, _ActionResult, ActionModel = load_controller(monkeypatch)
    async def bad_action(*_a, **_k):
        return 123
    controller.registry.execute_action = bad_action
    action = ActionModel(dummy={})
    with pytest.raises(ValueError):
        asyncio.run(controller.act(action))


def test_act_with_action_result(monkeypatch):
    """act should return ActionResult unchanged."""  # (verify normal execution)
    controller, ActionResult, ActionModel = load_controller(monkeypatch)
    expected = ActionResult(extracted_content='ok')
    async def good_action(*_a, **_k):
        return expected
    controller.registry.execute_action = good_action
    action = ActionModel(dummy={})
    result = asyncio.run(controller.act(action))
    assert isinstance(result, ActionResult)
    assert result.extracted_content == 'ok'


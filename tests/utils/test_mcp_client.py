import types
import sys
import asyncio
from enum import Enum

sys.path.append('.')

# Create stub modules for missing dependencies
pydantic_stub = types.ModuleType('pydantic')
class BaseModel:
    pass
class FieldInfo:
    def __init__(self, default=None, **kwargs):
        self.default = default
        self.kwargs = kwargs

def Field(**kwargs):
    return FieldInfo(**kwargs)

def create_model(name, __base__=BaseModel, **fields):
    annotations = {k: v[0] for k, v in fields.items()}
    defaults = {k: (v[1].default if isinstance(v[1], FieldInfo) else v[1]) for k, v in fields.items()}
    attrs = {'__annotations__': annotations}
    attrs.update(defaults)
    return type(name, (__base__,), attrs)

pydantic_stub.BaseModel = BaseModel
pydantic_stub.Field = Field
pydantic_stub.create_model = create_model
sys.modules["pydantic"] = pydantic_stub
langchain_tools = types.ModuleType("langchain.tools")
class BaseTool:
    pass
langchain_tools.BaseTool = BaseTool
sys.modules["langchain.tools"] = langchain_tools
langchain_mod = types.ModuleType("langchain")
langchain_mod.tools = langchain_tools
sys.modules["langchain"] = langchain_mod

browser_mod = types.ModuleType('browser_use')
controller_mod = types.ModuleType('browser_use.controller')
registry_mod = types.ModuleType('browser_use.controller.registry')
views_mod = types.ModuleType('browser_use.controller.registry.views')
class ActionModel(BaseModel):
    pass
views_mod.ActionModel = ActionModel
sys.modules.setdefault('browser_use', browser_mod)
sys.modules.setdefault('browser_use.controller', controller_mod)
sys.modules.setdefault('browser_use.controller.registry', registry_mod)
sys.modules.setdefault('browser_use.controller.registry.views', views_mod)

mcp_mod = types.ModuleType('langchain_mcp_adapters.client')
class DummyClient:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
mcp_mod.MultiServerMCPClient = DummyClient
sys.modules.setdefault("langchain_mcp_adapters.client", mcp_mod)
sys.modules.pop("src.utils.mcp_client", None)
from importlib import import_module
mcp_client = import_module("src.utils.mcp_client")


from src.utils.mcp_client import setup_mcp_client_and_tools, create_tool_param_model, resolve_type


class SuccessClient(DummyClient):
    def __init__(self, cfg):
        self.cfg = cfg
        self.entered = False
    async def __aenter__(self):
        self.entered = True
        return self


class FailClient(DummyClient):
    def __init__(self, cfg):
        raise RuntimeError('fail')


def test_setup_mcp_client_success(monkeypatch):
    monkeypatch.setattr(mcp_client, 'MultiServerMCPClient', SuccessClient)
    client = asyncio.run(setup_mcp_client_and_tools({'a': 1}))
    assert isinstance(client, SuccessClient)
    assert client.entered


def test_setup_mcp_client_failure(monkeypatch):
    monkeypatch.setattr(mcp_client, 'MultiServerMCPClient', FailClient)
    client = asyncio.run(setup_mcp_client_and_tools({'a': 1}))
    assert client is None


class FakeTool:
    name = 'tool'
    args_schema = {
        'properties': {
            'req_field': {'type': 'string'},
            'opt_enum': {'type': 'string', 'enum': ['x', 'y'], 'default': 'x'},
            'num_array': {'type': 'array', 'items': {'type': 'integer'}},
        },
        'required': ['req_field']
    }

def test_create_tool_param_model():
    model = create_tool_param_model(FakeTool)
    ann = model.__annotations__
    assert ann['req_field'] is str
    assert issubclass(ann['opt_enum'], Enum)
    assert getattr(ann['num_array'], '__origin__', None) is list
    assert model.req_field is ...
    assert model.opt_enum == 'x'


def test_resolve_type_enum_array():
    enum_type = resolve_type({'type': 'string', 'enum': ['a', 'b']}, 'test')
    array_type = resolve_type({'type': 'array', 'items': {'type': 'integer'}}, 'nums')
    assert issubclass(enum_type, Enum)
    assert getattr(array_type, '__origin__', None) is list

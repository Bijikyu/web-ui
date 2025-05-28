import sys
import types
import asyncio
import threading
import json
import pytest
sys.path.append(".")
sys.modules.setdefault("requests", types.ModuleType("requests"))  # (stub requests)
gradio_stub = types.ModuleType("gradio")  # (create gradio stub)
class Group:  # (context manager class)
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
class DummyComp:
    def __init__(self, *args, **kwargs):
        self.fn = None
    def change(self, fn):
        self.fn = fn
    def click(self, fn=None, inputs=None, outputs=None):
        self.fn = fn
class Checkbox(DummyComp):
    pass
class Textbox(DummyComp):
    pass
class Number(DummyComp):
    pass
gradio_stub.Group = Group
gradio_stub.Row = Row
gradio_stub.Column = Column
gradio_stub.Checkbox = Checkbox
gradio_stub.Textbox = Textbox
gradio_stub.Number = Number
sys.modules["gradio"] = gradio_stub  # (register gradio stub)

def setup_stubs():
    modules = {
        'browser_use.browser.browser': types.ModuleType('browser_use.browser.browser'),
        'langchain_community.tools.file_management': types.ModuleType('langchain_community.tools.file_management'),
        'langchain_core.messages': types.ModuleType('langchain_core.messages'),
        'langchain_core.prompts': types.ModuleType('langchain_core.prompts'),
        'langchain_core.tools': types.ModuleType('langchain_core.tools'),
        'langgraph.graph': types.ModuleType('langgraph.graph'),
        'pydantic': types.ModuleType('pydantic'),
        'src.agent.browser_use.browser_use_agent': types.ModuleType('src.agent.browser_use.browser_use_agent'),
        'src.browser.custom_browser': types.ModuleType('src.browser.custom_browser'),
        'src.browser.custom_context': types.ModuleType('src.browser.custom_context'),
        'src.controller.custom_controller': types.ModuleType('src.controller.custom_controller'),
        'src.utils.mcp_client': types.ModuleType('src.utils.mcp_client'),
    }
    modules['browser_use.browser.browser'].BrowserConfig = type('BrowserConfig', (), {})
    fm = modules['langchain_community.tools.file_management']
    for name in ['ListDirectoryTool', 'ReadFileTool', 'WriteFileTool']:
        setattr(fm, name, type(name, (), {}))
    msgs = modules['langchain_core.messages']
    for name in ['AIMessage', 'BaseMessage', 'HumanMessage', 'SystemMessage', 'ToolMessage']:
        setattr(msgs, name, type(name, (), {}))
    class Prompt:
        @classmethod
        def from_messages(cls, msgs):
            return msgs
    modules['langchain_core.prompts'].ChatPromptTemplate = Prompt
    class StructTool:
        @classmethod
        def from_function(cls, **kwargs):
            return kwargs
    modules['langchain_core.tools'].StructuredTool = StructTool
    modules['langchain_core.tools'].Tool = type('Tool', (), {})
    modules['langgraph.graph'].StateGraph = type('StateGraph', (), {})
    class BaseModel:
        pass
    def Field(*a, **k):
        return None
    modules['pydantic'].BaseModel = BaseModel
    modules['pydantic'].Field = Field
    modules['src.agent.browser_use.browser_use_agent'].BrowserUseAgent = type('BrowserUseAgent', (), {})
    modules['src.browser.custom_browser'].CustomBrowser = type('CustomBrowser', (), {})
    modules['src.browser.custom_context'].CustomBrowserContextConfig = type('CustomBrowserContextConfig', (), {})
    modules['src.controller.custom_controller'].CustomController = type('CustomController', (), {})
    modules['src.utils.mcp_client'].setup_mcp_client_and_tools = lambda *a, **k: None
    for name, mod in modules.items():
        sys.modules.setdefault(name, mod)

setup_stubs()
from src.agent.deep_research import deep_research_agent as dr
sys.modules.pop("gradio", None)  # (remove stub so other tests can override)

def test_run_browser_search_tool(monkeypatch):
    async def fake_task(query, task_id, llm, browser_config, stop_event):
        return {'query': query, 'result': f'result_{query}', 'status': 'completed'}
    monkeypatch.setattr(dr, 'run_single_browser_task', fake_task)
    stop = threading.Event()
    res = asyncio.run(dr._run_browser_search_tool(['q1', 'q2', 'q3'], 'tid', object(), {'h': True}, stop, max_parallel_browsers=2))
    assert res == [
        {'query': 'q1', 'result': 'result_q1', 'status': 'completed'},
        {'query': 'q2', 'result': 'result_q2', 'status': 'completed'},
    ]

def test_run_browser_search_tool_cancel(monkeypatch):
    called = False
    async def fake_task(*a, **k):
        nonlocal called
        called = True
        return {}
    monkeypatch.setattr(dr, 'run_single_browser_task', fake_task)
    stop = threading.Event(); stop.set()
    res = asyncio.run(dr._run_browser_search_tool(['q1'], 'tid', object(), {}, stop))
    assert not called
    assert res == [{'query': 'q1', 'result': None, 'status': 'cancelled'}]

def test_create_browser_search_tool(monkeypatch):
    async def fake_runner(queries, task_id, llm, browser_config, stop_event, max_parallel_browsers=1):
        return ['ok', queries, task_id, llm, browser_config, stop_event, max_parallel_browsers]
    monkeypatch.setattr(dr, '_run_browser_search_tool', fake_runner)
    captured = {}
    def dummy_from_function(cls, **kwargs):
        captured.update(kwargs)
        return kwargs
    monkeypatch.setattr(dr.StructuredTool, 'from_function', classmethod(dummy_from_function))
    stop = threading.Event()
    tool = dr.create_browser_search_tool('llm', {'b': True}, 'tid', stop, max_parallel_browsers=3)
    result = asyncio.run(tool['coroutine'](['search']))
    assert captured['name'] == 'parallel_browser_search'
    assert result[0] == 'ok'
    assert result[6] == 3


def test_load_previous_state(tmp_path):
    plan = tmp_path / dr.PLAN_FILENAME
    plan.write_text('- [x] done\n- [ ] todo\n')
    search = tmp_path / dr.SEARCH_INFO_FILENAME
    data = [{'query': 'q', 'result': 'r'}]
    search.write_text(json.dumps(data))
    state = dr._load_previous_state('tid', str(tmp_path))
    assert state['current_step_index'] == 1
    assert state['search_results'] == data
    assert len(state['research_plan']) == 2


def test_save_report_to_md(tmp_path):
    dr._save_report_to_md('hello', tmp_path)
    report = tmp_path / dr.REPORT_FILENAME
    assert report.read_text() == 'hello'

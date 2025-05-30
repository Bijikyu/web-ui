import sys
import types
import asyncio
import threading
import json
import pytest
sys.path.append(".")

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
        'requests': types.ModuleType('requests'),  # // stub requests module to satisfy imports
        'gradio': types.ModuleType('gradio'),  # // stub gradio for utilities
    }
    modules['browser_use.browser.browser'].BrowserConfig = type('BrowserConfig', (), {})
    fm = modules['langchain_community.tools.file_management']
    for name in ['ListDirectoryTool', 'ReadFileTool', 'WriteFileTool']:
        Tool = type(name, (), {  # provide minimal tool class
            '__init__': lambda self, n=name: setattr(self, 'name', n)  # // set name attribute on tool instance
        })
        setattr(fm, name, Tool)
    gr = modules['gradio']
    class DummyComp:
        def __init__(self, *a, **k):
            self.fn = None
        def change(self, fn):
            self.fn = fn
        def click(self, fn=None, inputs=None, outputs=None):
            self.fn = fn
    for attr in ['Group', 'Row', 'Column', 'Textbox', 'Checkbox', 'Number', 'Button', 'File']:
        if attr in ['Group', 'Row', 'Column']:
            cls = type(attr, (DummyComp,), {
                '__enter__': lambda self: self,
                '__exit__': lambda self, exc_type, exc, tb: None,
            })
        else:
            cls = type(attr, (DummyComp,), {})
        setattr(gr, attr, cls)
    gr.components = types.ModuleType('gradio.components')  # // attach components module placeholder
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

def test_run_browser_search_tool(monkeypatch):
    """Run search queries across parallel browsers and collect results."""  #(added docstring summarizing test intent)
    # run tasks in parallel browsers
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
    """Cancellation event short-circuits browser search tool."""  #(added docstring summarizing test intent)
    # cancellation yields cancelled status
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
    """Build a StructuredTool wrapper around the search runner."""  #(added docstring summarizing test intent)
    # create StructuredTool wrapper
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
    """Read research plan and search results from disk."""  #(added docstring summarizing test intent)
    # load saved state from files
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
    """Persist markdown report to disk."""  #(added docstring summarizing test intent)
    # write markdown report file
    dr._save_report_to_md('hello', tmp_path)
    report = tmp_path / dr.REPORT_FILENAME
    assert report.read_text() == 'hello'


def test_load_previous_state_invalid(tmp_path):
    """Gracefully handle malformed saved state files."""  #(added docstring summarizing test intent)
    # gracefully handle bad state files
    (tmp_path / dr.PLAN_FILENAME).write_text('- [ ] task\n')  # // create plan file for loading
    (tmp_path / dr.SEARCH_INFO_FILENAME).write_text('{bad')  # // invalid json should trigger error
    state = dr._load_previous_state('tid', str(tmp_path))
    assert 'search_results' not in state  # // search results omitted on parse fail
    assert 'error_message' in state and 'Failed to load search results' in state['error_message']  # // error message surfaced


def test_save_plan_and_search_files(tmp_path):
    """Write research plan markdown and search results JSON."""  #(added docstring summarizing test intent)
    # persist plan and search data
    plan = [
        {'step': 1, 'task': 'a', 'status': 'pending', 'queries': None, 'result_summary': None},
        {'step': 2, 'task': 'b', 'status': 'completed', 'queries': None, 'result_summary': None},
    ]
    dr._save_plan_to_md(plan, str(tmp_path))
    text = (tmp_path / dr.PLAN_FILENAME).read_text()
    assert '- [ ] a' in text and '- [x] b' in text  # // verify tasks and markers saved

    results = [{'query': 'q', 'result': 'r'}]
    dr._save_search_results_to_json(results, str(tmp_path))
    saved = json.loads((tmp_path / dr.SEARCH_INFO_FILENAME).read_text())
    assert saved == results  # // json saved correctly


def test_setup_tools(monkeypatch):
    """Create default tool set when MCP not configured."""  #(added docstring summarizing test intent)
    # default tool set without MCP
    monkeypatch.setattr(dr.DeepResearchAgent, '_compile_graph', lambda self: None)  # // avoid constructing StateGraph
    agent = dr.DeepResearchAgent('llm', {'b': True})
    monkeypatch.setattr(dr, 'create_browser_search_tool', lambda *a, **k: types.SimpleNamespace(name='browser'))  # // replace browser tool factory
    tools = asyncio.run(agent._setup_tools('tid', threading.Event()))
    names = {t.name for t in tools}
    assert names == {'WriteFileTool', 'ReadFileTool', 'ListDirectoryTool', 'browser'}  # // default tools built


def test_setup_tools_with_mcp(monkeypatch):
    """Include MCP client tools when configuration provided."""  #(added docstring summarizing test intent)
    # include tools from MCP client
    class DummyClient:
        def get_tools(self):
            return [types.SimpleNamespace(name='mcp')]
        async def __aexit__(self, exc_type, exc, tb):
            pass

    async def fake_setup(config):
        return DummyClient()

    monkeypatch.setattr(dr.DeepResearchAgent, '_compile_graph', lambda self: None)  # // avoid constructing StateGraph
    agent = dr.DeepResearchAgent('llm', {'b': True}, mcp_server_config={'url': 'x'})
    monkeypatch.setattr(dr, 'create_browser_search_tool', lambda *a, **k: types.SimpleNamespace(name='browser'))  # // replace browser tool factory
    monkeypatch.setattr(dr, 'setup_mcp_client_and_tools', fake_setup)  # // fake mcp tool setup
    tools = asyncio.run(agent._setup_tools('tid', threading.Event()))
    names = {t.name for t in tools}
    assert 'mcp' in names and 'browser' in names  # // mcp tools included


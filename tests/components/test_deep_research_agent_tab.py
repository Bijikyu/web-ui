import sys
import types
import importlib
import asyncio
import json
import logging

import pytest

sys.path.append(".")

class DummyComp:
    pass

class DummyUpdate(dict):
    pass

class DummyFile:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class DummyTask:
    def done(self):
        return False


class DummyManager:
    def __init__(self):
        self.components = {}
        self.dr_agent = None
        self.dr_current_task = None
        self.dr_task_id = None
        self.dr_save_dir = None
    def get_component_by_id(self, cid):
        return self.components[cid]


def load_deep_tab(monkeypatch):
    """Import deep_research_agent_tab with gradio and agent stubs."""  #(added docstring describing helper purpose)
    gradio = types.ModuleType("gradio")
    comps = types.ModuleType("gradio.components")
    comps.Component = DummyComp
    class DummyGroup:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass
    gradio.components = comps
    gradio.Group = DummyGroup
    gradio.Row = DummyGroup
    gradio.Column = DummyGroup
    gradio.Textbox = DummyComp
    gradio.Number = DummyComp
    gradio.Button = DummyComp
    gradio.Markdown = DummyComp
    gradio.File = DummyFile
    def update(**kwargs):
        return DummyUpdate(kwargs)
    gradio.update = update
    monkeypatch.setitem(sys.modules, "requests", types.ModuleType("requests"))
    manager_mod = types.ModuleType("src.webui.webui_manager")
    manager_mod.WebuiManager = DummyManager
    monkeypatch.setitem(sys.modules, "src.webui.webui_manager", manager_mod)
    dr_mod = types.ModuleType("src.agent.deep_research.deep_research_agent")
    class DeepResearchAgent:
        def __init__(self, *a, **k):
            self.current_task_id = "1"
            self.stopped = False
            self.closed = False
        async def run(self, *a, **k):
            return None
        async def stop(self):
            self.stopped = True
        async def close_mcp_client(self):
            self.closed = True
    dr_mod.DeepResearchAgent = DeepResearchAgent
    monkeypatch.setitem(sys.modules, "src.agent.deep_research.deep_research_agent", dr_mod)
    agent_utils_mod = types.ModuleType("src.utils.agent_utils")
    async def initialize_llm(*a, **k):
        return None
    agent_utils_mod.initialize_llm = initialize_llm
    monkeypatch.setitem(sys.modules, "src.utils.agent_utils", agent_utils_mod)
    monkeypatch.setitem(sys.modules, "gradio", gradio)
    monkeypatch.setitem(sys.modules, "gradio.components", comps)
    sys.modules.pop("src.webui.components.deep_research_agent_tab", None)
    return importlib.import_module("src.webui.components.deep_research_agent_tab")


class DummyAgent:
    def __init__(self):
        self.stopped = False
        self.closed = False
    async def stop(self):
        self.stopped = True
    async def close_mcp_client(self):
        self.closed = True



def test_read_file_safe_valid(monkeypatch, tmp_path):
    """Reading an existing file returns its text contents."""  #(added docstring summarizing test intent)
    # return file contents when readable
    mod = load_deep_tab(monkeypatch)
    file_path = tmp_path / "f.txt"
    file_path.write_text("hello")
    assert mod._read_file_safe(str(file_path)) == "hello"


def test_read_file_safe_error(monkeypatch, caplog):
    """Errors while reading result in log entry and None."""  #(added docstring summarizing test intent)
    # log and return None on error
    mod = load_deep_tab(monkeypatch)
    monkeypatch.setattr(mod.os.path, "exists", lambda p: True)
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError("bad")))
    with caplog.at_level(logging.ERROR):
        res = mod._read_file_safe("missing.txt")
    assert res is None
    assert "Error reading file missing.txt" in caplog.text


def test_update_mcp_server_invalid(monkeypatch):
    """Hide configuration view if MCP config file is invalid."""  #(added docstring summarizing test intent)
    # invalid config path hides config
    mod = load_deep_tab(monkeypatch)
    mgr = DummyManager()
    mgr.dr_agent = DummyAgent()
    monkeypatch.setattr(mod, "load_mcp_server_config", lambda p, logger: None)
    text, upd = asyncio.run(mod.update_mcp_server("bad.json", mgr))
    assert text is None
    assert upd == mod.gr.update(visible=False)
    assert mgr.dr_agent.closed


def test_update_mcp_server_valid(monkeypatch):
    """Display loaded MCP configuration JSON."""  #(added docstring summarizing test intent)
    # valid config loads and shows JSON
    mod = load_deep_tab(monkeypatch)
    mgr = DummyManager()
    mgr.dr_agent = DummyAgent()
    data = {"a": 1}
    monkeypatch.setattr(mod, "load_mcp_server_config", lambda p, logger: data)
    text, upd = asyncio.run(mod.update_mcp_server("ok.json", mgr))
    assert text == json.dumps(data, indent=2)
    assert upd == mod.gr.update(visible=True)
    assert mgr.dr_agent.closed


def test_stop_deep_research_running(monkeypatch, tmp_path):
    """Stop a running deep research agent and show final report."""  #(added docstring summarizing test intent)
    # stop agent and expose report file
    mod = load_deep_tab(monkeypatch)
    mgr = DummyManager()
    names = [
        "stop_button", "start_button", "markdown_display", "markdown_download",
        "research_task", "resume_task_id", "parallel_num", "max_query"
    ]  # // updated component id list to match code changes
    for name in names:
        mgr.components[f"deep_research_agent.{name}"] = DummyComp()
    mgr.dr_agent = DummyAgent()
    mgr.dr_current_task = DummyTask()
    mgr.dr_task_id = "1"
    mgr.dr_save_dir = str(tmp_path)
    report_dir = tmp_path / "1"
    report_dir.mkdir()
    report_file = report_dir / "report.md"
    report_file.write_text("report")
    async def dummy_sleep(*a, **k):
        return None
    monkeypatch.setattr(mod.asyncio, "sleep", dummy_sleep)
    updates = asyncio.run(mod.stop_deep_research(mgr))
    stop_comp = mgr.get_component_by_id("deep_research_agent.stop_button")
    start_comp = mgr.get_component_by_id("deep_research_agent.start_button")
    md_comp = mgr.get_component_by_id("deep_research_agent.markdown_display")
    dl_comp = mgr.get_component_by_id("deep_research_agent.markdown_download")
    assert mgr.dr_agent.stopped
    assert updates[stop_comp] == mod.gr.update(interactive=False, value="⏹️ Stopping...")
    assert updates[start_comp] == mod.gr.update(interactive=False)
    assert updates[md_comp] == mod.gr.update(value="report\n\n---\n*Research stopped by user.*")
    dl = updates[dl_comp]
    assert isinstance(dl, mod.gr.File)
    assert dl.kwargs["value"] == str(report_file)


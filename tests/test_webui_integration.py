import importlib  #(used to check gradio availability)
import asyncio
from unittest.mock import AsyncMock, MagicMock  # (import MagicMock for new test)

import pytest


skip_msg = "gradio is required for this test"
gradio = pytest.importorskip("gradio", reason=skip_msg)
try:
    from browser_use.agent.views import AgentHistoryList  # (check for full browser_use install)
except Exception:
    pytest.skip("browser-use package is required for this test", allow_module_level=True)  # (skip if missing)

from src.webui.interface import create_ui


@pytest.mark.asyncio
async def test_launch_and_callbacks(monkeypatch):
    """Launch the WebUI and ensure tabs and callbacks exist."""  # (add integration test for webui)
    run_mock = AsyncMock(return_value={})  # mock start handler
    stop_mock = AsyncMock(return_value={})  # mock stop handler

    monkeypatch.setattr(
        "src.webui.components.deep_research_agent_tab.run_deep_research",
        run_mock,
    )
    monkeypatch.setattr(
        "src.webui.components.deep_research_agent_tab.stop_deep_research",
        stop_mock,
    )

    demo = create_ui()
    config = demo.get_config()  # obtain blocks config to inspect tabs
    tab_labels = [c["props"].get("label") for c in config["components"] if c["type"] == "tabitem"]
    assert "⚙️ Agent Settings" in tab_labels
    assert "🌐 Browser Settings" in tab_labels
    assert "🤖 Run Agent" in tab_labels
    assert "📁 Load & Save Config" in tab_labels

    server = demo.queue().launch(share=False, server_name="127.0.0.1", server_port=0, prevent_thread_lock=True)

    await asyncio.sleep(0.1)  # give server time
    server.close()  # stop server

    assert run_mock.call_count == 0  # callbacks not triggered yet
    assert stop_mock.call_count == 0


def test_tab_functions_invoked(monkeypatch):
    """Ensure each tab creation function runs once during UI build."""  # (check create_ui wiring)
    create_agent = MagicMock(return_value=None)  # (mock agent settings tab)
    create_browser = MagicMock(return_value=None)  # (mock browser settings tab)
    create_run = MagicMock(return_value=None)  # (mock browser use agent tab)
    create_deep = MagicMock(return_value=None)  # (mock deep research agent tab)
    create_config = MagicMock(return_value=None)  # (mock load save config tab)

    monkeypatch.setattr("src.webui.interface.create_agent_settings_tab", create_agent)  # (patch agent tab maker)
    monkeypatch.setattr("src.webui.interface.create_browser_settings_tab", create_browser)  # (patch browser tab maker)
    monkeypatch.setattr("src.webui.interface.create_browser_use_agent_tab", create_run)  # (patch run tab maker)
    monkeypatch.setattr("src.webui.interface.create_deep_research_agent_tab", create_deep)  # (patch deep tab maker)
    monkeypatch.setattr("src.webui.interface.create_load_save_config_tab", create_config)  # (patch config tab maker)

    create_ui()  # (build UI to trigger patched functions)

    assert create_agent.call_count == 1  # (agent settings called once)
    assert create_browser.call_count == 1  # (browser settings called once)
    assert create_run.call_count == 1  # (run agent called once)
    assert create_deep.call_count == 1  # (deep research called once)
    assert create_config.call_count == 1  # (load/save config called once)


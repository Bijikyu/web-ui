import importlib  #(used to check gradio availability)
import asyncio
from unittest.mock import AsyncMock

import pytest


skip_msg = "gradio is required for this test"
gradio = pytest.importorskip("gradio", reason=skip_msg)

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


import pytest

skip_msg = "gradio is required for this test"
gr = pytest.importorskip("gradio", reason=skip_msg)

from src.webui.interface import create_ui, theme_map


def test_create_ui_returns_blocks_for_each_theme():  # build UI for all themes
    for name in theme_map:  # iterate through known themes
        ui = create_ui(theme_name=name)  # create UI with theme
        assert isinstance(ui, gr.Blocks)  # expect gr.Blocks returned

import importlib.util
import subprocess
import sys
from unittest.mock import MagicMock  # import MagicMock for stubbing
import pytest

skip = importlib.util.find_spec("dotenv") is None or importlib.util.find_spec("gradio") is None

@pytest.mark.skipif(skip, reason="required packages missing")
def test_webui_help_runs():
    """Run the CLI with --help and verify usage text appears."""  #(added docstring summarizing test intent)
    result = subprocess.run([sys.executable, 'webui.py', '--help'], capture_output=True, text=True)  # run CLI
    assert result.returncode == 0  # exit success
    assert 'usage:' in result.stdout.lower()  # usage text present


@pytest.mark.skipif(skip, reason="required packages missing")
def test_webui_custom_args(monkeypatch):
    """Verify create_ui and launch use CLI argument values."""  # describe new test
    import webui  # import target module
    args = ['webui.py', '--ip', '0.0.0.0', '--port', '1234', '--theme', 'Base']
    monkeypatch.setattr(sys, 'argv', args)  # inject custom CLI args
    demo = MagicMock()  # stub Gradio Blocks
    demo.queue.return_value = demo  # queue returns self
    demo.launch.return_value = None  # launch does nothing
    create_mock = MagicMock(return_value=demo)  # replacement create_ui
    monkeypatch.setattr('src.webui.interface.create_ui', create_mock)  # patch factory
    webui.main()  # run entrypoint
    create_mock.assert_called_once_with(theme_name='Base')  # theme passed correctly
    demo.queue.assert_called_once()  # queue called once
    demo.launch.assert_called_once_with(server_name='0.0.0.0', server_port=1234)  # launch args


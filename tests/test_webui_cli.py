import importlib.util
import subprocess
import sys
import pytest

skip = importlib.util.find_spec("dotenv") is None or importlib.util.find_spec("gradio") is None

@pytest.mark.skipif(skip, reason="required packages missing")
def test_webui_help_runs():
    result = subprocess.run([sys.executable, 'webui.py', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage:' in result.stdout.lower()


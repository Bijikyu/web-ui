import sys  # allow src imports
import logging  # capture logs
sys.path.append('.')  # add project root for imports
from src.utils import qerrors  # function under test


def test_qerrors_offline_logs(monkeypatch, caplog):
    """Calling qerrors offline logs error without raising."""  # comment summarizing test intent
    monkeypatch.setenv("CODEX", "True")  # set offline mode
    with caplog.at_level(logging.ERROR):
        qerrors(Exception("fail"), "ctx")  # invoke wrapper offline
    assert "ctx: fail" in caplog.text  # error message logged
    monkeypatch.delenv("CODEX", raising=False)  # cleanup env var


def test_qerrors_online_missing_module(monkeypatch, caplog):
    """When CODEX is unset and qerrors package missing stub logs error."""  # summarizing test intent
    monkeypatch.delenv("CODEX", raising=False)  # ensure online mode
    saved = sys.modules.pop("qerrors", None)  # remove module if present
    with caplog.at_level(logging.ERROR):
        qerrors(Exception("boom"), "ctx")  # call wrapper expecting stub
    assert "ctx: boom" in caplog.text  # stub logs error
    if saved is not None:
        sys.modules["qerrors"] = saved  # restore original module

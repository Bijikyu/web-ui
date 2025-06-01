import sys  # allow src imports
sys.path.append('.')  # add project root
from src.utils.offline import is_offline  # function under test


def test_is_offline_truthy_values(monkeypatch):
    """Return True for common truthy CODEX values."""  # docstring summarizing test
    for val in ["True", "true", "1"]:  # iterate test values
        monkeypatch.setenv("CODEX", val)  # set CODEX env to value
        assert is_offline()  # detection should succeed
        monkeypatch.delenv("CODEX", raising=False)  # clean env between cases


def test_is_offline_falsey_values(monkeypatch):
    """Return False when CODEX unset or falsy."""  # docstring summarizing test
    for val in [None, "", "False", "false", "0"]:  # iterate falsy options
        if val is not None:  # set CODEX only when value provided
            monkeypatch.setenv("CODEX", val)  # apply env var for test
        else:
            monkeypatch.delenv("CODEX", raising=False)  # ensure var unset
        assert not is_offline()  # detection should fail
        monkeypatch.delenv("CODEX", raising=False)  # cleanup between cases


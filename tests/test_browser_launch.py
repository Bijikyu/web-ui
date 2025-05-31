import os  # access env vars
import sys  # access sys path

sys.path.append(".")  # allow src import
from src.utils.browser_launch import build_browser_launch_options  # import util


def test_default_behavior_without_env(monkeypatch):
    """Use default config when no environment overrides are provided."""  #(added docstring summarizing test intent)
    # use defaults when env vars absent
    monkeypatch.setenv("CODEX", "True")  #// enable offline mode to avoid Playwright import
    monkeypatch.delenv("CHROME_PATH", raising=False)  # remove env path
    monkeypatch.delenv("CHROME_USER_DATA", raising=False)  # remove env data
    config = {"window_width": 800, "window_height": 600, "use_own_browser": False}  # default config
    path, args = build_browser_launch_options(config)  # call util
    assert path is None  # expect None path
    assert args == ["--window-size=800,600"]  # only window size
    monkeypatch.delenv("CODEX", raising=False)  #// cleanup offline flag


def test_own_browser_env(monkeypatch):
    """Environment variables take precedence over config options."""  #(added docstring summarizing test intent)
    # prefer env variables over config
    monkeypatch.setenv("CODEX", "True")  #// enable offline mode to avoid Playwright import
    monkeypatch.setenv("CHROME_PATH", "/env/chrome")  # set env path
    monkeypatch.setenv("CHROME_USER_DATA", "/env/profile")  # set env data
    config = {
        "window_width": 640,
        "window_height": 480,
        "use_own_browser": True,
        "browser_binary_path": "/config/chrome",
        "user_data_dir": "/config/profile",
    }  # config with fields
    path, args = build_browser_launch_options(config)  # call util
    assert path == "/env/chrome"  # env path used
    assert args == [
        "--window-size=640,480",
        "--user-data-dir=/config/profile",
        "--user-data-dir=/env/profile",
    ]  # all args present
    monkeypatch.delenv("CODEX", raising=False)  #// cleanup offline flag


def test_empty_env_path(monkeypatch):
    """Ensure empty CHROME_PATH environment variable is treated as None."""  #(added docstring summarizing test intent)
    # empty CHROME_PATH results in None
    monkeypatch.setenv("CODEX", "True")  #// enable offline mode to avoid Playwright import
    monkeypatch.setenv("CHROME_PATH", "")  # empty env value
    monkeypatch.delenv("CHROME_USER_DATA", raising=False)  # no env data
    config = {
        "window_width": 1024,
        "window_height": 768,
        "use_own_browser": True,
        # no browser_binary_path to test env empty string
    }  # config no binary path
    path, args = build_browser_launch_options(config)  # call util
    assert path is None  # empty env results in None
    assert args == ["--window-size=1024,768"]  # only window size arg
    monkeypatch.delenv("CODEX", raising=False)  #// cleanup offline flag

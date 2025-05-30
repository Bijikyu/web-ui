import asyncio  # use asyncio for running async methods
import json  # for cookie file
import sys  # to inject stubs
import types  # create stub modules
from unittest.mock import mock_open, patch  # patch utilities for tests
sys.path.append(".")  # allow src imports
from types import SimpleNamespace  # for simple objects

# -- Stub external modules --
patchright_async = types.ModuleType("patchright.async_api")  # stub patchright
patchright_async.Browser = type("Browser", (), {})  # minimal Browser class
patchright_async.BrowserContext = type("BrowserContext", (), {})  # minimal BrowserContext
sys.modules["patchright.async_api"] = patchright_async  # register stub

browser_use = types.ModuleType("browser_use")  # base package stub
browser_mod = types.ModuleType("browser_use.browser")  # subpackage stub
browser_browser = types.ModuleType("browser_use.browser.browser")  # stub browser module
class BrowserBase:
    def __init__(self, config=None):
        self.config = config
browser_browser.Browser = BrowserBase  # base browser
browser_browser.IN_DOCKER = False  # not in docker
sys.modules["browser_use"] = browser_use  # register base package
sys.modules["browser_use.browser"] = browser_mod  # register subpackage
sys.modules["browser_use.browser.browser"] = browser_browser  # register stub

browser_context = types.ModuleType("browser_use.browser.context")  # stub context module
class BrowserContext:
    def __init__(self, browser=None, config=None, state=None):
        self.browser = browser
        self.config = config
        self.state = state
browser_context.BrowserContext = BrowserContext  # base class implementation
browser_context.BrowserContextConfig = type("BrowserContextConfig", (), {})  # empty config class
browser_context.BrowserContextState = type("BrowserContextState", (), {})  # empty state class
sys.modules["browser_use.browser.context"] = browser_context  # register stub

import importlib  # module for importing
sys.modules.pop("src.browser.custom_context", None)  # remove conflicting stub
sys.modules.pop("src.browser", None)  # remove parent stub
custom_context = importlib.import_module("src.browser.custom_context")  # load module
importlib.reload(custom_context)  # ensure fresh state
CustomBrowserContext = custom_context.CustomBrowserContext  # class under test
CustomBrowserContextConfig = custom_context.CustomBrowserContextConfig  # config class

class DummyPWContext:
    def __init__(self):
        self.added_cookies = None
        self.init_scripts = []
        self.tracing = types.SimpleNamespace(start=lambda **k: None)
    async def add_cookies(self, cookies):
        self.added_cookies = cookies
    async def add_init_script(self, script):
        self.init_scripts.append(script)

class DummyPWBrowser:
    def __init__(self):
        self.contexts = []
        self.new_called = False
    async def new_context(self, **kwargs):
        self.new_called = True
        ctx = DummyPWContext()
        self.contexts.append(ctx)
        return ctx

def make_config(**kwargs):
    """Return a context config namespace with provided overrides."""  #(added docstring describing helper purpose)
    base = {
        "force_new_context": False,
        "cookies_file": None,
        "trace_path": None,
        "user_agent": None,
        "disable_security": False,
        "window_width": 800,
        "window_height": 600,
        "save_recording_path": None,
        "save_har_path": None,
        "locale": None,
        "http_credentials": None,
        "is_mobile": False,
        "has_touch": False,
        "geolocation": None,
        "permissions": None,
        "timezone_id": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)

def test_reuse_existing_context(monkeypatch):
    """Second call should reuse the first Playwright context."""  #(added docstring summarizing test intent)
    # second call reuses first context
    pw_browser = DummyPWBrowser()  # stub PlaywrightBrowser
    browser_config = SimpleNamespace(cdp_url="ws://x", browser_binary_path=None)  # config for reuse
    browser = BrowserBase(browser_config)  # create browser
    ctx_cfg = make_config()  # context config
    cb_ctx = CustomBrowserContext(browser=browser, config=ctx_cfg)  # instance under test
    ctx1 = asyncio.run(cb_ctx._create_context(pw_browser))  # first call creates
    assert pw_browser.new_called  # ensure creation
    pw_browser.new_called = False  # reset flag
    ctx2 = asyncio.run(cb_ctx._create_context(pw_browser))  # second call should reuse
    assert ctx2 is ctx1  # same context reused
    assert not pw_browser.new_called  # no new context created

def test_load_cookies_and_scripts(tmp_path):
    """Load cookie file and inject navigator override script."""  #(added docstring summarizing test intent)
    # cookies loaded and script injected
    cookie_file = tmp_path / "c.json"  # path for cookie file
    with open(cookie_file, "w") as f:
        json.dump([{"name": "a", "value": "1", "sameSite": "Bad"}], f)  # write cookie
    pw_browser = DummyPWBrowser()  # stub PlaywrightBrowser
    browser = BrowserBase(SimpleNamespace(cdp_url=None, browser_binary_path=None))  # browser without reuse condition
    cfg = make_config(cookies_file=str(cookie_file))  # config with cookies
    cb_ctx = CustomBrowserContext(browser=browser, config=cfg)  # instance under test
    ctx = asyncio.run(cb_ctx._create_context(pw_browser))  # create context
    assert pw_browser.new_called  # context created
    assert ctx.added_cookies == [{"name": "a", "value": "1", "sameSite": "None"}]  # cookie fixed
    assert any("navigator" in s for s in ctx.init_scripts)  # script injected

def test_malformed_cookies_file(monkeypatch):
    """Gracefully log errors for malformed cookie files."""  #(added docstring summarizing test intent)
    # malformed cookie file logs error
    pw_browser = DummyPWBrowser()  # stub PlaywrightBrowser
    browser = BrowserBase(SimpleNamespace(cdp_url=None, browser_binary_path=None))  # browser without reuse condition
    cfg = make_config(cookies_file="bad.json")  # config with bad cookie file
    cb_ctx = CustomBrowserContext(browser=browser, config=cfg)  # instance under test
    bad = "{invalid"  # malformed json text
    with patch("os.path.exists", return_value=True):  # pretend file exists
        with patch("builtins.open", mock_open(read_data=bad)):  # provide bad json
            with patch.object(custom_context, "logger") as log:  # capture logger
                ctx = asyncio.run(cb_ctx._create_context(pw_browser))  # create context
                log.error.assert_called()  # verify error logged
    assert pw_browser.new_called  # context created despite error
    assert ctx.added_cookies is None  # add_cookies not called

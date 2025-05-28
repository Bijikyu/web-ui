import asyncio  # test uses asyncio run
import sys  # to inject stubs
import types  # create stub modules
sys.path.append(".")  # allow src imports

# -- Stub external modules --
patchright_async = types.ModuleType("patchright.async_api")  # stub patchright for imports
patchright_async.Browser = type("Browser", (), {})  # minimal Browser class
patchright_async.BrowserContext = type("BrowserContext", (), {})  # minimal BrowserContext class
patchright_async.Playwright = type("Playwright", (), {})  # dummy Playwright class
patchright_async.async_playwright = lambda: None  # unused async_playwright
sys.modules["patchright.async_api"] = patchright_async  # register stub

browser_use = types.ModuleType("browser_use")  # base package stub
browser_mod = types.ModuleType("browser_use.browser")  # subpackage stub
browser_browser = types.ModuleType("browser_use.browser.browser")  # stub browser module
class BrowserBase:
    def __init__(self, config=None):
        self.config = config
browser_browser.Browser = BrowserBase  # base class with config
browser_browser.IN_DOCKER = False  # not running in docker
sys.modules["browser_use"] = browser_use  # register base package
sys.modules["browser_use.browser"] = browser_mod  # register subpackage
sys.modules["browser_use.browser.browser"] = browser_browser  # register stub

browser_context = types.ModuleType("browser_use.browser.context")  # stub context module
browser_context.BrowserContext = type("BrowserContext", (), {})  # minimal BrowserContext
browser_context.BrowserContextConfig = type("BrowserContextConfig", (), {})  # minimal config
browser_context.BrowserContextState = type("BrowserContextState", (), {})  # state class stub
sys.modules["browser_use.browser.context"] = browser_context  # register stub

chrome_mod = types.ModuleType("browser_use.browser.chrome")  # stub chrome constants
chrome_mod.CHROME_ARGS = ["--remote-debugging-port=9222", "--base"]  # base args
chrome_mod.CHROME_DETERMINISTIC_RENDERING_ARGS = ["--det"]  # deterministic arg
chrome_mod.CHROME_DISABLE_SECURITY_ARGS = ["--no-sec"]  # disable security arg
chrome_mod.CHROME_DOCKER_ARGS = ["--docker"]  # docker arg
chrome_mod.CHROME_HEADLESS_ARGS = ["--headless"]  # headless arg
sys.modules["browser_use.browser.chrome"] = chrome_mod  # register stub

screen_res = types.ModuleType("browser_use.browser.utils.screen_resolution")  # stub screen util
screen_res.get_screen_resolution = lambda: {"width": 1024, "height": 768}  # return screen size
screen_res.get_window_adjustments = lambda: (10, 20)  # return offsets
sys.modules["browser_use.browser.utils.screen_resolution"] = screen_res  # register stub

utils_mod = types.ModuleType("browser_use.utils")  # stub utils module
utils_mod.time_execution_async = lambda *a, **k: None  # unused helper
sys.modules["browser_use.utils"] = utils_mod  # register stub

import importlib  # module for importing
sys.modules.pop("src.browser.custom_browser", None)  # remove conflicting stub
sys.modules.pop("src.browser", None)  # remove parent stub
sys.modules.pop("src.browser.custom_context", None)  # remove context stub
custom_browser = importlib.import_module("src.browser.custom_browser")  # load module
importlib.reload(custom_browser)  # ensure fresh state
CustomBrowser = custom_browser.CustomBrowser  # class under test

class DummyBrowserType:
    def __init__(self):
        self.launch_kwargs = None
    async def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return "browser"

class Playwright:
    def __init__(self):
        self.chromium = DummyBrowserType()
        self.firefox = DummyBrowserType()
        self.webkit = DummyBrowserType()

class Config:
    def __init__(self, **kwargs):
        self.headless = kwargs.get("headless", False)
        self.disable_security = kwargs.get("disable_security", False)
        self.deterministic_rendering = kwargs.get("deterministic_rendering", False)
        self.extra_browser_args = kwargs.get("extra_browser_args", [])
        self.browser_class = kwargs.get("browser_class", "chromium")
        self.proxy = kwargs.get("proxy")
        self.browser_binary_path = kwargs.get("browser_binary_path")


def test_setup_builtin_browser_headless(monkeypatch):
    cfg = Config(headless=True, disable_security=True, deterministic_rendering=True, extra_browser_args=["--foo"])  # configuration for headless
    browser = CustomBrowser(config=cfg)  # create browser instance
    pw = Playwright()  # stub Playwright object
    monkeypatch.setattr(
        custom_browser.socket.socket,
        "connect_ex",
        lambda self, addr: 1,
    )  # (mock socket connect_ex to indicate port free)
    asyncio.run(browser._setup_builtin_browser(pw))  # run setup
    args = set(pw.chromium.launch_kwargs["args"])  # grab args
    expected = {"--base", "--headless", "--no-sec", "--det", "--window-position=0,0", "--foo", "--window-size=1920,1080", "--remote-debugging-port=9222"}  # expected args
    assert args == expected  # verify all args

def test_setup_builtin_browser_port_conflict(monkeypatch):
    cfg = Config(headless=False, extra_browser_args=[])  # configuration no headless
    browser = CustomBrowser(config=cfg)  # create browser instance
    pw = Playwright()  # stub Playwright
    monkeypatch.setattr(
        custom_browser.socket.socket,
        "connect_ex",
        lambda self, addr: 0,
    )  # (mock socket connect_ex to indicate port 9222 in use)
    asyncio.run(browser._setup_builtin_browser(pw))  # run setup
    args = set(pw.chromium.launch_kwargs["args"])  # captured args
    expected = {"--base", "--window-position=10,20", "--window-size=1024,768"}  # expected without debug port
    assert args == expected  # verify cleaned args

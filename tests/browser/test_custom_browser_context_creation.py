import asyncio  # (imports asyncio for running new_context)
import sys  # (used to insert stub modules)
import types  # (used to create stub modules)
sys.path.append(".")  # (allow src imports)

# -- Stub external modules --
patchright_async = types.ModuleType("patchright.async_api")  # (stub patchright module)
patchright_async.Browser = type("Browser", (), {})  # (minimal Browser class)
patchright_async.BrowserContext = type("BrowserContext", (), {})  # (minimal BrowserContext class)
patchright_async.Playwright = type("Playwright", (), {})  # (dummy Playwright class)
patchright_async.async_playwright = lambda: None  # (unused async_playwright)
sys.modules["patchright.async_api"] = patchright_async  # (register stub patchright)

browser_use = types.ModuleType("browser_use")  # (base package stub)
browser_mod = types.ModuleType("browser_use.browser")  # (subpackage stub)
browser_browser = types.ModuleType("browser_use.browser.browser")  # (stub browser module)
class BrowserBase:
    def __init__(self, config=None):
        self.config = config
browser_browser.Browser = BrowserBase  # (base browser class)
browser_browser.IN_DOCKER = False  # (not running in docker)
sys.modules["browser_use"] = browser_use  # (register base package)
sys.modules["browser_use.browser"] = browser_mod  # (register subpackage)
sys.modules["browser_use.browser.browser"] = browser_browser  # (register stub browser)

browser_context = types.ModuleType("browser_use.browser.context")  # (stub context module)
browser_context.BrowserContext = type("BrowserContext", (), {})  # (minimal BrowserContext)
browser_context.BrowserContextConfig = type("BrowserContextConfig", (), {})  # (minimal config)
browser_context.BrowserContextState = type("BrowserContextState", (), {})  # (state class stub)
sys.modules["browser_use.browser.context"] = browser_context  # (register stub context)

chrome_mod = types.ModuleType("browser_use.browser.chrome")  # (stub chrome constants)
chrome_mod.CHROME_ARGS = []  # (empty base args)
chrome_mod.CHROME_DETERMINISTIC_RENDERING_ARGS = []  # (empty deterministic args)
chrome_mod.CHROME_DISABLE_SECURITY_ARGS = []  # (empty disable security args)
chrome_mod.CHROME_DOCKER_ARGS = []  # (empty docker args)
chrome_mod.CHROME_HEADLESS_ARGS = []  # (empty headless args)
sys.modules["browser_use.browser.chrome"] = chrome_mod  # (register stub chrome)

screen_res = types.ModuleType("browser_use.browser.utils.screen_resolution")  # (stub screen util)
screen_res.get_screen_resolution = lambda: {"width": 0, "height": 0}  # (return zero size)
screen_res.get_window_adjustments = lambda: (0, 0)  # (return zero offsets)
sys.modules["browser_use.browser.utils.screen_resolution"] = screen_res  # (register stub screen util)

utils_mod = types.ModuleType("browser_use.utils")  # (stub utils module)
utils_mod.time_execution_async = lambda *a, **k: None  # (unused helper)
sys.modules["browser_use.utils"] = utils_mod  # (register stub utils)

import importlib  # (module for importing)
sys.modules.pop("src.browser.custom_browser", None)  # (remove conflicting stub)
sys.modules.pop("src.browser", None)  # (remove parent stub)
sys.modules.pop("src.browser.custom_context", None)  # (remove context stub)
custom_browser = importlib.import_module("src.browser.custom_browser")  # (load module under test)
importlib.reload(custom_browser)  # (ensure fresh state)
CustomBrowser = custom_browser.CustomBrowser  # (class under test)

# -- Stub CustomBrowserContext to capture config --
class StubCBCfg:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class StubCBContext:
    def __init__(self, browser=None, config=None, state=None):
        self.browser = browser
        self.config = config
        self.state = state

custom_browser.CustomBrowserContext = StubCBContext  # (patch context class)
custom_browser.CustomBrowserContextConfig = StubCBCfg  # (patch config class)

class SimpleConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self):
        return self.__dict__

def test_new_context_merges_config():  # browser and context configs are combined
    browser_cfg = SimpleConfig(foo=1)  # (simple browser config)
    browser = CustomBrowser(config=browser_cfg)  # (instantiate browser)
    ctx_cfg = SimpleConfig(bar=2)  # (context config)
    ctx = asyncio.run(browser.new_context(ctx_cfg))  # (create context)
    assert isinstance(ctx, StubCBContext)  # (returned object is stub)
    assert ctx.config.kwargs == {"foo": 1, "bar": 2}  # (merged config passed)

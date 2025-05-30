import asyncio

from patchright.async_api import Browser as PlaywrightBrowser
from patchright.async_api import (
    BrowserContext as PlaywrightBrowserContext,
)
from patchright.async_api import (
    Playwright,
    async_playwright,
)
from browser_use.browser.browser import Browser, IN_DOCKER
from browser_use.browser.context import BrowserContext, BrowserContextConfig  # deduped duplicate import
import logging  # removed extra PlaywrightBrowserContext import

from browser_use.browser.chrome import (
    CHROME_ARGS,
    CHROME_DETERMINISTIC_RENDERING_ARGS,
    CHROME_DISABLE_SECURITY_ARGS,
    CHROME_DOCKER_ARGS,
    CHROME_HEADLESS_ARGS,
)
from browser_use.browser.utils.screen_resolution import get_screen_resolution, get_window_adjustments
from browser_use.utils import time_execution_async
import socket

from .custom_context import CustomBrowserContext, CustomBrowserContextConfig

logger = logging.getLogger(__name__)


class CustomBrowser(Browser):

    async def new_context(self, config: CustomBrowserContextConfig | None = None) -> CustomBrowserContext:
        """Create a browser context""" # (added docstring reminder)
        browser_config = self.config.model_dump() if self.config else {}  # extract base settings from browser
        context_config = config.model_dump() if config else {}  # take overrides from provided config
        merged_config = {**browser_config, **context_config}  # merge so explicit context options win
        return CustomBrowserContext(config=CustomBrowserContextConfig(**merged_config), browser=self)  # instantiate context with merged settings

    async def _setup_builtin_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Sets up and returns a Playwright Browser instance with anti-detection measures."""
        assert self.config.browser_binary_path is None, 'browser_binary_path should be None if trying to use the builtin browsers'  # ensure builtin browser is used

        if self.config.headless:
            screen_size = {'width': 1920, 'height': 1080}  # fixed size in headless mode for consistency
            offset_x, offset_y = 0, 0  # no need for adjustment when headless
        else:
            screen_size = get_screen_resolution()  # match visible screen size in headed mode
            offset_x, offset_y = get_window_adjustments()  # adjust for OS chrome

        chrome_args = {
            *CHROME_ARGS,  # baseline Playwright flags for stability
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),  # additional flags required in Docker
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),  # hide UI when requested
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),  # disable security features when requested
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),  # ensure repeatable rendering
            f'--window-position={offset_x},{offset_y}',  # start position so capture tools align correctly
            *self.config.extra_browser_args,
        }  # final Chromium argument set
        contain_window_size = False
        for arg in self.config.extra_browser_args:
            if "--window-size" in arg:
                contain_window_size = True
                break
        if not contain_window_size:
            chrome_args.add(f'--window-size={screen_size["width"]},{screen_size["height"]}')  # ensure consistent viewport size

        # check if port 9222 is already taken, if so remove the remote-debugging-port arg to prevent conflicts with other Chrome instances
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', 9222)) == 0:
                chrome_args.remove('--remote-debugging-port=9222')  # avoid crashing when port in use

        browser_class = getattr(playwright, self.config.browser_class)
        args = {
            'chromium': list(chrome_args),
            'firefox': [
                *{
                    '-no-remote',
                    *self.config.extra_browser_args,
                }
            ],
            'webkit': [
                *{
                    '--no-startup-window',
                    *self.config.extra_browser_args,
                }
            ],
        }

        browser = await browser_class.launch(
            headless=self.config.headless,
            args=args[self.config.browser_class],
            proxy=self.config.proxy.model_dump() if self.config.proxy else None,
            handle_sigterm=False,
            handle_sigint=False,
        )  # start browser with computed flags
        return browser

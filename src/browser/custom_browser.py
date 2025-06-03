"""Custom browser implementation with enhanced setup."""  # module docstring summarizing purpose
import asyncio

try:  # attempt patchright first for browser automation
    from patchright.async_api import Browser as PlaywrightBrowser  # use patchright Browser when available
    from patchright.async_api import (
        BrowserContext as PlaywrightBrowserContext,
    )
    from patchright.async_api import (
        Playwright,
        async_playwright,
    )
except ImportError:  # fallback to upstream playwright if patchright missing
    from playwright.async_api import Browser as PlaywrightBrowser
    from playwright.async_api import (
        BrowserContext as PlaywrightBrowserContext,
    )
    from playwright.async_api import (
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
    """Browser wrapper returning CustomBrowserContext with merged settings."""  #// explains reason for subclass

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

        chrome_args = list(CHROME_ARGS)  # base Chrome args list maintaining order
        if IN_DOCKER:
            chrome_args.extend(CHROME_DOCKER_ARGS)  # append docker specific flags
        if self.config.headless:
            chrome_args.extend(CHROME_HEADLESS_ARGS)  # append headless flags when requested
        if self.config.disable_security:
            chrome_args.extend(CHROME_DISABLE_SECURITY_ARGS)  # add security disabling flags
        if self.config.deterministic_rendering:
            chrome_args.extend(CHROME_DETERMINISTIC_RENDERING_ARGS)  # add deterministic rendering flags
        chrome_args.append(f'--window-position={offset_x},{offset_y}')  # set initial position for consistency
        chrome_args.extend(self.config.extra_browser_args)  # finally add extra args from config
        contain_window_size = False  # track if user provided size arg
        for arg in self.config.extra_browser_args:
            if "--window-size" in arg:
                contain_window_size = True
                break
        if not contain_window_size:
            chrome_args.append(
                f'--window-size={screen_size["width"]},{screen_size["height"]}'
            )  # append default size when absent

        # check if port 9222 is already taken, if so remove the remote-debugging-port arg to prevent conflicts with other Chrome instances
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', 9222)) == 0:
                if '--remote-debugging-port=9222' in chrome_args:
                    chrome_args.remove('--remote-debugging-port=9222')  # remove arg only when present

        browser_class = getattr(playwright, self.config.browser_class)
        args = {
            'chromium': chrome_args,  # pass computed chromium args list
            'firefox': ['-no-remote', *self.config.extra_browser_args],  # firefox args list in order
            'webkit': ['--no-startup-window', *self.config.extra_browser_args],  # webkit args list in order
        }

        browser = await browser_class.launch(
            headless=self.config.headless,
            args=args[self.config.browser_class],
            proxy=self.config.proxy.model_dump() if self.config.proxy else None,
            handle_sigterm=False,
            handle_sigint=False,
        )  # start browser with computed flags
        return browser

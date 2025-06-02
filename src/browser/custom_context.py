"""Custom browser context providing anti-detection features."""  # module docstring summarizing purpose
import json
import logging
import os

from browser_use.browser.browser import Browser, IN_DOCKER
from browser_use.browser.context import BrowserContext, BrowserContextConfig
try:  # try patchright for extended features
    from patchright.async_api import Browser as PlaywrightBrowser
    from patchright.async_api import BrowserContext as PlaywrightBrowserContext
except ImportError:  # fallback to playwright on failure
    from playwright.async_api import Browser as PlaywrightBrowser
    from playwright.async_api import BrowserContext as PlaywrightBrowserContext
from typing import Optional
from browser_use.browser.context import BrowserContextState

logger = logging.getLogger(__name__)


class CustomBrowserContextConfig(BrowserContextConfig):
    """Configuration that allows forcing a new Playwright context."""  #// clarify extension
    force_new_context: bool = False  # force to create new context


class CustomBrowserContext(BrowserContext):
    """BrowserContext subclass injecting anti-detection scripts by default."""  #// explains customization
    def __init__(
            self,
            browser: 'Browser',
            config: BrowserContextConfig | None = None,
            state: Optional[BrowserContextState] = None,
    ):
        """Initialize by delegating to :class:`BrowserContext`.

        The parent class sets up configuration and state, so no extra logic is needed.
        """  #// added docstring clarifying delegation and lack of extra logic
        super(CustomBrowserContext, self).__init__(browser=browser, config=config, state=state)

    async def _create_context(self, browser: PlaywrightBrowser):
        """Creates a new browser context with anti-detection measures and loads cookies if available."""
        if not self.config.force_new_context and self.browser.config.cdp_url and len(browser.contexts) > 0:
            context = browser.contexts[0]  # reuse existing CDP connected context when possible
        elif not self.config.force_new_context and self.browser.config.browser_binary_path and len(
                browser.contexts) > 0:
            context = browser.contexts[0]  # reuse launched browser context instead of new one
        else:
            context = await browser.new_context(
                no_viewport=True,
                user_agent=self.config.user_agent,
                java_script_enabled=True,
                bypass_csp=self.config.disable_security,
                ignore_https_errors=self.config.disable_security,
                record_video_dir=self.config.save_recording_path,
                record_video_size={
                    "width": self.config.window_width,
                    "height": self.config.window_height
                },
                record_har_path=self.config.save_har_path,
                locale=self.config.locale,
                http_credentials=self.config.http_credentials,
                is_mobile=self.config.is_mobile,
                has_touch=self.config.has_touch,
                geolocation=self.config.geolocation,
                permissions=self.config.permissions,
                timezone_id=self.config.timezone_id,
            )  # create a fresh context when reuse is not possible

        if self.config.trace_path:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)  # begin tracing when requested

        # Load cookies if they exist
        if self.config.cookies_file and os.path.exists(self.config.cookies_file):
            with open(self.config.cookies_file, 'r') as f:
                try:
                    cookies = json.load(f)  # read persisted cookies

                    valid_same_site_values = ['Strict', 'Lax', 'None']
                    for cookie in cookies:
                        if 'sameSite' in cookie:
                            if cookie['sameSite'] not in valid_same_site_values:
                                logger.warning(
                                    f"Fixed invalid sameSite value '{cookie['sameSite']}' to 'None' for cookie {cookie.get('name')}"
                                )
                                cookie['sameSite'] = 'None'
                    logger.info(f'🍪  Loaded {len(cookies)} cookies from {self.config.cookies_file}')
                    await context.add_cookies(cookies)  # restore browsing session

                except json.JSONDecodeError as e:
                    logger.error(f'Failed to parse cookies file: {str(e)}')

        # Expose anti-detection scripts
        await context.add_init_script(  # inject JS to mask automation footprint
            """
            // Webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US']
            });

            // Plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Chrome runtime
            window.chrome = { runtime: {} };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            (function () {
                const originalAttachShadow = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function attachShadow(options) {
                    return originalAttachShadow.call(this, { ...options, mode: "open" });
                };
            })();
            """
        )  # ensure context behaves more like a real user

        return context

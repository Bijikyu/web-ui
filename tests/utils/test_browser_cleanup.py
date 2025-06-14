import sys  # allow src imports
sys.path.append('.')  # include project root
import asyncio  # run async functions
from unittest.mock import AsyncMock, patch  # mocking async objects
from src.utils.browser_cleanup import close_browser_resources  # function to test


def test_close_browser_resources_success():
    """Browser and context close successfully when cleanup is called."""  #(added docstring summarizing test intent)
    # check normal closure
    browser = AsyncMock()  # fake browser
    context = AsyncMock()  # fake context
    with patch('src.utils.browser_cleanup.logger') as log:  # patch logger
        asyncio.run(close_browser_resources(browser, context))  # call util
        context.close.assert_awaited_once()  # context closed
        browser.close.assert_awaited_once()  # browser closed
        log.info.assert_any_call(
            "⚠️ Closing browser context when changing browser config."  # message text
        )
        log.info.assert_any_call(
            "⚠️ Closing browser when changing browser config."  # message text
        )


def test_close_browser_resources_errors():
    """Cleanup logs errors when closing browser or context fails."""  #(added docstring summarizing test intent)
    # handle closing errors
    browser = AsyncMock()  # fake browser
    context = AsyncMock()  # fake context
    browser.close.side_effect = Exception('b')  # raise on close
    context.close.side_effect = Exception('c')  # raise on close
    with patch('src.utils.browser_cleanup.logger') as log:  # patch logger
        asyncio.run(close_browser_resources(browser, context))  # call util
        log.error.assert_any_call('Error closing context: c')  # context error log
        log.error.assert_any_call('Error closing browser: b')  # browser error log


def test_close_browser_resources_none():
    """Calling cleanup with None arguments logs nothing."""  #(added docstring summarizing test intent)
    # call with no browser or context
    with patch('src.utils.browser_cleanup.logger') as log:  # patch logger
        asyncio.run(close_browser_resources(None, None))  # invoke util with none
        log.info.assert_not_called()  # no info logs expected
        log.error.assert_not_called()  # no error logs expected


def test_close_browser_resources_none_logs():
    """Ensure calling cleanup twice with None does not log."""  #(added docstring summarizing test intent)
    # verify logging
    with patch('src.utils.browser_cleanup.logger') as log:  # patch logger
        asyncio.run(close_browser_resources(None, None))  # call util again
        log.info.assert_not_called()  # nothing logged as info
        log.error.assert_not_called()  # nothing logged as error

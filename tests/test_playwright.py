
import pdb
import pytest  # (import for importorskip)
pytest.importorskip("dotenv", reason="python-dotenv required")  # (skip if dotenv missing)

import logging  # (replaced pdb import with logging)

from dotenv import load_dotenv

load_dotenv()


pytest.importorskip("patchright", reason="patchright is required")  # (skip if patchright missing)


logger = logging.getLogger(__name__)  # (added logger for debug output)



@pytest.mark.skip(reason="requires manual browser interaction")
def test_connect_browser():  # (skip heavy browser test)
    import os
    from patchright.sync_api import sync_playwright

    chrome_exe = os.getenv("CHROME_PATH", "")
    chrome_use_data = os.getenv("CHROME_USER_DATA", "")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=chrome_use_data,
            executable_path=chrome_exe,
            headless=False  # Keep browser window visible
        )

        page = browser.new_page()
        page.goto("https://mail.google.com/mail/u/0/#inbox")
        page.wait_for_load_state()
        logger.debug("Browser page loaded")  # (added debug log in place of manual pause)
        browser.close()


if __name__ == '__main__':
    test_connect_browser()

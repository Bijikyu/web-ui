import logging
logger = logging.getLogger(__name__)

async def close_browser_resources(browser, context):
    if context:
        logger.info("⚠️ Closing browser context when changing browser config.")  # log context closing
        try:
            await context.close()
        except Exception as e:
            logger.error(f"Error closing context: {e}")
    if browser:
        logger.info("⚠️ Closing browser when changing browser config.")  # log browser closing
        try:
            await browser.close()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

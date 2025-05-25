import os  # // needed for env lookup
from typing import Any, Dict, List, Optional, Tuple  # // typing for function


def build_browser_launch_options(config: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:  # // util to build browser options
    """Build browser binary path and extra launch arguments."""  # // describe function
    window_w = config.get("window_width", 1280)  # // width from config
    window_h = config.get("window_height", 1100)  # // height from config
    extra_args = [f"--window-size={window_w},{window_h}"]  # // default arg list
    browser_user_data_dir = config.get("user_data_dir", None)  # // custom data dir
    if browser_user_data_dir:
        extra_args.append(f"--user-data-dir={browser_user_data_dir}")  # // add dir option
    use_own_browser = config.get("use_own_browser", False)  # // check custom browser usage
    browser_binary_path = config.get("browser_binary_path", None)  # // path from config
    if use_own_browser:
        browser_binary_path = os.getenv("CHROME_PATH", None) or browser_binary_path  # // env override
        if browser_binary_path == "":
            browser_binary_path = None  # // empty -> None
        chrome_user_data = os.getenv("CHROME_USER_DATA", None)  # // check env data dir
        if chrome_user_data:
            extra_args.append(f"--user-data-dir={chrome_user_data}")  # // add env dir
    else:
        browser_binary_path = None  # // not using custom browser
    return browser_binary_path, extra_args  # // return values

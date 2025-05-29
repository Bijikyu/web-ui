import json, logging, os  # new utility imports for safe json loading
logger = logging.getLogger(__name__)  # logger setup for this module


def load_json_safe(path: str):  # utility to safely load json
    if not path or not os.path.exists(path):  # validate path exists
        return None  # return None if invalid
    try:
        with open(path, "r", encoding="utf-8") as f:  # open file safely
            return json.load(f)  # return parsed json
    except Exception as e:  # catch any exception during load
        logger.error(f"Failed loading {path}: {e}")  # log failure
        return None  # return None on failure


def load_mcp_server_config(path: str, logger) -> dict | None:  # load MCP server config with validation
    if not path or not os.path.exists(path) or not path.endswith('.json'):  # validate path exists and is json
        logger.warning(f"{path} is not a valid MCP file.")  # warn when invalid
        return None  # return None on invalid path
    data = load_json_safe(path)  # use existing safe loader
    if data is None:  # check load failure
        logger.warning(f"{path} cannot be loaded.")  # warn when loading fails
    return data  # return parsed json or None

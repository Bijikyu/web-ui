import json, logging, os  # //new utility imports for safe json loading
logger = logging.getLogger(__name__)  # //logger setup for this module


def load_json_safe(path: str):  # //utility to safely load json
    if not path or not os.path.exists(path):  # //validate path exists
        return None  # //return None if invalid
    try:
        with open(path, "r", encoding="utf-8") as f:  # //open file safely
            return json.load(f)  # //return parsed json
    except Exception as e:  # //catch any exception during load
        logger.error(f"Failed loading {path}: {e}")  # //log failure
        return None  # //return None on failure

import os  # //(new file import os for file checks)
import json  # //(new file import json to load config)
import gradio as gr  # //(new file import gradio for UI updates)
import logging  # //(new file import logging for warnings)

logger = logging.getLogger(__name__)  # //(new logger for debugging)


async def load_mcp_server_config(mcp_file: str):  # //(new util to load MCP config)
    """Load MCP server JSON and return display data."""  # //(docstring for new function)
    if not mcp_file or not os.path.exists(mcp_file) or not mcp_file.endswith('.json'):  # //(validate file path)
        logger.warning(f"{mcp_file} is not a valid MCP file.")  # //(log warning for invalid path)
        return None, gr.update(visible=False)  # //(return invisibility for bad file)

    with open(mcp_file, 'r') as f:  # //(open provided json file)
        mcp_server = json.load(f)  # //(parse json content)

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)  # //(return serialized json and visible update)

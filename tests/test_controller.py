import asyncio
import logging  # (replaced pdb import with logging)
import pytest  # (needed for skipping heavy tests)
import sys
import time

sys.path.append(".")

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)  # (added logger for debug output)


@pytest.mark.skip(reason="requires MCP servers and manual checks")
async def test_mcp_client():  # (skip heavy MCP test)
    from src.utils.mcp_client import setup_mcp_client_and_tools, create_tool_param_model

    test_server_config = {
        "playwright": {
            "command": "npx",
            "args": [
                "@playwright/mcp@latest",
            ],
            "transport": "stdio",
        },
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/Users/warmshao/ai_workspace",
            ]
        }
    }

    mcp_tools, mcp_client = await setup_mcp_client_and_tools(test_server_config)

    for tool in mcp_tools:
        tool_param_model = create_tool_param_model(tool)
        print(tool.name)
        print(tool.description)
        print(tool_param_model.model_json_schema())
    logger.debug("MCP client tools enumerated")  # (replaced manual breakpoint with debug log)


@pytest.mark.skip(reason="requires MCP servers and manual checks")
async def test_controller_with_mcp():  # (skip heavy MCP integration test)
    import os
    from src.controller.custom_controller import CustomController
    from browser_use.controller.registry.views import ActionModel

    mcp_server_config = {
        "mcpServers": {
            "markitdown": {
                "command": "docker",
                "args": [
                    "run",
                    "--rm",
                    "-i",
                    "markitdown-mcp:latest"
                ]
            },
            "desktop-commander": {
                "command": "npx",
                "args": [
                    "-y",
                    "@wonderwhy-er/desktop-commander"
                ]
            },
            # "filesystem": {
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@modelcontextprotocol/server-filesystem",
            #         "/Users/xxx/ai_workspace",
            #     ]
            # },
        }
    }

    controller = CustomController()
    await controller.setup_mcp_client(mcp_server_config)
    action_name = "mcp.desktop-commander.execute_command"
    action_info = controller.registry.registry.actions[action_name]
    param_model = action_info.param_model
    print(param_model.model_json_schema())
    params = {"command": f"python ./tmp/test.py"
              }
    validated_params = param_model(**params)
    ActionModel_ = controller.registry.create_action_model()
    # Create ActionModel instance with the validated parameters
    action_model = ActionModel_(**{action_name: validated_params})
    result = await controller.act(action_model)
    result = result.extracted_content
    print(result)
    if result and "Command is still running. Use read_output to get more output." in result and "PID" in \
            result.split("\n")[0]:
        pid = int(result.split("\n")[0].split("PID")[-1].strip())
        action_name = "mcp.desktop-commander.read_output"
        action_info = controller.registry.registry.actions[action_name]
        param_model = action_info.param_model
        print(param_model.model_json_schema())
        params = {"pid": pid}
        validated_params = param_model(**params)
        action_model = ActionModel_(**{action_name: validated_params})
        output_result = ""  # (initialize output result)
        end_time = time.time() + 5  # (timeout to avoid hanging)
        while time.time() < end_time:
            time.sleep(1)
            result = await controller.act(action_model)
            result = result.extracted_content
            if result:
                output_result = result  # (capture command output)
                break
        print(output_result)
        assert output_result  # (ensure some output was returned)
    await controller.close_mcp_client()
    logger.debug("MCP client closed")  # (removed final breakpoint)


if __name__ == '__main__':
    # asyncio.run(test_mcp_client())
    asyncio.run(test_controller_with_mcp())

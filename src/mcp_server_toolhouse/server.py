import asyncio
import os
import platform
import uuid

import httpx

from typing import Any, Dict, List, Union

from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration constants
TOOLHOUSE_BASE_URL: str = "https://api.toolhouse.ai/v1"
GET_TOOLS_ENDPOINT: str = f"{TOOLHOUSE_BASE_URL}/get_tools"
RUN_TOOLS_ENDPOINT: str = f"{TOOLHOUSE_BASE_URL}/run_tools"

TOOLHOUSE_API_KEY: str = os.environ.get("TOOLHOUSE_API_KEY", None)
if not TOOLHOUSE_API_KEY:
    raise EnvironmentError("TOOLHOUSE_API_KEY environment variable is not set")

TOOLHOUSE_BUNDLE: str = os.environ.get("TOOLHOUSE_BUNDLE", "mcp-toolhouse")
if not TOOLHOUSE_BUNDLE:
    raise EnvironmentError("TOOLHOUSE_BUNDLE environment variable is not set")

# Create a server instance
server = Server("mcp-server-toolhouse")


def get_common_headers() -> Dict[str, str]:
    """Constructs and returns common headers for HTTP requests."""
    return {
        "Content-Type": "application/json",
        "User-Agent": f"Toolhouse/1.2.1 Python/{platform.python_version()}",
        "Authorization": f"Bearer {TOOLHOUSE_API_KEY}",
    }


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    Queries the Toolhouse API for tools and returns a list of tool objects.
    """
    headers = get_common_headers()
    payload = {
        "bundle": TOOLHOUSE_BUNDLE,
        "metadata": {},
        "provider": "openai",
    }

    response = httpx.post(GET_TOOLS_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
    response_data = response.json()

    tools: List[types.Tool] = []
    for tool in response_data:
        func = tool.get("function", {})
        tools.append(
            types.Tool.model_construct(
                name=func.get("name", ""),
                description=func.get("description", ""),
                inputSchema=func.get("parameters", {}),
            )
        )

    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, args: Dict[str, Any]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """
    Calls a tool by sending a function call to the Toolhouse API and returns the result.
    """
    headers = get_common_headers()
    payload = {
        "provider": "openai",
        "bundle": TOOLHOUSE_BUNDLE,
        "metadata": {},
        "content": {
            "type": "function",
            "id": str(uuid.uuid4()),
            "function": {
                "name": name,
                "arguments": args,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                RUN_TOOLS_ENDPOINT, headers=headers, json=payload
            )
            response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"Request error while accessing {exc.request.url!r}: {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        print(
            f"HTTP error {exc.response.status_code} while accessing {exc.request.url!r}: {exc}"
        )
        raise
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        raise

    response_data = response.json()
    content_text = response_data.get("content", {}).get("content") or "no response"
    return [types.TextContent.model_construct(type="text", text=content_text)]


async def run_server() -> None:
    """
    Runs the MCP server using stdio streams.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="MCP Toolhouse server",
            server_version="0.2.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


def main() -> None:
    """Main entry point for starting the MCP Toolhouse server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()

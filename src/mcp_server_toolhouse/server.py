# Standard library imports
import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Sequence
import asyncio

# Third-party imports
from openai import AsyncOpenAI
from mcp.server import Server, NotificationOptions, stdio
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from toolhouse import Toolhouse

# Initialize the MCP server
app = Server("mcp-server-toolhouse")


# Custom exception hierarchy for better error handling
class ToolhouseError(Exception):
    """Base exception for Toolhouse-related errors"""

    pass


class ToolFetchError(ToolhouseError):
    """Raised when there's an error fetching tools from the Toolhouse API"""

    pass


class ToolExecutionError(ToolhouseError):
    """Raised when there's an error during tool execution"""

    pass


@dataclass
class ToolhouseConfig:
    """Configuration container for Toolhouse integration with default values"""

    api_key: str = os.getenv("TOOLHOUSE_API_KEY") or TOOLHOUSE_API_KEY
    bundle_name: str = os.getenv("TOOLHOUSE_BUNDLE_NAME", "mcp-toolhouse")
    openai_key: str = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    model: str = "llama-3.3-70b-versatile"  # Default LLM model
    max_tokens: int = 1024  # Maximum tokens for LLM responses
    provider: str = "openai"  # Default API provider
    tool_provider: str = "anthropic"  # Provider for tool execution
    base_url: str = "https://api.groq.com/openai/v1"  # Groq API endpoint

    # Validate required API keys
    if not api_key:
        raise ToolhouseError("Missing TOOLHOUSE_API_KEY environment variable")
    if not openai_key:
        raise ToolhouseError("Missing GROQ_API_KEY environment variable")


def setup_logging() -> logging.Logger:
    """Configure logging with both file and console output"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("mcp-toolhouse.log"), logging.StreamHandler()],
    )
    return logging.getLogger("mcp-server-toolhouse")


LOGGER = setup_logging()


async def get_toolhouse_instance(config: ToolhouseConfig) -> Toolhouse:
    """Initialize Toolhouse and OpenAI client instances with provided configuration"""
    try:
        th = Toolhouse(config.api_key, provider="openai")
        th.set_metadata("id", "orlando")  # Set user identifier
        openai_client = AsyncOpenAI(api_key=config.openai_key, base_url=config.base_url)
        return th, openai_client
    except Exception as e:
        raise ToolhouseError(f"Failed to initialize Toolhouse: {str(e)}")


async def run_server() -> None:
    """Initialize and run the MCP server with stdio communication"""
    try:
        async with stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="toolhouse",
                    server_version="0.1.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        LOGGER.error("Server failed to start", exc_info=True)
        raise McpError(f"Server startup failed: {str(e)}")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Retrieve and format available tools from Toolhouse"""
    try:
        th = Toolhouse(
            provider=ToolhouseConfig.tool_provider, api_key=ToolhouseConfig.api_key
        )
        tools = th.get_tools(ToolhouseConfig.bundle_name)
        # Convert Toolhouse tool format to MCP tool format
        parsed_tools = [
            Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["input_schema"],
            )
            for tool in tools
        ]
        return parsed_tools
    except Exception as e:
        LOGGER.error("Tool listing failed", exc_info=True)
        raise ToolFetchError(f"Failed to list tools: {str(e)}")


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Any | None
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Execute a tool using Groq's LLM API via async OpenAI SDK"""

    # Prepare initial message for the LLM
    messages = [
        {
            "role": "user",
            "content": f"Can you use the tool {name}? Here is some more information that I give you to complete your task: {arguments}",
        }
    ]

    try:
        config = ToolhouseConfig
        th, openai_client = await get_toolhouse_instance(config)
        tools = th.get_tools(config.bundle_name)

        # First LLM call to get tool execution plan
        response = await openai_client.chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=messages,
            tools=tools,
        )

        # Execute tools based on LLM response
        messages.extend(th.run_tools(response))

        # Clean up message content
        for i in range(len(messages)):
            if "audio" in messages[i]:
                del messages[i]["audio"]
            if "refusal" in messages[i]:
                del messages[i]["refusal"]

        # Final LLM call to process tool results
        final_response = await openai_client.chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=messages,
            tools=tools,
        )

        answer = final_response.choices[0].message.content
        return [TextContent(type="text", text=json.dumps(answer, indent=2))]

    except Exception as e:
        raise ToolExecutionError(f"Failed to execute tool: {str(e)}")


async def main():
    """Application entry point with error handling"""
    try:
        await run_server()
    except Exception as e:
        LOGGER.error("Application failed to start", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

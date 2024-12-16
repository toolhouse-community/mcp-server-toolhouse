# toolhouse-mcp MCP Server

MCP project to connect conversational models with Toolhouse's tools. Built on top of [Toolhouse](https://toolhouse.ai/) and Groq's API.

## Features

- Allows compatible MCP Clients, like Claude Desktop App, to access a vast library of tools to enhance their capabilities

## Configuration

### Getting API Keys

1. **Toolhouse API Key**:

   - Sign up at [Toolhouse](https://toolhouse.ai/) and create an account.
   - Obtain your API key from the Toolhouse dashboard.

2. **Groq API Key**:

   - Sign up at [Groq](https://groq.com/) if you don’t already have an account.
   - Get your API key from the API console.

3. Set these environment variables:
   ```bash
   export TOOLHOUSE_API_KEY="your_toolhouse_api_key"
   export GROQ_API_KEY="your_groq_api_key"
   ```

### Run this project locally

This project is not yet configured for ephemeral environments like `uvx`. Run the project locally by cloning the repository:

```bash
git clone https://github.com/toolhouse-community/mcp-server-toolhouse.git
```

Add this tool as an MCP server.

On MacOS:

```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

On Windows:

```bash
%APPDATA%/Claude/claude_desktop_config.json
```

Modify the configuration file to include:

```json
"toolhouse": {
    "command": "uv",
    "args": [
        "--directory",
        "/path/to/this/folder/toolhouse_mcp",
        "run",
        "toolhouse-mcp"
    ],
    "env": {
        "TOOLHOUSE_API_KEY": "your_toolhouse_api_key",
        "GROQ_API_KEY": "your_groq_api_key"
    }
}
```

## TODO

Future improvements include:

- Adding test coverage for all modules
- Extending API support for enhanced tool configurations

## Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging experience, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

Launch the Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm):

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/toolhouse_mcp run toolhouse-mcp
```

The Inspector will display a URL to access debugging tools in your browser.

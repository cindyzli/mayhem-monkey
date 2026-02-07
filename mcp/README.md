# kernel-mcp client

This folder contains a small client that calls the `akakak/kernel-mcp` MCP server using the Dedalus SDK.

## Install

```bash
python -m pip install dedalus-labs python-dotenv
```

## Run

```bash
python mcp/kernel_mcp_client.py --input "Use your tools to summarize kernel-mcp"
```

## Environment variables

- `DEDALUS_API_KEY` - required for Dedalus requests
- `DEDALUS_MODEL` - default `gemini-2.0-flash`
- `KERNEL_MCP_INPUT` - default prompt text
- `KERNEL_MCP_MODEL` - model ID, default `openai/gpt-5-nano`
- `KERNEL_MCP_SERVERS` - comma-separated list, default `akakak/kernel-mcp`


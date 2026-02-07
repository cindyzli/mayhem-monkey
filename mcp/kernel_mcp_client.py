import argparse
import asyncio
import os
from typing import List

from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kernel-mcp via Dedalus")
    parser.add_argument(
        "--input",
        dest="input_text",
        default=os.getenv("KERNEL_MCP_INPUT", "Tell me about kernel-mcp tools."),
        help="Prompt to send to the MCP server",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("KERNEL_MCP_MODEL", "openai/gpt-5-nano"),
        help="Model ID to use",
    )
    parser.add_argument(
        "--mcp",
        nargs="*",
        default=_split_env_list("KERNEL_MCP_SERVERS", ["akakak/kernel-mcp"]),
        help="MCP servers to connect to",
    )
    return parser.parse_args()


def _split_env_list(env_key: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(env_key, "")
    if not raw:
        return fallback
    return [item.strip() for item in raw.split(",") if item.strip()]


async def main() -> None:
    load_dotenv()
    args = _parse_args()

    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input=args.input_text,
        model=args.model,
        mcp_servers=args.mcp,
    )

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())

import argparse
import asyncio
import os
import sys
from typing import List

from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kernel-mcp via Dedalus (Chat Mode)")
    # Removed the "--input" argument since we are now interactive
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

    print(f"--- Dedalus Terminal Chat ---")
    print(f"Model: {args.model}")
    print(f"Servers: {args.mcp}")
    print("Initializing client... (Type 'quit' or 'exit' to stop)")

    # 1. Initialize the client ONCE outside the loop
    try:
        client = AsyncDedalus()
        runner = DedalusRunner(client)
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    # 2. Enter the infinite loop
    while True:
        try:
            # Use standard python input (this blocks until you type)
            user_input = input("\nYou: ").strip()

            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            # Skip empty inputs
            if not user_input:
                continue

            print("Dedalus: Thinking...", end="\r", flush=True)

            # 3. Run the async request
            result = await runner.run(
                input=user_input,
                model=args.model,
                mcp_servers=args.mcp
            )
            
            # Clear the "Thinking..." line and print result
            sys.stdout.write("\033[K") # ANSI escape to clear line (optional polish)
            print(f"Dedalus: {result.final_output}")

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nInterrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
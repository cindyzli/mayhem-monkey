import asyncio
import os
from typing import Dict, List, Optional

from dedalus_labs import AsyncDedalus, DedalusRunner


class DedalusClient:
    def __init__(self, model: Optional[str] = None) -> None:
        self._model = model or os.getenv("DEDALUS_MODEL", "gemini-2.0-flash")

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        system_text = ""
        user_text = ""
        for message in messages:
            if message.get("role") == "system":
                system_text = message.get("content", "")
            elif message.get("role") == "user":
                user_text = message.get("content", "")

        prompt = f"{system_text}\n\nUser:\n{user_text}".strip()

        client = AsyncDedalus()
        runner = DedalusRunner(client)
        result = await runner.run(
            input=prompt,
            model=self._model,
        )
        return result.final_output

    def chat_sync(self, messages: List[Dict[str, str]]) -> str:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.chat(messages))

        if loop.is_running():
            raise RuntimeError("Use chat_async in an active event loop")
        return loop.run_until_complete(self.chat(messages))

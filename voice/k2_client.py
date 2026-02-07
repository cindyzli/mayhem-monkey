import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class K2Client:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: int = 20,
    ) -> None:
        self.api_key = api_key or os.getenv("K2_API_KEY")
        self.api_url = api_url or os.getenv(
            "K2_API_URL", "https://api.k2think.ai/v1/chat/completions"
        )
        self.model = model or os.getenv("K2_MODEL", "MBZUAI-IFM/K2-Think-v2")
        self.timeout_s = timeout_s

        if not self.api_key:
            raise RuntimeError("K2_API_KEY is not set")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        print("one")
        request = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "accept": "application/json",
                "authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
                "User-Agent": "MayhemMonkey/1.0",
            },
            method="POST",
        )
        print("two")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"K2 API error {e.code}: {body}") from e
        print("three")
        parsed: Dict[str, Any] = json.loads(raw)
        choices = parsed.get("choices", [])
        if not choices:
            raise RuntimeError("K2 response missing choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("K2 response missing content")
        return content

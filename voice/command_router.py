import asyncio
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Optional

from chaos_methods import ChaosMonkey

from voice.dedalus_client import DedalusClient


class ChaosCommandRouter:
    def __init__(
        self,
        monkey: ChaosMonkey,
        driver: Any = None,
        dry_run: bool = True,
    ) -> None:
        self.monkey = monkey
        self.driver = driver
        self.dry_run = dry_run if driver is None else dry_run

    def handle_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return

        action = self._infer_action(text)
        self._dispatch(action)

    def _infer_action(self, text: str) -> Dict[str, Any]:
        if os.getenv("DEDALUS_API_KEY"):
            return self._infer_action_with_gemini(text)
        return self._infer_action_with_keywords(text)

    def _infer_action_with_gemini(self, text: str) -> Dict[str, Any]:
        client = DedalusClient()
        prompt = (
            "You are a command router for a safe chaos testing tool. "
            "Pick exactly one action from the allowed list and return JSON only.\n\n"
            "Allowed actions:\n"
            "- open_new_tab(url:str)\n"
            "Return JSON in the format:\n"
            "{\"action\":\"action_name\",\"args\":{...}}"
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ]
        raw = self._run_async(client.chat(messages), timeout_s=15)
        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                action = json.loads(match.group(0))
            else:
                return {"action": "click_random", "args": {"count": 5}}

        if action.get("action") == "open_new_tab":
            url = (action.get("args") or {}).get("url", "")
            if url:
                self._start_gemini_router(url)

        return action

    def _start_gemini_router(self, url: str) -> None:
        router_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "attacker", "gemini_router.py",
        )
        print(f"[ROUTER] Starting gemini_router with {url}")
        subprocess.run([sys.executable, router_path, url])


    def _run_async(self, coro, timeout_s: int):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(asyncio.wait_for(coro, timeout=timeout_s))
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    lambda: asyncio.run(asyncio.wait_for(coro, timeout=timeout_s))
                )
                return future.result(timeout=timeout_s + 2)
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout_s))

    def _extract_url_from_text(self, text: str) -> Optional[str]:
        url_match = re.search(r"https?://[^\s]+", text, re.IGNORECASE)
        if url_match:
            return url_match.group(0).rstrip(").,;")
        domain_match = re.search(
            r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,})\b",
            text,
        )
        if domain_match:
            return f"https://{domain_match.group(1)}"
        return None

    def _infer_action_with_keywords(self, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        default_url = os.getenv("CHAOS_DEFAULT_URL") or os.getenv("CHAOS_START_URL") or "https://www.google.com"
        extracted_url = self._extract_url_from_text(text)
        if "click" in lowered:
            return {"action": "click_random", "args": {"count": 10}}
        if "open" in lowered and "tab" in lowered:
            return {"action": "open_new_tab", "args": {"url": extracted_url or default_url}}
        if "open" in lowered and "chrome" in lowered:
            return {"action": "open_new_tab", "args": {"url": extracted_url or default_url}}
        if extracted_url and any(word in lowered for word in ("open", "go", "navigate", "visit")):
            return {"action": "open_new_tab", "args": {"url": extracted_url}}
        if "extract" in lowered and "link" in lowered:
            return {"action": "extract_links", "args": {"selector": "a[href]"}}
        if "get" in lowered and "link" in lowered:
            return {"action": "extract_links", "args": {"selector": "a[href]"}}
        if "remove" in lowered and "dom" in lowered:
            return {"action": "remove_dom_nodes", "args": {"selector": "header, footer"}}
        if "slow" in lowered or "network" in lowered:
            return {
                "action": "simulate_network_issues",
                "args": {"latency_ms": 800, "throughput_kbps": 128, "offline": False},
            }
        if "scroll" in lowered:
            return {"action": "random_scroll", "args": {"steps": 5}}
        if "reload" in lowered or "refresh" in lowered:
            return {"action": "reload_page", "args": {}}
        if "hide" in lowered:
            return {
                "action": "toggle_visibility",
                "args": {"selector": "nav, aside", "hidden": True},
            }
        if "report" in lowered:
            return {"action": "generate_report", "args": {"path": "chaos_report.json"}}
        return {"action": "click_random", "args": {"count": 5}}

    def _dispatch(self, action: Dict[str, Any]) -> None:
        name = action.get("action")
        args = action.get("args", {}) or {}

        if self.dry_run or self.driver is None:
            self.monkey._record("router_dry_run", "ok", json.dumps(action))
            print(f"[DRY RUN] {action}")
            return

        if not hasattr(self.monkey, name):
            self.monkey._record("router_error", "error", f"unknown action: {name}")
            return

        if name == "open_new_tab" and "url" not in args:
            args["url"] = os.getenv("CHAOS_DEFAULT_URL") or os.getenv("CHAOS_START_URL") or "https://www.google.com"


        if name == "extract_links" and "selector" not in args:
            args["selector"] = "a[href]"

        method = getattr(self.monkey, name)
        result = method(self.driver, **args)
        if name == "extract_links" and isinstance(result, list):
            preview = ", ".join(result[:5])
            print(f"[LINKS] {len(result)} found: {preview}")

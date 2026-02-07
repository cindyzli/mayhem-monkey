import json
import os
from typing import Any, Dict, Optional

from chaos_methods import ChaosMonkey
from voice.k2_client import K2Client


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
        if os.getenv("K2_API_KEY"):
            return self._infer_action_with_k2(text)
        return self._infer_action_with_keywords(text)

    def _infer_action_with_k2(self, text: str) -> Dict[str, Any]:
        client = K2Client()
        prompt = (
            "You are a command router for a safe chaos testing tool. "
            "Pick exactly one action from the allowed list and return JSON only.\n\n"
            "Allowed actions:\n"
            "- click_random(count:int)\n"
            "- open_new_tab(url:str)\n"
            "- remove_dom_nodes(selector:str)\n"
            "- simulate_network_issues(latency_ms:int, throughput_kbps:int, offline:bool)\n"
            "- random_scroll(steps:int)\n"
            "- reload_page()\n"
            "- toggle_visibility(selector:str, hidden:bool)\n"
            "- input_text(selector:str, text:str)\n"
            "- input_value(selector:str, value:str)\n"
            "- input_fuzzing(selector:str, max_payloads:int)\n"
            "- generate_report(path:str)\n\n"
            "If the user does not specify a URL for open_new_tab, "
            "use https://www.google.com.\n\n"
            "Return JSON in the format:\n"
            "{\"action\":\"action_name\",\"args\":{...}}"
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ]
        content = client.chat(messages)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._infer_action_with_keywords(text)

    def _infer_action_with_keywords(self, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        default_url = os.getenv("CHAOS_DEFAULT_URL") or os.getenv("CHAOS_START_URL") or "https://www.google.com"
        if "click" in lowered:
            return {"action": "click_random", "args": {"count": 10}}
        if "open" in lowered and "tab" in lowered:
            return {"action": "open_new_tab", "args": {"url": default_url}}
        if "open" in lowered and "chrome" in lowered:
            return {"action": "open_new_tab", "args": {"url": default_url}}
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

        method = getattr(self.monkey, name)
        method(self.driver, **args)

import argparse
import os
import sys
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from chaos_methods import ChaosMonkey
from voice.dedalus_client import DedalusClient
from voice.selenium_adapter import SeleniumAdapter


ALLOWED_ACTIONS = [
    "click_random(count:int)",
    "open_new_tab(url:str)",
    "remove_dom_nodes(selector:str)",
    "random_scroll(steps:int)",
    "reload_page()",
    "toggle_visibility(selector:str, hidden:bool)",
    "input_text(selector:str, text:str)",
    "input_value(selector:str, value:str)",
    "input_fuzzing(selector:str, max_payloads:int)",
    "extract_links(selector:str)",
    "generate_report(path:str)",
]


def _build_prompt(url: str) -> str:
    return (
        "You are a safe chaos-testing agent. "
        "Choose exactly one action from the allowed list and return JSON only.\n\n"
        f"Target URL: {url}\n\n"
        "Allowed actions:\n"
        + "\n".join(f"- {action}" for action in ALLOWED_ACTIONS)
        + "\n\n"
        "Return JSON in the format:\n"
        "{\"action\":\"action_name\",\"args\":{...}}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Selenium chaos runner")
    parser.add_argument("--url", help="Target URL to open")
    parser.add_argument("--steps", type=int, default=5, help="Number of actions to run")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    url = args.url or input("Enter target URL: ").strip()
    if not url:
        print("No URL provided.")
        sys.exit(1)
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    options = Options()
    if not args.headed:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    adapter = SeleniumAdapter(driver)
    monkey = ChaosMonkey()
    client = DedalusClient()

    adapter.open_new_tab(url)

    prompt = _build_prompt(url)
    for _ in range(args.steps):
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Choose the next safe chaos action."},
        ]
        content = client.chat_sync(messages)
        try:
            action = __import__("json").loads(content)
        except Exception:
            continue

        name = action.get("action")
        args = action.get("args", {}) or {}
        if not hasattr(monkey, name):
            continue
        try:
            getattr(monkey, name)(adapter, **args)
        except Exception:
            continue

    report = monkey.generate_report()
    print(report)
    driver.quit()


if __name__ == "__main__":
    main()

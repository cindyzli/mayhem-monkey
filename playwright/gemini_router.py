import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]

def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dedalus_module = _load_module(
    "mm_dedalus_client",
    ROOT / "voice" / "dedalus_client.py",
)
browser_actions = _load_module(
    "mm_browser_actions",
    ROOT / "playwright" / "browser_actions.py",
)

DedalusClient = dedalus_module.DedalusClient
get_html = browser_actions.get_html
click = browser_actions.click
type_text = browser_actions.type_text


ALLOWED_ACTIONS = ["gethtml", "click", "type_text"]


def _prompt_for_input(label: str) -> str:
    value = input(label).strip()
    if not value:
        raise ValueError(f"{label} is required")
    return value


def _build_prompt(instruction: str, url: str) -> str:
    return (
        "You are routing a browser action. Choose exactly one action from the list "
        "and return JSON only.\n\n"
        f"URL: {url}\n"
        f"Instruction: {instruction}\n\n"
        "Allowed actions:\n"
        "- gethtml (no extra args)\n"
        "- click (requires selector)\n"
        "- type_text (requires selector and text)\n\n"
        "Return JSON in the format:\n"
        '{"action":"gethtml|click|type_text","selector":"...","text":"..."}'
    )


def _parse_response(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Gemini did not return valid JSON")
    action = data.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    return data


def main() -> None:
    url = _prompt_for_input("Enter target URL: ")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    instruction = _prompt_for_input("Describe the action (e.g., 'click login button'): ")

    client = DedalusClient()
    prompt = _build_prompt(instruction, url)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": instruction},
    ]

    raw = client.chat_sync(messages)
    action = _parse_response(raw)

    if action["action"] == "gethtml":
        print(get_html(url))
    elif action["action"] == "click":
        selector = action.get("selector")
        if not selector:
            raise ValueError("selector is required for click")
        print(click(url, selector))
    elif action["action"] == "type_text":
        selector = action.get("selector")
        text = action.get("text")
        if not selector or text is None:
            raise ValueError("selector and text are required for type_text")
        print(type_text(url, selector, text))
    else:
        raise ValueError(f"Unsupported action: {action['action']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

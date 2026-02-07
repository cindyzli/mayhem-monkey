import json
import os
import sys
from typing import Any, Dict

# UPDATED: Import the new library and types
from google import genai
from google.genai import types

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

ALLOWED_ACTIONS = ["get_html", "click", "type_text"]

SYSTEM_PROMPT = """You are a penetration tester for a website and you are trying to execute a SQL injection attack.

You will be given the raw HTML for the page. You are able to perform the following 2 actions:
click(url: str, selector: str, headed: bool = False)
input_text(url: str, selector: str, text: str, submit: bool = False, headed: bool = False)

When you want to take an action, respond with ONLY a JSON object in one of these formats:
{"action":"click","selector":"..."}
{"action":"type_text","selector":"...","text":"..."}

Once you have reached the end of the task, output ONLY a JSON in the following format and replace "<attack_result>" with a description of the success:
{"result": "<attack_result>"}
"""


def _prompt_for_input(label: str) -> str:
    value = input(label).strip()
    if not value:
        raise ValueError(f"{label} is required")
    return value


def _parse_response(raw: str) -> Dict[str, Any]:
    # Some basic cleanup to find JSON
    for candidate in [raw.splitlines()[-1], raw]:
        candidate = candidate.strip()
        if candidate.startswith("```"):
            candidate = "\n".join(candidate.split("\n")[1:])
        if candidate.endswith("```"):
            candidate = candidate[: candidate.rfind("```")]
        candidate = candidate.strip()
        try:
            data = json.loads(candidate)
            # Check if it's a valid action or a result
            if data.get("action") in ALLOWED_ACTIONS or "result" in data:
                return data
        except json.JSONDecodeError:
            continue
    # If we fall through, it's invalid
    raise ValueError(f"Gemini did not return valid JSON. Raw response:\n{raw}")


def _execute_action(page, action: Dict[str, Any]) -> str:
    # Handle the 'result' case (task complete)
    if "result" in action:
        return f"Task complete: {action['result']}"

    name = action.get("action")

    if name == "get_html":
        return page.content()

    elif name == "click":
        selector = action.get("selector")
        if not selector:
            return "Error: selector is required for click"
        try:
            page.click(selector, timeout=5000)
            page.wait_for_load_state("domcontentloaded")
            return f"Clicked '{selector}'. Page URL is now: {page.url}"
        except Exception as e:
            return f"Click failed: {e}"

    elif name == "type_text":
        selector = action.get("selector")
        text = action.get("text")
        if not selector or text is None:
            return "Error: selector and text are required for type_text"
        try:
            page.fill(selector, text)
            return f"Typed '{text}' into '{selector}'. Page URL: {page.url}"
        except Exception as e:
            return f"Type failed: {e}"

    return f"Unknown action: {name}"


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = _prompt_for_input("Enter target URL: ")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # --- UPDATED GENAI SETUP ---
    # 1. Initialize the Client
    client = genai.Client(api_key=api_key)

    # 2. Create the chat session with configuration
    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7, # Optional: Adds a bit of creativity for attacks
        )
    )
    # ---------------------------

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        print(f"Navigating to {url} ...")
        page.goto(url, wait_until="domcontentloaded")
        print(f"Ready. Page loaded: {page.url}\n")

        while True:
            html = page.content()
            
            # Simple prompt construction
            user_message = (
                f"Current page URL: {page.url}\n"
                f"HTML snippet (first 20000 chars): {html[:20000]}\n\n" # Truncating slightly to be safe
                "What is the next action? Return ONLY JSON."
            )

            try:
                # 3. Send message using the new chat object
                response = chat.send_message(user_message)
                raw = response.text
                print(f"Gemini response: {raw}")

                parsed = _parse_response(raw)

                # Check if the agent says it's done
                if "result" in parsed:
                    print(f"\nTask complete. Result: {parsed['result']}")
                    break

                print(f"Executing Action: {parsed}")
                result_feedback = _execute_action(page, parsed)
                print(f"Action Result: {result_feedback}\n")

                # Note: In a real chat loop, we don't manually 'feed back' the result 
                # immediately unless we prompt again. The loop handles the next prompt.
                # If you want to force the context update immediately without a new user prompt:
                # You rely on the next loop iteration to send the new state (HTML).

            except Exception as e:
                print(f"Error in loop: {e}\n", file=sys.stderr)
                # Break to avoid infinite error loops during testing
                break

    print("Browser closed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
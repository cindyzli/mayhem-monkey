"""
Gemini-driven chaos monkey router.

Keeps a persistent browser open and lets Gemini decide what to do next.
After each action Gemini narrates what it did via ElevenLabs TTS.
The loop continues until Gemini declares it's finished or the user presses Ctrl-C.
"""

import json
import os
import queue
import sys
import tempfile
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from elevenlabs import ElevenLabs, VoiceSettings

from dotenv import load_dotenv

load_dotenv()
last_action = ""

# ---------------------------------------------------------------------------
# Lazy imports for google.genai (require pip install google-genai)
# ---------------------------------------------------------------------------
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# TTS helper – speaks text out loud using ElevenLabs (same logic as voice/tts.py)
# ---------------------------------------------------------------------------
_elevenlabs_client = None
_tts_queue: queue.Queue = queue.Queue()


def _tts_worker():
    """Background thread that plays TTS clips sequentially."""
    while True:
        path = _tts_queue.get()
        if path is None:
            break
        try:
            subprocess.run(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            os.unlink(path)
        except Exception:
            pass
        _tts_queue.task_done()


_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()


def _get_elevenlabs():
    global _elevenlabs_client
    if _elevenlabs_client is None:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return None

        _elevenlabs_client = ElevenLabs(api_key=api_key)
    return _elevenlabs_client


def speak(text: str) -> None:
    """Speak *text* aloud. Silently skips if ElevenLabs isn't configured."""
    client = _get_elevenlabs()
    if client is None:
        print(f"[TTS unavailable] {text}")
        return
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id="onwK4e9ZLuTAKqWW03F9",  # Daniel - Steady Broadcaster
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(speed=1.2)
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        for chunk in audio:
            tmp.write(chunk)
        tmp.close()

        if sys.platform == "darwin":
            _tts_queue.put(tmp.name)
        else:
            print(f"[TTS] {text}")
    except Exception as exc:
        print(f"[TTS error] {exc}")


# ---------------------------------------------------------------------------
# Evidence capture — watches for JS dialogs, console errors, page crashes
# ---------------------------------------------------------------------------
_dialog_log: List[Dict[str, str]] = []
_console_errors: List[str] = []


def _install_page_monitors(page) -> None:
    """Attach listeners that capture evidence of vulnerabilities."""

    def _on_dialog(dialog):
        entry = {
            "type": dialog.type,           # alert / confirm / prompt
            "message": dialog.message,
        }
        _dialog_log.append(entry)
        print(f"  [DIALOG {dialog.type}] {dialog.message}")
        import time
        time.sleep(2)  # Wait 3 seconds so you can see the alert
        dialog.accept()                    # dismiss so automation isn't blocked

    def _on_console(msg):
        if msg.type in ("error", "warning"):
            text = msg.text[:300]
            _console_errors.append(text)

    page.on("dialog", _on_dialog)
    page.on("console", _on_console)


def _collect_evidence(page, *, url_before: str) -> str:
    """
    Snapshot observable side-effects right after an action.
    Returns a human-readable string that gets sent back to Gemini.
    """
    parts: List[str] = []

    # 1. JS dialogs (alert/confirm/prompt) — strongest XSS signal
    if _dialog_log:
        parts.append(
            "JS DIALOGS triggered: "
            + "; ".join(f"[{d['type']}] {d['message']}" for d in _dialog_log)
        )
        _dialog_log.clear()

    # 2. Console errors / warnings
    if _console_errors:
        parts.append(
            "Console errors: " + "; ".join(_console_errors[-5:])
        )
        _console_errors.clear()

    # 3. URL changed? (redirect after injection = interesting)
    if page.url != url_before:
        parts.append(f"URL changed: {url_before} -> {page.url}")

    # 4. Page title (sometimes reflects injected content)
    try:
        title = page.title()
        if title:
            parts.append(f"Page title: {title}")
    except Exception:
        pass

    # 5. Visible error messages / banners on the page
    try:
        error_text = page.evaluate(r"""() => {
            const markers = [];
            // Look for common error containers
            const selectors = [
                '.error', '.alert', '.warning', '.danger', '.flash',
                '[role="alert"]', '.notice', '.message', '.toast',
                '.notification', '.err', '.field-error', '.form-error',
            ];
            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    const t = (el.textContent || '').trim();
                    if (t && t.length < 500) markers.push(t);
                }
            }
            // Also check if any raw payload text appears in <body>
            const body = document.body ? document.body.innerText : '';
            const patterns = ['<script', 'onerror=', 'javascript:', 'SQL', 'syntax',
                              'error', 'exception', 'stack trace', 'unexpected'];
            for (const p of patterns) {
                const idx = body.toLowerCase().indexOf(p.toLowerCase());
                if (idx !== -1) {
                    markers.push('REFLECTED: ...' + body.substring(Math.max(0,idx-30), idx+60) + '...');
                    break;
                }
            }
            return markers.slice(0, 5).join(' | ');
        }""")
        if error_text:
            parts.append(f"Page signals: {error_text}")
    except Exception:
        pass

    # 6. Brief HTML snippet (first 3000 chars of the *current* page)
    try:
        html_snippet = page.content()[:3000]
        parts.append(f"HTML after action (first 3000 chars):\n{html_snippet}")
    except Exception:
        pass

    return "\n".join(parts) if parts else "No notable side-effects observed."


# ---------------------------------------------------------------------------
# Allowed actions – includes input_text as an alias for type_text
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = {"get_html", "click", "type_text", "input_text", "goto"}

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
RESULTS_FILE = os.path.join(RESULTS_DIR, "scan_results.json")

SYSTEM_PROMPT = """SYSTEM_PROMPT = \
You are a senior security QA engineer testing a web application that you own \
and have explicit permission to test.

Goal:
1) Identify whether the application is vulnerable to common input-handling \
issues (SQLi, reflected/stored XSS, auth/session flaws, broken access control).
2) Provide a clear reproduction path and evidence for any finding.

Each turn you will receive:
- The page HTML.

You can interact with the page using these actions:
  click       – requires "selector"
  type_text   – requires "selector" and "text"
  goto        – requires "url" (navigate the browser to a new URL). ONLY USE TO GET SEARCH VULNERABILITY BELOW.
  get_html    – no extra fields

Selector Rules (CRITICAL):
- **ALWAYS use text selectors**: Playwright can find elements by text. ALWAYS use "text=Submit" or "text=Sign In" instead of generic CSS.
- **Be specific**: Use unique IDs (#id) or compound classes (.class.other) if text is unavailable.

Rules:
- Try multiple payload variations on each input before moving on.
- Always try an exploit on every page if available before moving on. Never move on before testing edit buttons.
- No matter what, do not reload the page or navigate away after injecting a payload. Press submit immediately after filling out the payload.
- Move on immediately if a certain exploit does not work

*** OUTPUT FORMAT ***
Return EXACTLY one JSON object per turn. Include a "thinking" field. Be VERY VERY brief with the thinking field.

Action example:
{"thinking":"I will try an XSS exploit.","action":"click","selector":"text=Submit"}
{"thinking":"I will try an SQL injection in the password field.","action":"type_text","selector":"input[name='title']","text":"<script>alert('xss')</script>"}

Once the search vulnerability has been found after visiting all pages, create a final report JSON so the UI can render it. The schema you MUST STRICTLY FOLLOW is:
{
  "vulnerabilities": [
    {
      "title": "One-line summary of the finding",
      "severity": "critical | high | medium | low",
      "category": "SQL Injection | Cross-Site Scripting | CSRF Protection | Authentication | Authorization | Encryption | Input Validation | File Upload | Session Management | API Security",
      "details": {
        "description": "What you did and what happened (2-3 sentences).",
        "impact": "Why this matters to the business/user.",
        "recommendation": "One concrete fix or mitigation.",
        "codeSnippet": "Optional evidence snippet or repro command."
      }
    }
  ]
}
You may return multiple vulnerabilities in the array, but every entry MUST include each field above and use one of the four allowed severity strings exactly as written. Do not return any other JSON shape.
"""

MAX_CONSECUTIVE_ERRORS = 5          # give up after this many parse/action failures in a row
INTER_STEP_DELAY = 0        # seconds between actions (avoids rate-limits)


def _parse_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from Gemini's response, tolerating markdown fences."""
    text = raw.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    text = text.strip()

    # Try the whole thing first, then the last line
    for candidate in [text, text.splitlines()[-1].strip()]:
        try:
            data = json.loads(candidate)
            action = data.get("action")
            
            # Normalise input_text -> type_text
            if action == "input_text":
                data["action"] = "type_text"
                action = "type_text"

            # --- FIX IS HERE ---
            # Allow "headerTitle" to pass through validation
            if action in ALLOWED_ACTIONS or "vulnerabilities" in data or "severity" in data:
                return data
            # -------------------

        except (json.JSONDecodeError, IndexError):
            continue

    raise ValueError(f"Could not parse Gemini response:\n{raw[:500]}")


def _auto_submit(page, input_selector: str = "") -> Optional[str]:
    """
    Submit the form that owns the element we just typed into.
    Only clicks the submit button *inside that form* — never random page buttons.
    Returns a description of what was clicked, or None.
    """
    # ---- Strategy 1: find the <form> wrapping the input, click its submit ----
    try:
        result = page.evaluate("""(inputSel) => {
            // Find the input we just filled
            let input = inputSel ? document.querySelector(inputSel) : document.activeElement;
            if (!input) input = document.activeElement;
            const form = input ? input.closest('form') : null;
            if (!form) return null;

            // Look for the form's own submit trigger
            let btn = form.querySelector("input[type='submit'], button[type='submit']");
            if (!btn) btn = form.querySelector("button:not([type='button']):not([type='reset'])");
            if (btn && btn.offsetParent !== null) {
                btn.scrollIntoView({behavior:'instant', block:'center'});
                btn.click();
                return 'Clicked form submit: ' + (btn.textContent || btn.value || 'submit').trim();
            }

            // No button — submit the form directly
            try { form.requestSubmit(); } catch(e) { form.submit(); }
            return 'Submitted form via JS';
        }""", input_selector)
        if result:
            # Brief wait — do NOT use wait_for_load_state which forces a full reload wait
            time.sleep(1.0)
            return result
    except Exception:
        pass

    return None


def _get_filled_input_summary(page) -> str:
    """Return a short summary of current input values so Gemini knows fields are filled."""
    try:
        summary = page.evaluate("""() => {
            const inputs = document.querySelectorAll('input, textarea');
            const filled = [];
            for (const el of inputs) {
                const val = el.value;
                if (val && val.length > 0) {
                    const id = el.name || el.id || el.type || 'input';
                    // Mask passwords
                    const display = el.type === 'password' ? '***' : val.substring(0, 40);
                    filled.push(id + '=' + JSON.stringify(display));
                }
            }
            return filled.join(', ');
        }""")
        return summary
    except Exception:
        return ""


def _execute_action(page, data: Dict[str, Any]) -> str:
    global last_action
    """Run the action on the live Playwright page and return a feedback string."""
    action = data.get("action")
    last_action = f"last action: {data}"
    
    if action == "goto":
        target_url = data.get("url", "")
        if not target_url:
            return "Error: 'url' is required for goto"
        url_before = page.url
        try:
            page.goto(target_url, wait_until="domcontentloaded")
            evidence = _collect_evidence(page, url_before=url_before)
            return f"Navigated to {page.url}\n{evidence}"
        except Exception as exc:
            return f"Navigation to '{target_url}' failed: {exc}"

    if action == "get_html":
        html = page.content()
        filled = _get_filled_input_summary(page)
        extra = f"\nCurrent input values: {filled}" if filled else ""
        return f"Got HTML ({len(html)} chars){extra}"

    if action == "click":
        selector = data.get("selector", "")
        if not selector:
            return "Error: 'selector' is required for click"
        url_before = page.url
        try:
            # --- UPDATED CLICK LOGIC ---
            # Create a locator and grab the first match to avoid "strict mode" errors
            loc = page.locator(selector).first
            
            # Wait for it to be ready, then click
            loc.wait_for(state="visible", timeout=5000)
            loc.click(timeout=5000)
            
            # Wait a moment for JS to fire or page to reload
            time.sleep(1.0) 
            
            # NOW collect evidence
            evidence = _collect_evidence(page, url_before=url_before)
            return f"Clicked '{selector}'.\n{evidence}"
            # ---------------------------

        except Exception as exc:
            evidence = _collect_evidence(page, url_before=url_before)
            return f"Click failed on '{selector}': {exc}\n{evidence}"

    if action == "type_text":
        selector = data.get("selector", "")
        text = data.get("text")
        if not selector or text is None:
            return "Error: 'selector' and 'text' are required for type_text"
        url_before = page.url
        try:
            page.wait_for_selector(selector, state="visible", timeout=5000)
            # strict=True ensures we don't type into a hidden or wrong input
            page.fill(selector, text, strict=True)
            
            if data.get("submit"):
                page.press(selector, "Enter")
                page.wait_for_load_state("domcontentloaded")
            return f"Typed into '{selector}'. URL: {page.url}"
            page.wait_for_selector(selector, timeout=5000)
            page.fill(selector, text)
            result_msg = f"Typed '{text}' into '{selector}'."

            # --- Submit only the form that owns this input --------------------
            time.sleep(0.3)
            submit_result = _auto_submit(page, input_selector=selector)
            if submit_result:
                result_msg += f" {submit_result}."
            else:
                result_msg += " No form found; payload injected but not submitted."

            # --- Capture evidence IMMEDIATELY after submit --------------------
            time.sleep(0.5)
            evidence = _collect_evidence(page, url_before=url_before)
            result_msg += f"\n{evidence}"
            return result_msg
        except Exception as exc:
            evidence = _collect_evidence(page, url_before=url_before)
            return f"Type failed on '{selector}': {exc}\n{evidence}"

    return f"Unknown action '{action}'"


def attack_page(url: str, threat_summary: str = "") -> None:
    """Launch the Gemini chaos-monkey loop against a single page."""
    main(url=url, threat_summary=threat_summary)


def main(url: Optional[str] = None, threat_summary: str = "") -> None:
    global last_action
    print(f"[gemini_router main] Received URL arg: {url!r}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    if url is None:
        url = input("Enter target URL: ").strip()
    if not url:
        raise SystemExit("URL is required")
    if url.startswith("http://"):
        url = url.replace("http://", "https://")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    print(f"[gemini_router main] Final URL for browser: {url!r}")

    # --- Gemini chat session ---
    client = genai.Client(api_key=api_key)
    chat = client.chats.create(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )

    speak(f"Starting chaos test on {url}")

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        _install_page_monitors(page)
        print(f"Navigating to {url} ...")
        page.goto(url, wait_until="domcontentloaded")
        print(f"Page loaded: {page.url}\n")

        consecutive_errors = 0
        step = 0

        while True:
            step += 1
            html = page.content()

            filled = _get_filled_input_summary(page)
            filled_note = f"\nCurrent input values: {filled}" if filled else ""

            # Capture screenshot before each step
            screenshot_path = os.path.join(SCREENSHOT_DIR, f"step_{step}.png")
            # screenshot_bytes = page.screenshot(full_page=True)
            # with open(screenshot_path, "wb") as f:
            #     f.write(screenshot_bytes)
            # print(f"Screenshot saved: {screenshot_path}")

            # Build multimodal message: screenshot image + HTML text
            # screenshot_part = types.Part.from_bytes(
            #     data=screenshot_bytes,
            #     mime_type="image/png",
            # )
            text_part = (
                f"Current page URL: {page.url}\n"
                f"HTML (first 15000 chars):\n{html[:15000]}\n"
                f"{filled_note}\n\n"
                "What is the next action? Return ONLY the JSON object."
            )

            try:
                print(last_action)
                response = chat.send_message([last_action, text_part])
                raw = response.text.strip()
                print(f"\n--- Step {step} ---")
                print(f"Gemini: {raw}")

                parsed = _parse_response(raw)
                consecutive_errors = 0  # reset on success

                # Finished?
                if "vulnerabilities" in parsed:
                    # 1. Save results IMMEDIATEY
                    os.makedirs(RESULTS_DIR, exist_ok=True)
                    with open(RESULTS_FILE, "w") as rf:
                        json.dump(parsed, rf, indent=2)
                    
                    print(f"\nDone! Results saved to {RESULTS_FILE}")
                    
                    # 2. Speak a short confirmation, NOT the raw JSON
                    speak("Vulnerability scan complete. Results have been saved.")

                    break


                # Narrate the thinking
                thinking = parsed.get("thinking", "")
                if thinking:
                    print(f"Thinking: {thinking}")
                    speak(thinking)
                    _tts_queue.join()  # wait for TTS to finish before next action

                

                # Execute
                feedback = _execute_action(page, parsed)
                print(f"Result: {feedback}")

            except Exception as exc:
                consecutive_errors += 1
                print(f"[Step {step}] Error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {exc}",
                      file=sys.stderr)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    speak("Too many errors in a row. Stopping.")
                    print("Too many consecutive errors — stopping.", file=sys.stderr)
                    break
                # Tell Gemini about the error so it can adapt
                try:
                    chat.send_message(
                        f"The previous response caused an error: {exc}. "
                        "Please try a different approach. Return ONLY JSON."
                    )
                except Exception:
                    pass

            time.sleep(INTER_STEP_DELAY)

        browser.close()
    print("Browser closed.")


if __name__ == "__main__":
    try:
        url = sys.argv[1] if len(sys.argv) > 1 else None
        main(url=url)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as exc:
        print(f"Fatal: {exc}", file=sys.stderr)
        sys.exit(1)

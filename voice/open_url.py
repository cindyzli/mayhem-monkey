"""
Standalone voice listener that waits for "open <webpage>" commands
and pipes the URL to gemini_router to start security testing.

Requires:
  - capture.py running on localhost:30000 (microphone stream)
  - ELEVENLABS_API_KEY in .env
  - GEMINI_API_KEY in .env
"""

import asyncio
import os
import re
import urllib.request
import urllib.error

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, RealtimeEvents, RealtimeUrlOptions
from elevenlabs import CommitStrategy
import concurrent.futures
import json
from typing import Optional

from dedalus_client import DedalusClient

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")



def _extract_url(text: str) -> str | None:
    """
    Pull a URL or domain out of a voice transcript like
    'open google.com', 'open https://example.com', 'go to reddit.com'.
    Returns a full URL or None.
    """
    print(f"[_extract_url] Input: {text!r}")

    # Explicit URL
    url_match = re.search(r"https?://[^\s]+", text, re.IGNORECASE)
    if url_match:
        extracted = url_match.group(0).rstrip(").,;")
        print(f"[_extract_url] Explicit URL found: {extracted!r}")
        return extracted

    # Domain-like pattern after trigger words
    trigger = re.search(
        r"\b(?:open|go\s+to|navigate\s+to|visit|attack|test|scan)\s+(.+)",
        text,
        re.IGNORECASE,
    )
    if trigger:
        remainder = trigger.group(1).strip().rstrip(".")
        print(f"[_extract_url] Remainder after trigger: {remainder!r}")
        domain_match = re.search(
            r"\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}(?::\d+)?(?:/\S*)?)\b",
            remainder,
        )
        if domain_match:
            extracted_domain = domain_match.group(1)
            final_url = f"https://{extracted_domain}"
            print(f"[_extract_url] Domain matched: {extracted_domain!r} -> {final_url!r}")
            return final_url
        else:
            print(f"[_extract_url] No domain match in remainder")

    print(f"[_extract_url] No URL found")
    return None

def _run_async(coro, timeout_s: int = 15):
    """Run an async coroutine from sync code, handling nested event loops."""
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


def _infer_action_with_gemini(text: str) -> Optional[str]:
    """Use Gemini to decide if the user wants to open a URL."""
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
    raw = _run_async(client.chat(messages), timeout_s=15)
    try:
        action = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            action = json.loads(match.group(0))
        else:
            return None

    if action.get("action") == "open_new_tab":
        url = (action.get("args") or {}).get("url", "")
        if url:
            return url

    return None


def _start_gemini_router(url: str) -> bool:
    """Tell app.py to launch the scanner for the given URL. Returns True on success."""
    print(f"[open_url] Requesting scan for: {url}")
    data = json.dumps({"url": url}).encode("utf-8")
    req = urllib.request.Request(
        f"{BACKEND_URL}/scan/start",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            print(f"[open_url] Scanner response: {body}")
            return True
    except urllib.error.URLError as exc:
        print(f"[open_url] Failed to start scanner via API: {exc}")
        return False


def _stop_voice_pipeline() -> None:
    """Tell app.py to stop capture.py (microphone)."""
    req = urllib.request.Request(f"{BACKEND_URL}/stop", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5):
            print("[open_url] Voice pipeline stopped")
    except urllib.error.URLError:
        pass


async def main():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in .env")

    elevenlabs = ElevenLabs(api_key=api_key)
    stop_event = asyncio.Event()

    connection = await elevenlabs.speech_to_text.realtime.connect(
        RealtimeUrlOptions(
            model_id="scribe_v2_realtime",
            url="http://localhost:30000/stream",
            commit_strategy=CommitStrategy.VAD,
            vad_silence_threshold_secs=1.5,
            vad_threshold=0.4,
            min_speech_duration_ms=100,
            min_silence_duration_ms=100,
            include_timestamps=False,
        )
    )

    def on_session_started(_data):
        print("[open_url] STT session started — say 'open <website>' to begin")

    def on_committed_transcript(data):
        text = (data.get("text", "") or "").strip()
        if not text:
            return
        print(f"[open_url] Heard: {text}")

        url = _extract_url(text)
        if not url and os.getenv("DEDALUS_API_KEY"):
            url = _infer_action_with_gemini(text)
        if url:
            if _start_gemini_router(url):
                print("[open_url] URL detected, stopping voice pipeline...")
                _stop_voice_pipeline()
                stop_event.set()
        else:
            print(f"[open_url] No URL detected, ignoring.")

    def on_error(error):
        print(f"[open_url] STT error: {error}")
        stop_event.set()

    def on_close():
        print("[open_url] Connection closed")

    connection.on(RealtimeEvents.SESSION_STARTED, on_session_started)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
    connection.on(RealtimeEvents.ERROR, on_error)
    connection.on(RealtimeEvents.CLOSE, on_close)

    print("[open_url] Listening for 'open <website>' commands... (Ctrl+C to stop)")

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\n[open_url] Stopping...")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Simple Playwright browser automation: click buttons, submit text, get raw HTML.

Usage:
    python playwright/browser_actions.py <url> --action get_html
    python playwright/browser_actions.py <url> --action click --selector "button#submit"
    python playwright/browser_actions.py <url> --action type --selector "input[name='q']" --text "hello"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def get_html(url: str, headed: bool = False) -> str:
    """Navigate to a URL and return the raw HTML."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        html = page.content()
        browser.close()
    return html


def click(url: str, selector: str, headed: bool = False) -> str:
    """Navigate to a URL, click an element matching the selector, and return the resulting HTML."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.click(selector)
        page.wait_for_load_state("domcontentloaded")
        html = page.content()
        browser.close()
    return html


def type_text(url: str, selector: str, text: str, submit: bool = False, headed: bool = False) -> str:
    """Navigate to a URL, fill a text field, optionally submit the form, and return the resulting HTML."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.fill(selector, text)
        if submit:
            page.press(selector, "Enter")
            page.wait_for_load_state("domcontentloaded")
        html = page.content()
        browser.close()
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple Playwright browser actions")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--action", required=True, choices=["get_html", "click", "type"], help="Action to perform")
    parser.add_argument("--selector", help="CSS selector for click/type targets")
    parser.add_argument("--text", help="Text to type (for 'type' action)")
    parser.add_argument("--submit", action="store_true", help="Press Enter after typing to submit")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    args = parser.parse_args()

    url = args.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    if args.action == "get_html":
        print(get_html(url, headed=args.headed))

    elif args.action == "click":
        if not args.selector:
            print("Error: --selector is required for click action", file=sys.stderr)
            sys.exit(1)
        print(click(url, args.selector, headed=args.headed))

    elif args.action == "type":
        if not args.selector or args.text is None:
            print("Error: --selector and --text are required for type action", file=sys.stderr)
            sys.exit(1)
        print(type_text(url, args.selector, args.text, submit=args.submit, headed=args.headed))


if __name__ == "__main__":
    main()

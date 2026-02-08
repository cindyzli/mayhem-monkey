import os
import sys
import argparse
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# Allow importing from sibling packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from attacker.gemini_router import attack_page

load_dotenv()


def evaluate_vulnerabilities(html: str) -> str:
    """Ask Gemini to evaluate a page's HTML for potential security vulnerabilities."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  [WARN] GEMINI_API_KEY not set, skipping vulnerability evaluation")
        return ""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=f"Evaluate this page for any potential security vulnerabilities:\n\n{html[:15000]}",
    )
    return response.text.strip()


def crawl(start_url, max_pages=100):
    """Crawl a website starting from start_url and attack each page."""
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    if not base_domain:
        print(f"Error: invalid URL '{start_url}'")
        sys.exit(1)

    visited = set()
    queue = deque([start_url])
    page_count = 0

    session = requests.Session()
    session.headers.update({
        "User-Agent": "MayhemMonkeyCrawler/1.0",
    })

    print(f"Crawling {start_url} (domain: {base_domain})")

    while queue and page_count < max_pages:
        url = queue.popleft()
        url = urldefrag(url).url  # strip fragment

        if url in visited:
            continue
        visited.add(url)

        try:
            resp = session.get(url, timeout=10)
        except requests.RequestException as e:
            print(f"  SKIP {url} ({e})")
            continue

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            continue

        page_count += 1
        print(f"  [{page_count}] Evaluating {url} for vulnerabilities...")
        threat_summary = evaluate_vulnerabilities(resp.text)
        print(f"  Threat summary: {threat_summary[:200]}")
        print(f"  Attacking {url}")
        attack_page(url, threat_summary=threat_summary)

        # Parse and enqueue links
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            link = urljoin(url, tag["href"])
            link = urldefrag(link).url
            parsed_link = urlparse(link)

            # Stay on the same domain, only http(s)
            if parsed_link.scheme in ("http", "https") and parsed_link.netloc == base_domain:
                if link not in visited:
                    queue.append(link)

    print(f"\nDone. Attacked {page_count} pages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a website and attack each page.")
    parser.add_argument("url", help="The starting URL to crawl")
    parser.add_argument("-m", "--max-pages", type=int, default=100, help="Max pages to crawl (default: 100)")
    args = parser.parse_args()

    crawl(args.url, max_pages=args.max_pages)

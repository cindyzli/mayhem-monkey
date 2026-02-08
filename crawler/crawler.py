import os
import sys
import hashlib
import argparse
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque

import requests
from bs4 import BeautifulSoup


def sanitize_filename(url):
    """Convert a URL into a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    if parsed.query:
        path += "_" + hashlib.md5(parsed.query.encode()).hexdigest()[:8]
    if not path.endswith(".html"):
        path += ".html"
    return path


def crawl(start_url, output_dir="crawled_pages", max_pages=100):
    """Crawl a website starting from start_url and save all HTML pages."""
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    if not base_domain:
        print(f"Error: invalid URL '{start_url}'")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    visited = set()
    queue = deque([start_url])
    saved_count = 0

    session = requests.Session()
    session.headers.update({
        "User-Agent": "MayhemMonkeyCrawler/1.0",
    })

    print(f"Crawling {start_url} (domain: {base_domain})")
    print(f"Saving HTML files to: {os.path.abspath(output_dir)}/")

    while queue and saved_count < max_pages:
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

        # Save the HTML file
        filename = sanitize_filename(url)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(resp.text)
        saved_count += 1
        print(f"  [{saved_count}] Saved {url} -> {filename}")

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

    print(f"\nDone. Saved {saved_count} pages to {os.path.abspath(output_dir)}/")
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a website and save all HTML pages.")
    parser.add_argument("url", help="The starting URL to crawl")
    parser.add_argument("-o", "--output", default="crawled_pages", help="Output directory (default: crawled_pages)")
    parser.add_argument("-m", "--max-pages", type=int, default=100, help="Max pages to crawl (default: 100)")
    args = parser.parse_args()

    crawl(args.url, output_dir=args.output, max_pages=args.max_pages)

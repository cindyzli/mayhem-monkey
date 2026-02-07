#!/usr/bin/env python3
"""
CLI entry point for the Mayhem Monkey pentesting engine.

Run from the project root:
    python playwright/run.py <target_url> [options]

Examples:
    # Run all checks
    python playwright/run.py https://target.example.com

    # Run specific checks
    python playwright/run.py https://target.example.com --checks xss sqli security_headers

    # Run with visible browser
    python playwright/run.py https://target.example.com --headed

    # Save report to file
    python playwright/run.py https://target.example.com --output report.json

    # Set crawl depth
    python playwright/run.py https://target.example.com --depth 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the playwright/ directory is on sys.path so sibling imports work
_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

from pentest_engine import PentestEngine


AVAILABLE_CHECKS = [
    "recon",
    "security_headers",
    "cookie_security",
    "xss",
    "sqli",
    "csrf",
    "open_redirect",
    "sensitive_paths",
    "clickjacking",
    "form_security",
    "input_fuzzing",
    "mixed_content",
    "info_disclosure",
    "auth_testing",
    "cors",
    "subdomain_takeover",
]

SEVERITY_COLORS = {
    "critical": "\033[91m",  # red
    "high": "\033[93m",      # yellow
    "medium": "\033[33m",    # orange
    "low": "\033[94m",       # blue
    "info": "\033[90m",      # gray
}
RESET = "\033[0m"


def print_banner() -> None:
    print(
        r"""
  __  __             _                     __  __             _
 |  \/  | __ _ _   _| |__   ___ _ __ ___  |  \/  | ___  _ __ | | _____ _   _
 | |\/| |/ _` | | | | '_ \ / _ \ '_ ` _ \ | |\/| |/ _ \| '_ \| |/ / _ \ | | |
 | |  | | (_| | |_| | | | |  __/ | | | | || |  | | (_) | | | |   <  __/ |_| |
 |_|  |_|\__,_|\__, |_| |_|\___|_| |_| |_||_|  |_|\___/|_| |_|_|\_\___|\__, |
               |___/                                                     |___/
                        Playwright Pentesting Engine
    """
    )


def print_summary(report: dict) -> None:
    summary = report["summary"]
    total = report["total_findings"]

    print(f"\n{'='*60}")
    print(f"  TARGET:  {report['target']}")
    print(f"  TIME:    {report['timestamp']}")
    print(f"  PAGES:   {report['pages_crawled']} crawled")
    print(f"  FORMS:   {report['forms_discovered']} discovered")
    print(f"{'='*60}")
    print(f"\n  FINDINGS: {total} total\n")

    for sev in ("critical", "high", "medium", "low", "info"):
        count = summary.get(sev, 0)
        color = SEVERITY_COLORS.get(sev, "")
        bar = "#" * count
        print(f"    {color}{sev.upper():>10}{RESET}  {count:>3}  {color}{bar}{RESET}")

    print(f"\n{'='*60}")

    if total == 0:
        print("  No vulnerabilities found. Target appears well-hardened.")
        return

    # Group findings by category
    by_category: dict = {}
    for f in report["findings"]:
        cat = f["category"]
        by_category.setdefault(cat, []).append(f)

    for category, findings in by_category.items():
        print(f"\n  [{category.upper()}]")
        for f in findings:
            sev = f["severity"]
            color = SEVERITY_COLORS.get(sev, "")
            print(f"    {color}[{sev.upper()}]{RESET} {f['title']}")
            if f.get("description"):
                print(f"           {f['description'][:120]}")
            if f.get("evidence"):
                print(f"           Evidence: {f['evidence'][:120]}")
            if f.get("url"):
                print(f"           URL: {f['url'][:120]}")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mayhem Monkey Playwright Pentesting Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("target_url", help="Target URL to pentest")
    parser.add_argument(
        "--checks",
        nargs="+",
        choices=AVAILABLE_CHECKS,
        default=None,
        help="Specific checks to run (default: all)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Max crawl depth (default: 2)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10000,
        help="Page timeout in ms (default: 10000)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save JSON report to file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON only (no pretty-print)",
    )

    args = parser.parse_args()
    target = args.target_url

    # Ensure URL has a scheme
    if not target.startswith(("http://", "https://")):
        target = f"https://{target}"

    if not args.json:
        print_banner()
        print(f"  Target: {target}")
        print(f"  Checks: {', '.join(args.checks) if args.checks else 'ALL'}")
        print(f"  Depth:  {args.depth}")
        print(f"  Mode:   {'Headed' if args.headed else 'Headless'}")
        print()

    engine = PentestEngine(headless=not args.headed, timeout=args.timeout)

    if not args.json:
        print("  Running pentest...")

    report = engine.run(
        target_url=target,
        checks=args.checks,
        max_crawl_depth=args.depth,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        if not args.json:
            print(f"\n  Report saved to: {args.output}")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)


if __name__ == "__main__":
    main()

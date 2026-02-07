"""
Chaos Monkey methods (safe failure injection).

These helpers are intentionally non-exploitative: they focus on resilience testing
without attempting security attacks. Integrate with your chosen browser driver
(e.g., Playwright or Selenium) by adapting the driver interface used below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import random
from typing import Any, Callable, Iterable, List, Optional, Sequence


@dataclass
class ActionResult:
    name: str
    status: str
    details: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ChaosMonkey:
    """
    Safe chaos-testing helpers for UI and runtime resilience.

    The driver object is intentionally generic. You can pass in a Playwright page,
    Selenium driver, or your own adapter object that implements the required
    methods for each action.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._results: List[ActionResult] = []

    @property
    def results(self) -> List[ActionResult]:
        return list(self._results)

    def _record(self, name: str, status: str, details: str = "") -> None:
        self._results.append(ActionResult(name=name, status=status, details=details))

    def _find_element(self, driver: Any, selector: str) -> Any:
        if hasattr(driver, "query_selector"):
            return driver.query_selector(selector)
        if hasattr(driver, "find_element_by_css_selector"):
            return driver.find_element_by_css_selector(selector)
        if hasattr(driver, "find_element"):
            try:
                return driver.find_element("css selector", selector)
            except TypeError:
                return driver.find_element(selector)
        raise RuntimeError("driver lacks query_selector() or find_element()")

    def _set_element_value(self, element: Any, text: str, clear: bool = True) -> None:
        if hasattr(element, "fill"):
            element.fill(text)
            return
        if clear and hasattr(element, "clear"):
            element.clear()
        if hasattr(element, "send_keys"):
            element.send_keys(text)
            return
        raise RuntimeError("element lacks fill() or send_keys()")

    def click_random(
        self,
        driver: Any,
        count: int = 10,
        selector: str = "a, button, input, [role='button']",
    ) -> None:
        """
        Click a random set of clickable elements.
        Expects driver.query_selector_all(selector) -> list of elements,
        and each element has a click() method.
        """
        if not hasattr(driver, "query_selector_all"):
            raise RuntimeError("driver lacks query_selector_all()")
        elements = driver.query_selector_all(selector)
        if not elements:
            self._record("click_random", "skipped", "no elements found")
            return
        for _ in range(min(count, len(elements))):
            element = self._rng.choice(elements)
            if hasattr(element, "click"):
                element.click()
        self._record("click_random", "ok", f"clicked {min(count, len(elements))}")

    def input_text(
        self,
        driver: Any,
        selector: str,
        text: str,
        clear: bool = True,
    ) -> None:
        """
        Fill a single input with the provided text.
        This is suitable for piping chat input into a target field.
        """
        element = self._find_element(driver, selector)
        if not element:
            self._record("input_text", "skipped", "no element found")
            return
        self._set_element_value(element, text, clear=clear)
        self._record("input_text", "ok", f"{selector} text_len={len(text)}")

    def input_value(
        self,
        driver: Any,
        selector: str,
        value: str,
        clear: bool = True,
    ) -> None:
        """
        Alias for input_text() with a more generic name.
        """
        self.input_text(driver, selector, value, clear=clear)

    def input_fuzzing(
        self,
        driver: Any,
        selector: str,
        payloads: Optional[Sequence[str]] = None,
        max_payloads: int = 10,
        clear: bool = True,
    ) -> None:
        """
        Feed benign edge-case strings into a single input for robustness testing.
        """
        benign_payloads = [
            "",
            " ",
            "a" * 1,
            "a" * 255,
            "A" * 1024,
            "0",
            "-1",
            "0000123",
            "3.14159",
            "true",
            "false",
            "null",
            "none",
            "test@example.com",
            "https://example.com/path?x=1&y=2",
            "line1\nline2\nline3",
            "tabs\tand\tspaces",
            "emoji🙂",
            "accented café",
        ]
        values = list(payloads) if payloads is not None else benign_payloads
        element = self._find_element(driver, selector)
        if not element:
            self._record("input_fuzzing", "skipped", "no element found")
            return
        for text in values[:max_payloads]:
            self._set_element_value(element, text, clear=clear)
        self._record("input_fuzzing", "ok", f"{selector} count={min(max_payloads, len(values))}")

    def open_new_tab(self, driver: Any, url: str) -> None:
        """
        Open a new tab and navigate to url.
        Expects driver.new_page() -> page (Playwright) or driver.open_new_tab(url).
        """
        if hasattr(driver, "open_new_tab"):
            driver.open_new_tab(url)
            self._record("open_new_tab", "ok", url)
            return
        if hasattr(driver, "new_page"):
            page = driver.new_page()
            if hasattr(page, "goto"):
                page.goto(url)
                self._record("open_new_tab", "ok", url)
                return
        raise RuntimeError("driver lacks open_new_tab() or new_page().goto()")

    def extract_links(self, driver: Any, selector: str = "a[href]") -> List[str]:
        """
        Extract href links from the current page.
        Expects driver.query_selector_all(selector) and element.get_attribute("href")
        or driver.execute_script to read attributes.
        """
        if not hasattr(driver, "query_selector_all"):
            raise RuntimeError("driver lacks query_selector_all()")
        elements = driver.query_selector_all(selector)
        links: List[str] = []
        for element in elements:
            href = None
            if hasattr(element, "get_attribute"):
                href = element.get_attribute("href")
            elif hasattr(driver, "execute_script"):
                href = driver.execute_script("return arguments[0].getAttribute('href');", element)
            if href:
                links.append(href)
        self._record("extract_links", "ok", f"found {len(links)} links")
        return links

    def remove_dom_nodes(self, driver: Any, selector: str) -> None:
        """
        Remove DOM nodes matching selector.
        Expects driver.execute_script(js) or driver.evaluate(js).
        """
        js = (
            "document.querySelectorAll(arguments[0])"
            ".forEach(el => el.remove());"
        )
        if hasattr(driver, "execute_script"):
            driver.execute_script(js, selector)
            self._record("remove_dom_nodes", "ok", selector)
            return
        if hasattr(driver, "evaluate"):
            driver.evaluate(js, selector)
            self._record("remove_dom_nodes", "ok", selector)
            return
        raise RuntimeError("driver lacks execute_script() or evaluate()")

    def simulate_network_issues(
        self,
        driver: Any,
        latency_ms: int = 500,
        throughput_kbps: int = 256,
        offline: bool = False,
    ) -> None:
        """
        Simulate network issues if supported by driver.
        Expects driver.set_network_conditions(...) or driver.route(...) for adapters.
        """
        if hasattr(driver, "set_network_conditions"):
            driver.set_network_conditions(
                offline=offline,
                latency=latency_ms,
                throughput=throughput_kbps * 1024,
            )
            self._record(
                "simulate_network_issues",
                "ok",
                f"latency={latency_ms}ms throughput={throughput_kbps}kbps offline={offline}",
            )
            return
        raise RuntimeError("driver lacks set_network_conditions()")

    def random_scroll(self, driver: Any, steps: int = 5) -> None:
        """
        Scroll randomly to shake layout and lazy loading.
        Expects driver.execute_script(js).
        """
        if not hasattr(driver, "execute_script"):
            raise RuntimeError("driver lacks execute_script()")
        for _ in range(steps):
            dy = self._rng.randint(200, 1200)
            driver.execute_script("window.scrollBy(0, arguments[0]);", dy)
        self._record("random_scroll", "ok", f"steps={steps}")

    def reload_page(self, driver: Any) -> None:
        """
        Reload the current page.
        Expects driver.reload() or driver.refresh().
        """
        if hasattr(driver, "reload"):
            driver.reload()
            self._record("reload_page", "ok", "reload()")
            return
        if hasattr(driver, "refresh"):
            driver.refresh()
            self._record("reload_page", "ok", "refresh()")
            return
        raise RuntimeError("driver lacks reload() or refresh()")

    def toggle_visibility(self, driver: Any, selector: str, hidden: bool = True) -> None:
        """
        Hide or show elements via inline style to test layout resilience.
        Expects driver.execute_script(js) or driver.evaluate(js).
        """
        js = (
            "document.querySelectorAll(arguments[0]).forEach(el => {"
            "  el.style.visibility = arguments[1] ? 'hidden' : 'visible';"
            "});"
        )
        if hasattr(driver, "execute_script"):
            driver.execute_script(js, selector, hidden)
            self._record("toggle_visibility", "ok", f"{selector} hidden={hidden}")
            return
        if hasattr(driver, "evaluate"):
            driver.evaluate(js, selector, hidden)
            self._record("toggle_visibility", "ok", f"{selector} hidden={hidden}")
            return
        raise RuntimeError("driver lacks execute_script() or evaluate()")

    def generate_report(self, path: Optional[str] = None) -> str:
        """
        Create a JSON report of actions. If path is provided, writes to file.
        Returns JSON string.
        """
        payload = {"actions": [r.__dict__ for r in self._results]}
        text = json.dumps(payload, indent=2, sort_keys=True)
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            self._record("generate_report", "ok", path)
        return text

    def run_scenario(
        self, steps: Iterable[Callable[[], None]], stop_on_error: bool = False
    ) -> None:
        """
        Run a list of step callables; record errors without crashing by default.
        """
        for step in steps:
            try:
                step()
            except Exception as exc:  # pylint: disable=broad-except
                self._record("scenario_step", "error", str(exc))
                if stop_on_error:
                    raise

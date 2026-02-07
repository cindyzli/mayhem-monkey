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

    def resize_viewport(
        self,
        driver: Any,
        widths: Optional[Sequence[int]] = None,
        heights: Optional[Sequence[int]] = None,
    ) -> None:
        """
        Randomly resize the viewport to test responsive design breakpoints.
        Expects driver.set_viewport_size(w, h) or driver.set_window_size(w, h).
        """
        default_widths = [320, 375, 414, 768, 1024, 1280, 1440, 1920]
        default_heights = [480, 568, 667, 812, 900, 1024, 1080]
        w = self._rng.choice(widths or default_widths)
        h = self._rng.choice(heights or default_heights)
        if hasattr(driver, "set_viewport_size"):
            driver.set_viewport_size({"width": w, "height": h})
        elif hasattr(driver, "set_window_size"):
            driver.set_window_size(w, h)
        else:
            raise RuntimeError("driver lacks set_viewport_size() or set_window_size()")
        self._record("resize_viewport", "ok", f"{w}x{h}")

    def clear_storage(self, driver: Any) -> None:
        """
        Clear localStorage, sessionStorage, and cookies to test state recovery.
        Expects driver.execute_script(js) or driver.evaluate(js).
        """
        js = (
            "try { localStorage.clear(); } catch(e) {}"
            "try { sessionStorage.clear(); } catch(e) {}"
        )
        if hasattr(driver, "execute_script"):
            driver.execute_script(js)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        if hasattr(driver, "delete_all_cookies"):
            driver.delete_all_cookies()
        elif hasattr(driver, "context") and hasattr(driver.context, "clear_cookies"):
            driver.context.clear_cookies()
        self._record("clear_storage", "ok", "localStorage + sessionStorage + cookies")

    def rapid_click(
        self, driver: Any, selector: str, count: int = 20
    ) -> None:
        """
        Click the same element rapidly to test debounce/throttle handling.
        """
        element = self._find_element(driver, selector)
        if not element:
            self._record("rapid_click", "skipped", "no element found")
            return
        for _ in range(count):
            if hasattr(element, "click"):
                element.click()
        self._record("rapid_click", "ok", f"{selector} count={count}")

    def fill_all_inputs(
        self,
        driver: Any,
        selector: str = "input, textarea, select",
    ) -> None:
        """
        Fill every visible input/textarea with random data and select random
        options in dropdowns to stress-test form handling.
        """
        if not hasattr(driver, "query_selector_all"):
            raise RuntimeError("driver lacks query_selector_all()")
        elements = driver.query_selector_all(selector)
        filled = 0
        for el in elements:
            tag = None
            if hasattr(el, "evaluate"):
                tag = el.evaluate("e => e.tagName.toLowerCase()")
            elif hasattr(el, "tag_name"):
                tag = el.tag_name.lower()
            if tag == "select":
                js = (
                    "var opts = arguments[0].options;"
                    "if(opts.length > 1) arguments[0].selectedIndex = "
                    "Math.floor(Math.random() * opts.length);"
                )
                if hasattr(driver, "execute_script"):
                    driver.execute_script(js, el)
                    filled += 1
            else:
                text = "chaos_" + str(self._rng.randint(0, 99999))
                try:
                    self._set_element_value(el, text)
                    filled += 1
                except RuntimeError:
                    pass
        self._record("fill_all_inputs", "ok", f"filled {filled}/{len(elements)}")

    def disable_css(self, driver: Any) -> None:
        """
        Strip all stylesheets and inline styles to test content accessibility
        and structural resilience without CSS.
        """
        js = (
            "document.querySelectorAll('link[rel=stylesheet], style')"
            ".forEach(el => el.remove());"
            "document.querySelectorAll('[style]')"
            ".forEach(el => el.removeAttribute('style'));"
        )
        if hasattr(driver, "execute_script"):
            driver.execute_script(js)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("disable_css", "ok", "removed all stylesheets and inline styles")

    def mutate_text(
        self, driver: Any, probability: float = 0.3, max_nodes: int = 50
    ) -> None:
        """
        Randomly scramble visible text content to test UI resilience to
        unexpected content changes (e.g. bad translations, corrupted data).
        """
        js = """
        (function(prob, maxN) {
            var walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, null, false
            );
            var nodes = [], n;
            while ((n = walker.nextNode()) && nodes.length < maxN) {
                if (n.textContent.trim()) nodes.push(n);
            }
            var mutated = 0;
            nodes.forEach(function(node) {
                if (Math.random() < prob) {
                    node.textContent = node.textContent.split('').sort(
                        function() { return 0.5 - Math.random(); }
                    ).join('');
                    mutated++;
                }
            });
            return mutated;
        })(arguments[0], arguments[1]);
        """
        if hasattr(driver, "execute_script"):
            count = driver.execute_script(js, probability, max_nodes)
        elif hasattr(driver, "evaluate"):
            count = driver.evaluate(js, probability, max_nodes)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("mutate_text", "ok", f"mutated {count} text nodes")

    def back_forward_navigation(self, driver: Any, cycles: int = 5) -> None:
        """
        Rapidly navigate back and forward to stress-test history state handling.
        Expects driver.back() and driver.forward() or driver.go_back()/go_forward().
        """
        for _ in range(cycles):
            if hasattr(driver, "back"):
                driver.back()
            elif hasattr(driver, "go_back"):
                driver.go_back()
            else:
                raise RuntimeError("driver lacks back() or go_back()")
            if hasattr(driver, "forward"):
                driver.forward()
            elif hasattr(driver, "go_forward"):
                driver.go_forward()
            else:
                raise RuntimeError("driver lacks forward() or go_forward()")
        self._record("back_forward_navigation", "ok", f"cycles={cycles}")

    def zoom_page(self, driver: Any, level: Optional[float] = None) -> None:
        """
        Change page zoom level to test layout at non-default zoom.
        Level is a float (e.g. 0.5 = 50%, 2.0 = 200%).
        """
        if level is None:
            level = self._rng.choice([0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0])
        js = f"document.body.style.zoom = '{level}';"
        if hasattr(driver, "execute_script"):
            driver.execute_script(js)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("zoom_page", "ok", f"zoom={level}")

    def focus_blur_cycle(
        self,
        driver: Any,
        selector: str = "input, textarea, button, a, select",
        cycles: int = 3,
    ) -> None:
        """
        Rapidly focus and blur interactive elements to test focus-related
        event handlers and validation triggers.
        """
        if not hasattr(driver, "query_selector_all"):
            raise RuntimeError("driver lacks query_selector_all()")
        elements = driver.query_selector_all(selector)
        if not elements:
            self._record("focus_blur_cycle", "skipped", "no elements found")
            return
        count = 0
        for el in elements:
            for _ in range(cycles):
                if hasattr(el, "focus"):
                    el.focus()
                if hasattr(el, "blur"):
                    el.blur()
                count += 1
        self._record("focus_blur_cycle", "ok", f"elements={len(elements)} cycles={cycles}")

    def random_form_submit(self, driver: Any) -> None:
        """
        Find all forms and submit one at random to test server-side validation
        and error handling with potentially incomplete data.
        """
        if not hasattr(driver, "query_selector_all"):
            raise RuntimeError("driver lacks query_selector_all()")
        forms = driver.query_selector_all("form")
        if not forms:
            self._record("random_form_submit", "skipped", "no forms found")
            return
        form = self._rng.choice(forms)
        js = "arguments[0].requestSubmit ? arguments[0].requestSubmit() : arguments[0].submit();"
        if hasattr(driver, "execute_script"):
            driver.execute_script(js, form)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js, form)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("random_form_submit", "ok", f"submitted 1 of {len(forms)} forms")

    def trigger_resize_events(self, driver: Any, count: int = 10) -> None:
        """
        Fire rapid window resize events to stress-test resize listeners,
        debounce logic, and responsive layout recalculations.
        """
        js = """
        (function(n) {
            for (var i = 0; i < n; i++) {
                window.dispatchEvent(new Event('resize'));
            }
        })(arguments[0]);
        """
        if hasattr(driver, "execute_script"):
            driver.execute_script(js, count)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js, count)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("trigger_resize_events", "ok", f"count={count}")

    def inject_console_monitor(self, driver: Any) -> None:
        """
        Inject a script that captures console.error and console.warn calls
        into a global array for later retrieval and analysis.
        """
        js = """
        if (!window.__chaosConsoleLog) {
            window.__chaosConsoleLog = [];
            var origError = console.error;
            var origWarn = console.warn;
            console.error = function() {
                window.__chaosConsoleLog.push({
                    level: 'error',
                    args: Array.from(arguments).map(String),
                    ts: Date.now()
                });
                origError.apply(console, arguments);
            };
            console.warn = function() {
                window.__chaosConsoleLog.push({
                    level: 'warn',
                    args: Array.from(arguments).map(String),
                    ts: Date.now()
                });
                origWarn.apply(console, arguments);
            };
        }
        """
        if hasattr(driver, "execute_script"):
            driver.execute_script(js)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("inject_console_monitor", "ok", "monitoring console.error + console.warn")

    def collect_console_errors(self, driver: Any) -> List[dict]:
        """
        Retrieve captured console errors/warnings from inject_console_monitor().
        Returns list of {level, args, ts} dicts.
        """
        js = "return window.__chaosConsoleLog || [];"
        if hasattr(driver, "execute_script"):
            logs = driver.execute_script(js)
        elif hasattr(driver, "evaluate"):
            logs = driver.evaluate("window.__chaosConsoleLog || []")
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("collect_console_errors", "ok", f"collected {len(logs)} entries")
        return logs

    def scramble_element_order(self, driver: Any, selector: str) -> None:
        """
        Randomly reorder child elements of a container to test whether the
        UI handles unexpected DOM ordering (e.g. list items, table rows).
        """
        js = """
        var parent = document.querySelector(arguments[0]);
        if (parent) {
            var children = Array.from(parent.children);
            for (var i = children.length - 1; i > 0; i--) {
                var j = Math.floor(Math.random() * (i + 1));
                parent.appendChild(children[j]);
                children.splice(j, 1);
            }
        }
        """
        if hasattr(driver, "execute_script"):
            driver.execute_script(js, selector)
        elif hasattr(driver, "evaluate"):
            driver.evaluate(js, selector)
        else:
            raise RuntimeError("driver lacks execute_script() or evaluate()")
        self._record("scramble_element_order", "ok", selector)

    def simulate_slow_resources(self, driver: Any, delay_ms: int = 3000) -> None:
        """
        Intercept image and script loads to simulate slow resource loading.
        Expects Playwright-style driver.route() for request interception.
        """
        if not hasattr(driver, "route"):
            raise RuntimeError("driver lacks route() — requires Playwright-style API")

        def slow_handler(route: Any) -> None:
            import time
            time.sleep(delay_ms / 1000)
            route.continue_()

        driver.route("**/*.{png,jpg,jpeg,gif,svg,js,css}", slow_handler)
        self._record("simulate_slow_resources", "ok", f"delay={delay_ms}ms on assets")

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

from __future__ import annotations

from typing import Any, List, Optional


class PlaywrightAdapter:
    def __init__(self, page: Any, context: Optional[Any] = None) -> None:
        self._page = page
        self._context = context

    def set_page(self, page: Any) -> None:
        self._page = page

    def query_selector_all(self, selector: str) -> List[Any]:
        return self._page.query_selector_all(selector)

    def query_selector(self, selector: str) -> Any:
        return self._page.query_selector(selector)

    def execute_script(self, script: str, *args: Any) -> Any:
        return self._page.evaluate(script, *args)

    def refresh(self) -> None:
        self._page.reload()

    def open_new_tab(self, url: str) -> None:
        if not self._context:
            raise RuntimeError("Playwright context is not set")
        new_page = self._context.new_page()
        new_page.goto(url)
        self._page = new_page

    def quit(self) -> None:
        try:
            self._page.close()
        except Exception:
            pass

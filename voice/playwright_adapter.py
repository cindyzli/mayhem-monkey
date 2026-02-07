from __future__ import annotations

import asyncio
from typing import Any, List, Optional


class _ElementWrapper:
    def __init__(self, handle: Any, runner) -> None:
        self._handle = handle
        self._runner = runner

    def click(self) -> None:
        self._runner(self._handle.click())

    def fill(self, text: str) -> None:
        self._runner(self._handle.fill(text))

    def get_attribute(self, name: str) -> Optional[str]:
        return self._runner(self._handle.get_attribute(name))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handle, name)


class PlaywrightAdapter:
    def __init__(
        self,
        page: Any,
        context: Optional[Any] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        if loop is None:
            raise RuntimeError("PlaywrightAdapter requires a target event loop")
        self._page = page
        self._context = context
        self._loop = loop

    def set_page(self, page: Any) -> None:
        self._page = page

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def _wrap(self, handle: Any) -> _ElementWrapper:
        return _ElementWrapper(handle, self._run)

    def query_selector_all(self, selector: str) -> List[Any]:
        handles = self._run(self._page.query_selector_all(selector))
        return [self._wrap(handle) for handle in handles]

    def query_selector(self, selector: str) -> Any:
        handle = self._run(self._page.query_selector(selector))
        return self._wrap(handle) if handle is not None else None

    def execute_script(self, script: str, *args: Any) -> Any:
        unwrapped = [
            arg._handle if isinstance(arg, _ElementWrapper) else arg
            for arg in args
        ]
        return self._run(self._page.evaluate(script, *unwrapped))

    def refresh(self) -> None:
        self._run(self._page.reload())

    def open_new_tab(self, url: str) -> None:
        if not self._context:
            raise RuntimeError("Playwright context is not set")
        new_page = self._run(self._context.new_page())
        self._run(new_page.goto(url))
        self._page = new_page

    def quit(self) -> None:
        try:
            self._run(self._page.close())
        except Exception:
            pass

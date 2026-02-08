import asyncio
import threading
from typing import Optional, Tuple

from playwright.async_api import async_playwright

from voice.playwright_adapter import PlaywrightAdapter


class PlaywrightVoiceDriver:
    def __init__(self, headless: bool, start_url: Optional[str]) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._playwright = None
        self._browser = None
        self._context = None
        self.adapter = self._run_coroutine(self._init(headless, start_url))

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_coroutine(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _init(self, headless: bool, start_url: Optional[str]) -> PlaywrightAdapter:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context()
        page = await self._context.new_page()
        if start_url:
            await page.goto(start_url)
        return PlaywrightAdapter(page=page, context=self._context, loop=self._loop)

    def stop(self) -> None:
        async def _shutdown() -> None:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()

        try:
            self._run_coroutine(_shutdown())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=2)

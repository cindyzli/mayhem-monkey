from __future__ import annotations

from typing import Any, List


class SeleniumAdapter:
    def __init__(self, driver: Any) -> None:
        self._driver = driver

    def query_selector_all(self, selector: str) -> List[Any]:
        from selenium.webdriver.common.by import By

        return self._driver.find_elements(By.CSS_SELECTOR, selector)

    def query_selector(self, selector: str) -> Any:
        from selenium.webdriver.common.by import By

        return self._driver.find_element(By.CSS_SELECTOR, selector)

    def execute_script(self, script: str, *args: Any) -> Any:
        return self._driver.execute_script(script, *args)

    def refresh(self) -> None:
        self._driver.refresh()

    def open_new_tab(self, url: str) -> None:
        try:
            self._driver.switch_to.new_window("tab")
        except Exception:
            self._driver.execute_script("window.open('about:blank','_blank');")
            self._driver.switch_to.window(self._driver.window_handles[-1])
        self._driver.get(url)

    def quit(self) -> None:
        self._driver.quit()

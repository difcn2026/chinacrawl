"""Unified Parser Layer — Selector with adaptive relocation.

对标 Scrapling Selector.adaptive=True：当 CSS/XPath 找不到目标元素时，
自动回退到 adaptive.py 的 AdaptiveFinder 重新定位。

XHLS v3.3 | Worker C — chinacrawl/parser.py
"""

from lxml import html as lhtml
from lxml.html import HtmlElement
from typing import List, Optional, Union


class SelectorList:
    """List of selected elements with chainable query methods.

    Supports iteration, len(), .text, .get(), and chained .css() / .xpath().
    """

    def __init__(self, elements: List[HtmlElement]):
        self._elements: List[HtmlElement] = elements

    # --- Container protocol ---

    def __iter__(self):
        return iter(self._elements)

    def __len__(self) -> int:
        return len(self._elements)

    def __bool__(self) -> bool:
        return len(self._elements) > 0

    def __getitem__(self, index: int) -> "SelectorList":
        """Single-element slice returns a new SelectorList for chaining."""
        el = self._elements[index]
        return SelectorList([el])

    # --- Value access ---

    @property
    def text(self) -> str:
        """Text content of first element, stripped."""
        if not self._elements:
            return ""
        return (self._elements[0].text_content() or "").strip()

    def get(self, attr: str = None) -> Optional[str]:
        """Get attribute value (or text content if attr is None) of first element."""
        if not self._elements:
            return None
        if attr is None:
            return (self._elements[0].text_content() or "").strip()
        return self._elements[0].get(attr)

    # --- Chained queries on selected elements ---

    def css(self, selector: str) -> "SelectorList":
        """Run a CSS query scoped to every element in this list, union results."""
        results: List[HtmlElement] = []
        for el in self._elements:
            results.extend(el.cssselect(selector))
        return SelectorList(results)

    def xpath(self, xpath_expr: str) -> "SelectorList":
        """Run an XPath query scoped to every element in this list, union results."""
        results: List[HtmlElement] = []
        for el in self._elements:
            results.extend(el.xpath(xpath_expr))
        return SelectorList(results)

    # --- Helpers ---

    def getall(self) -> List[HtmlElement]:
        """Return raw list of lxml elements."""
        return self._elements


class Selector:
    """Unified HTML selector with optional adaptive relocation.

    Usage::

        sel = Selector(html_text, url="https://example.com")
        items = sel.css(".price", adaptive=True)   # falls back to adaptive.py
        print(items.text)                           # first match text
        print(items.get("data-id"))                 # first match attribute
    """

    def __init__(self, html_text: str, url: str = ""):
        self.html: str = html_text
        self.url: str = url
        self._tree = lhtml.fromstring(html_text) if html_text else None

    # --- Primary query methods ---

    def css(
        self,
        selector: str,
        adaptive: bool = False,
        auto_save: bool = False,
    ) -> SelectorList:
        """CSS selector query.

        :param selector:  CSS selector string.
        :param adaptive:  If True and no elements found, call adaptive.py to relocate.
        :param auto_save: Reserved for future auto-save integration (ignored for now).
        :return: SelectorList of matched elements.
        """
        if self._tree is None:
            return SelectorList([])

        elements: List[HtmlElement] = self._tree.cssselect(selector)
        if not elements and adaptive:
            elements = self._adaptive_relocate(selector)
        return SelectorList(elements)

    def xpath(self, xpath_expr: str) -> SelectorList:
        """XPath query. Returns a SelectorList."""
        if self._tree is None:
            return SelectorList([])
        elements: List[HtmlElement] = self._tree.xpath(xpath_expr)
        return SelectorList(elements)

    # --- Adaptive fallback ---

    def _adaptive_relocate(self, selector: str) -> List[HtmlElement]:
        """Fallback: use adaptive.py to find elements after page structure changes.

        Returns a single-element list (matching adaptive.find's signature)
        or an empty list on failure.
        """
        try:
            from .adaptive import get_finder   # type: ignore[import-untyped]

            finder = get_finder()
            found: Optional[HtmlElement] = finder.find(
                self.html,
                selector,
                url=self.url,
            )
            if found is not None:
                return [found]
        except Exception:
            pass
        return []

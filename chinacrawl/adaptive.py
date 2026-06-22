"""Adaptive Element Finder - Auto-relocates elements when pages change.

Inspired by Scrapling's adaptive engine. Uses text/structure similarity
to re-locate target elements after website DOM updates, with SQLite-based
cross-session memory.

XHLS v3.3 | Xiao Hei Learning System
Layer L4: Adaptive Engine
"""

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from lxml import etree
from lxml.html import HtmlElement, fromstring, tostring

# --- Database path ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adaptive_store.db")

# --- Data Classes ---


@dataclass
class ElementSignature:
    """Compact fingerprint of a DOM element for similarity matching."""

    tag: str = ""
    text: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)
    path: str = ""  # CSS path from root
    nth_child: int = 0
    depth: int = 0
    parent_tag: str = ""

    @classmethod
    def from_element(cls, el: HtmlElement) -> "ElementSignature":
        """Extract signature from an lxml HtmlElement."""
        text = "".join(el.itertext()).strip()[:500]
        attrs = dict(el.attrib)
        # Remove noise attributes
        for noisy in ("style", "data-v-", "data-src", "onclick", "onmouseover"):
            attrs = {k: v for k, v in attrs.items() if not k.startswith(noisy)}

        # Build CSS path
        path_parts = []
        current = el
        while current is not None and current.tag is not etree.Comment:
            tag = current.tag if isinstance(current.tag, str) else "unknown"
            nth = cls._nth_of_type(current)
            path_parts.append(f"{tag}:nth-child({nth})")
            current = current.getparent()
        path_parts.reverse()

        parent = el.getparent()
        parent_tag = parent.tag if parent is not None and isinstance(parent.tag, str) else ""

        return cls(
            tag=el.tag if isinstance(el.tag, str) else "unknown",
            text=text,
            attrs=attrs,
            path=" > ".join(path_parts),
            nth_child=cls._nth_of_type(el),
            depth=len(path_parts),
            parent_tag=parent_tag,
        )

    @staticmethod
    def _nth_of_type(el: HtmlElement) -> int:
        """Return 1-based nth-child among same-tag siblings."""
        parent = el.getparent()
        if parent is None:
            return 1
        count = 0
        for child in parent:
            if child.tag == el.tag:
                count += 1
            if child is el:
                return count
        return 1

    def similarity_to(self, other: "ElementSignature") -> float:
        """Calculate similarity score (0.0 to 1.0) between two signatures."""
        score = 0.0

        # Tag match: 0.25
        if self.tag == other.tag:
            score += 0.25

        # Text similarity: 0.35
        if self.text and other.text:
            text_sim = SequenceMatcher(None, self.text, other.text).ratio()
            score += 0.35 * text_sim
            # Penalty: if both have text but no match, cap below threshold
            if text_sim < 0.1:
                return min(score, 0.40)  # force below default threshold
        elif self.text == other.text:
            score += 0.35

        # Attribute overlap: 0.20
        common_keys = set(self.attrs.keys()) & set(other.attrs.keys())
        if common_keys:
            attr_score = 0.0
            for key in common_keys:
                if self.attrs[key] == other.attrs[key]:
                    attr_score += 1.0
            attr_score /= max(len(common_keys), 1)
            score += 0.20 * attr_score
        elif not self.attrs and not other.attrs:
            score += 0.20

        # Structural similarity (depth + parent): 0.20
        depth_diff = abs(self.depth - other.depth)
        if depth_diff <= 1:
            score += 0.10
        elif depth_diff <= 3:
            score += 0.05
        if self.parent_tag == other.parent_tag:
            score += 0.10

        return min(score, 1.0)


@dataclass
class SelectorRecord:
    """Stored selector reference for adaptive re-finding."""

    url: str
    selector: str
    selector_type: str  # "css" or "xpath"
    signature: ElementSignature
    page_hash: str
    updated_at: str = ""


# --- SQLite Storage ---


class AdaptiveStore:
    """Thread-safe SQLite storage for selector records."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS selector_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                selector TEXT NOT NULL,
                selector_type TEXT NOT NULL DEFAULT 'css',
                url TEXT NOT NULL,
                signature_json TEXT NOT NULL,
                page_hash TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                hit_count INTEGER DEFAULT 1,
                UNIQUE(domain, selector)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_domain ON selector_records(domain)
            """
        )
        conn.commit()

    def save(self, record: SelectorRecord):
        domain = urlparse(record.url).netloc
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO selector_records (domain, selector, selector_type, url, signature_json, page_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(domain, selector) DO UPDATE SET
                signature_json = excluded.signature_json,
                page_hash = excluded.page_hash,
                url = excluded.url,
                updated_at = datetime('now'),
                hit_count = hit_count + 1
            """,
            (
                domain,
                record.selector,
                record.selector_type,
                record.url,
                json.dumps(record.signature.__dict__, ensure_ascii=False),
                record.page_hash,
            ),
        )
        conn.commit()

    def load(self, domain: str, selector: str) -> Optional[SelectorRecord]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT url, selector, selector_type, signature_json, page_hash, updated_at "
            "FROM selector_records WHERE domain = ? AND selector = ?",
            (domain, selector),
        ).fetchone()
        if row is None:
            return None
        sig_data = json.loads(row[3])
        sig = ElementSignature(**sig_data)
        return SelectorRecord(
            url=row[0],
            selector=row[1],
            selector_type=row[2],
            signature=sig,
            page_hash=row[4],
            updated_at=row[5],
        )

    def load_all_for_domain(self, domain: str) -> List[SelectorRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT url, selector, selector_type, signature_json, page_hash, updated_at "
            "FROM selector_records WHERE domain = ? ORDER BY updated_at DESC",
            (domain,),
        ).fetchall()
        records = []
        for row in rows:
            sig_data = json.loads(row[3])
            sig = ElementSignature(**sig_data)
            records.append(
                SelectorRecord(
                    url=row[0],
                    selector=row[1],
                    selector_type=row[2],
                    signature=sig,
                    page_hash=row[4],
                    updated_at=row[5],
                )
            )
        return records

    def delete(self, domain: str, selector: str):
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM selector_records WHERE domain = ? AND selector = ?",
            (domain, selector),
        )
        conn.commit()


# --- Adaptive Finder ---


class AdaptiveFinder:
    """Auto-relocates DOM elements when web pages change structure.

    Usage:
        finder = AdaptiveFinder()
        html = fetch_page("https://example.com/products")

        # First time: learn the element
        el = finder.find(html, ".product-price", url="https://example.com/products")

        # Later, after site redesign: auto re-locate
        new_html = fetch_page("https://example.com/products")
        el = finder.refind(new_html)  # uses stored signature to re-locate
    """

    def __init__(self, store: Optional[AdaptiveStore] = None, threshold: float = 0.55):
        """
        :param store: AdaptiveStore instance (creates default if None)
        :param threshold: Minimum similarity score to consider a match (0.0-1.0)
        """
        self.store = store or AdaptiveStore()
        self.threshold = threshold
        self._last_record: Optional[SelectorRecord] = None
        self._last_url: str = ""
        self._last_selector: str = ""

    def _page_hash(self, html: str) -> str:
        """Structural hash of the page (ignores dynamic content)."""
        try:
            tree = fromstring(html)
            # Hash based on tag structure, not text content
            structure = self._extract_structure(tree)
            return hashlib.sha256(structure.encode()).hexdigest()[:16]
        except Exception:
            return hashlib.sha256(html.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_structure(el: HtmlElement, depth: int = 0) -> str:
        """Build a structural fingerprint: tag names + class ids in tree order."""
        if not isinstance(el.tag, str):
            return ""
        class_id = ""
        if "id" in el.attrib:
            class_id = f"#{el.attrib['id']}"
        elif "class" in el.attrib:
            cls = el.attrib["class"].split()[0] if el.attrib["class"] else ""
            class_id = f".{cls}" if cls else ""
        parts = [f"{'  ' * depth}<{el.tag}{class_id}>"]
        for child in el:
            parts.append(AdaptiveFinder._extract_structure(child, depth + 1))
        return "\n".join(parts)

    def find(
        self,
        html: str,
        selector: str,
        url: str = "",
        selector_type: str = "css",
    ) -> Optional[HtmlElement]:
        """Find element by selector and record its signature for future re-finding.

        :param html: Raw HTML string
        :param selector: CSS or XPath selector
        :param url: Source URL (for domain-based lookup)
        :param selector_type: "css" or "xpath"
        :return: Found element, or None
        """
        try:
            tree = fromstring(html)
        except Exception:
            return None

        elements = self._query(tree, selector, selector_type)
        if elements is None or len(elements) == 0:
            return None

        el = elements[0]
        sig = ElementSignature.from_element(el)
        page_hash = self._page_hash(html)

        record = SelectorRecord(
            url=url,
            selector=selector,
            selector_type=selector_type,
            signature=sig,
            page_hash=page_hash,
        )

        self.store.save(record)
        self._last_record = record
        self._last_url = url
        self._last_selector = selector

        return el

    def refind(
        self,
        html: str,
        url: str = "",
        selector: Optional[str] = None,
        selector_type: Optional[str] = None,
    ) -> Optional[HtmlElement]:
        """Re-locate a previously-recorded element in potentially changed HTML.

        Strategy (in order):
        1. Try the original selector directly
        2. Try the recorded signature against all elements on the page
        3. Try fuzzy CSS path matching
        4. Try text content matching

        :param html: Raw HTML string (possibly changed)
        :param url: Source URL (uses last_url if empty)
        :param selector: Override selector (uses last_selector if empty)
        :param selector_type: Override selector type
        :return: Re-located element, or None
        """
        url = url or self._last_url
        selector = selector or self._last_selector
        selector_type = selector_type or (self._last_record.selector_type if self._last_record else "css")
        domain = urlparse(url).netloc

        # Load record from store
        record = self._last_record
        if record is None:
            record = self.store.load(domain, selector)
        if record is None:
            # First time, fall back to normal find
            return self.find(html, selector, url, selector_type)

        try:
            tree = fromstring(html)
        except Exception:
            return None

        # Strategy 1: Direct selector match
        elements = self._query(tree, selector, selector_type)
        if elements and len(elements) > 0:
            return elements[0]

        # Strategy 2: Signature similarity against all elements
        best_el, best_score = self._similarity_scan(tree, record.signature)
        if best_el is not None and best_score >= self.threshold:
            return best_el

        # Strategy 3: Fuzzy CSS path (verify text before returning)
        sig_path = record.signature.path
        path_parts = sig_path.split(" > ")
        if len(path_parts) > 3:
            for trim in range(1, min(3, len(path_parts) - 1)):
                fuzzy = " > ".join(path_parts[trim:])
                try:
                    els = tree.cssselect(fuzzy)
                    for el in els:
                        el_text = "".join(el.itertext()).strip()
                        if el_text and record.signature.text:
                            from difflib import SequenceMatcher
                            if SequenceMatcher(None, el_text, record.signature.text).ratio() > 0.3:
                                return el
                except Exception:
                    continue

        # Strategy 4: Text content search
        if record.signature.text and len(record.signature.text) > 10:
            keywords = record.signature.text.split()[:5]
            for el in tree.iter():
                if not isinstance(el.tag, str):
                    continue
                el_text = "".join(el.itertext()).strip()
                if all(kw in el_text for kw in keywords):
                    return el

        return None

    def refind_all(
        self,
        html: str,
        url: str = "",
        selector: Optional[str] = None,
        selector_type: Optional[str] = None,
    ) -> List[HtmlElement]:
        """Re-locate ALL matching elements (for list pages)."""
        url = url or self._last_url
        selector = selector or self._last_selector
        selector_type = selector_type or (self._last_record.selector_type if self._last_record else "css")
        domain = urlparse(url).netloc

        record = self._last_record or self.store.load(domain, selector)
        if record is None:
            return []

        try:
            tree = fromstring(html)
        except Exception:
            return []

        # Strategy 1: Direct selector
        elements = self._query(tree, selector, selector_type)
        if elements and len(elements) > 0:
            return elements

        # Strategy 2: Scan all with signature
        results = []
        target_sig = record.signature
        for el in tree.iter():
            if not isinstance(el.tag, str):
                continue
            sig = ElementSignature.from_element(el)
            if sig.similarity_to(target_sig) >= self.threshold:
                results.append(el)
        return results

    def _query(
        self, tree: HtmlElement, selector: str, selector_type: str
    ) -> Optional[List[HtmlElement]]:
        """Execute a CSS or XPath query on the tree."""
        try:
            if selector_type == "css":
                return tree.cssselect(selector)
            elif selector_type == "xpath":
                return tree.xpath(selector)
        except Exception:
            pass
        return None

    def _similarity_scan(
        self, tree: HtmlElement, target_sig: ElementSignature
    ) -> Tuple[Optional[HtmlElement], float]:
        """Scan all elements and find the best similarity match."""
        best_el = None
        best_score = 0.0

        for el in tree.iter():
            if not isinstance(el.tag, str):
                continue
            sig = ElementSignature.from_element(el)
            score = sig.similarity_to(target_sig)
            if score > best_score:
                best_score = score
                best_el = el

        return best_el, best_score

    def learn_page(self, html: str, url: str, selectors: Dict[str, str]) -> Dict[str, bool]:
        """Batch-learn multiple selectors for a page.

        :param html: Raw HTML
        :param url: Source URL
        :param selectors: {name: css_selector} mapping
        :return: {name: success} mapping
        """
        results = {}
        for name, sel in selectors.items():
            el = self.find(html, sel, url, "css")
            results[name] = el is not None
        return results

    def refind_page(self, html: str, url: str, names: List[str]) -> Dict[str, Optional[HtmlElement]]:
        """Batch re-find previously learned selectors.

        :param html: New HTML
        :param url: Source URL
        :param names: List of selector names to re-find
        :return: {name: element_or_None}
        """
        domain = urlparse(url).netloc
        results = {}
        records = self.store.load_all_for_domain(domain)
        record_map = {r.selector: r for r in records}

        for name in names:
            if name not in record_map:
                results[name] = None
                continue
            record = record_map[name]
            try:
                tree = fromstring(html)
            except Exception:
                results[name] = None
                continue

            # Try direct
            els = self._query(tree, name, record.selector_type)
            if els and len(els) > 0:
                results[name] = els[0]
                continue

            # Try signature
            best_el, best_score = self._similarity_scan(tree, record.signature)
            if best_el is not None and best_score >= self.threshold:
                results[name] = best_el
            else:
                results[name] = None

        return results


# --- Convenience: Global singleton ---

_global_finder: Optional[AdaptiveFinder] = None


def get_finder(threshold: float = 0.55) -> AdaptiveFinder:
    """Get or create the global AdaptiveFinder singleton."""
    global _global_finder
    if _global_finder is None:
        _global_finder = AdaptiveFinder(threshold=threshold)
    return _global_finder

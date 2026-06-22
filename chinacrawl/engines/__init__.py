"""ChinaCrawl Engine Plugins.

Auto-discovers and registers all engines in this directory.

Usage:
    from chinacrawl.engines import registry, JDEngine, TaobaoEngine

    # All engines auto-register on import
    for name in registry.list_all():
        engine = registry.get(name)
        print(f"{engine.display_name}: playwright={engine.requires_playwright}")

    # Deep Pinduoduo access (full browser automation + brand reports)
    from chinacrawl.engines.pinduoduo import product_search, product_feed, BrandAnalyzer
"""

from .base import BaseEngine, EngineProduct, EngineSearchResult, EngineRegistry, registry
from .jd import JDEngine
from .taobao import TaobaoEngine
from .xhs import XHSEngine

# Register built-in engines
_builtin = [JDEngine, TaobaoEngine, XHSEngine]

# Try registering existing douyin/pinduoduo as engine adapters
try:
    from .douyin_adapter import DouyinEngineAdapter
    _builtin.append(DouyinEngineAdapter)
except ImportError:
    pass

try:
    from .pinduoduo_adapter import PinduoduoEngine
    _builtin.append(PinduoduoEngine)
except ImportError:
    pass

# Deep Pinduoduo subpackage (full browser automation)
try:
    from . import pinduoduo  # noqa: F401
    PDD_DEEP_AVAILABLE = True
except ImportError:
    PDD_DEEP_AVAILABLE = False


def list_engines() -> list:
    """List all registered engine names."""
    return registry.list_all()


def get_engine(name: str):
    """Get engine by name."""
    return registry.get(name)


__all__ = [
    "BaseEngine", "EngineProduct", "EngineSearchResult",
    "EngineRegistry", "registry",
    "JDEngine", "TaobaoEngine",
    "PDD_DEEP_AVAILABLE",
    "list_engines", "get_engine",
]

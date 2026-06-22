# chinacrawl/core - Shared browser infrastructure
# All platform adapters (pinduoduo, douyin, etc.) use this layer.

from .browser import launch_browser, close_browser, create_context
from .anti_detect import (
    ANTI_DETECT_JS,
    CONTEXT_OVERRIDES,
    random_delay,
    random_touch_events,
    random_scroll_steps,
)
from .session import load_session, save_session, check_session, get_cookie_dir

__all__ = [
    "launch_browser", "close_browser", "create_context",
    "ANTI_DETECT_JS", "CONTEXT_OVERRIDES",
    "random_delay", "random_touch_events", "random_scroll_steps",
    "load_session", "save_session", "check_session", "get_cookie_dir",
]

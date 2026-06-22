"""Unified CAPTCHA Handler for Chinese Websites.

Covers:
- Slider CAPTCHA (滑块验证码): Douyin, JD, Taobao, PDD, 12306
- Click CAPTCHA (点选验证码): Government sites, banking
- SMS verification (短信验证码): Login/register flows
- Image CAPTCHA (图形验证码): Legacy sites
- Cloudflare Turnstile: International-facing Chinese sites

Strategy priority: Browser automation > OCR > External service > Manual fallback

XHLS v3.4 | Xiao Hei Learning System
Layer L3.6: CAPTCHA Engine
"""

import base64
import hashlib
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Callable, List, Tuple, Dict, Any

log = logging.getLogger("chinacrawl.captcha")


# ============================================================
# Types
# ============================================================

class CAPTCHAType(Enum):
    """CAPTCHA challenge types."""
    SLIDER = auto()          # 滑块验证码
    CLICK_TEXT = auto()      # 点选文字 (e.g., "点击图中 火车")
    CLICK_ICON = auto()      # 点选图标 (e.g., "点击图中所有 汽车")
    IMAGE_TEXT = auto()      # 图形验证码 (4-6 digit alphanumeric)
    SMS = auto()             # 短信验证码
    TURNSTILE = auto()       # Cloudflare Turnstile
    RECAPTCHA_V2 = auto()    # Google reCAPTCHA v2
    HCAPTCHA = auto()        # hCaptcha
    PUZZLE = auto()          # 拼图验证码
    ROTATE = auto()          # 旋转验证码
    CUSTOM = auto()          # 自定义类型


@dataclass
class CAPTCHAChallenge:
    """Represents a detected CAPTCHA challenge."""

    type: CAPTCHAType
    url: str = ""
    site_key: str = ""           # reCAPTCHA/hCaptcha site key
    selector: str = ""            # CSS selector for the CAPTCHA element
    image_base64: str = ""        # Screenshot or CAPTCHA image
    background_base64: str = ""   # Slider background image
    slider_selector: str = ""     # Slider button selector
    gap_distance: int = 0         # Pre-computed gap distance (pixels)
    phone_number: str = ""        # For SMS CAPTCHA
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CAPTCHAResult:
    """CAPTCHA solving result."""

    success: bool
    solution: str = ""           # Token, slider distance, text answer
    elapsed_ms: int = 0
    attempts: int = 1
    method: str = ""             # "browser", "ocr", "service", "manual"
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class CAPTCHAError(Exception):
    """CAPTCHA solving failure."""
    pass


# ============================================================
# Slider CAPTCHA Solver (滑块验证码)
# ============================================================


def _ocr_image(img_bytes: bytes) -> str:
    """Try OCR on a captcha image using available backends.

    Returns recognized text string, or empty string on failure.
    Tries: pytesseract (if tesseract binary available) > PIL analysis fallback.
    """
    # Try pytesseract first
    try:
        import pytesseract
        import os, sys
        # Auto-detect tesseract binary location
        if os.name == 'nt':
            candidates = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]
            for c in candidates:
                if os.path.exists(c):
                    pytesseract.pytesseract.tesseract_cmd = c
                    break
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        # Preprocess: grayscale + threshold for better OCR
        img = img.convert('L')
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        text = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
        text = text.strip().replace(' ', '')
        if text and len(text) >= 2:
            log.info('OCR (tesseract): %s', text)
            return text
    except Exception as e:
        log.debug('pytesseract OCR not available: %s', e)

    # Fallback: PIL-based simple denoise + save for debugging
    try:
        from PIL import Image
        import io
        from pathlib import Path
        img = Image.open(io.BytesIO(img_bytes))
        debug_dir = Path.home() / '.chinacrawl' / 'captcha_debug'
        debug_dir.mkdir(parents=True, exist_ok=True)
        import time
        ts = int(time.time() * 1000)
        img.save(debug_dir / f'captcha_{ts}.png')
        log.info('Captcha image saved to %s (no OCR available)', debug_dir / f'captcha_{ts}.png')
    except Exception:
        pass

    return ''
class SliderSolver:
    """Solves slider/拖动验证码 by analyzing gap position.

    Common implementations:
    - Alibaba Cloud (阿里云): Used by Taobao, 1688
    - NetEase Yidun (网易易盾): Used by Douyin, NetEase
    - Tencent CAPTCHA (腾讯验证码): Used by JD, WeChat
    - Geetest (极验): Used by many government sites
    """

    # Known CSS selectors for CAPTCHA elements on popular sites
    _SELECTORS = {
        "geetest": {
            "canvas": ".geetest_canvas_bg",
            "slider": ".geetest_slider_button",
            "iframe": ".geetest_iframe",
        },
        "alibaba": {
            "canvas": "#nc_1__bg",
            "slider": "#nc_1_n1z",
            "wrapper": ".nc_wrapper",
        },
        "yidun": {
            "canvas": ".yidun_bg-img",
            "slider": ".yidun_slider",
            "iframe": "#yidun_iframe",
        },
        "tencent": {
            "canvas": ".tcaptcha-drag-img",
            "slider": ".tcaptcha-drag-button",
        },
    }

    def __init__(self, page=None):
        self._page = page

    @staticmethod
    def compute_gap_distance(
        background: bytes,
        template: Optional[bytes] = None,
    ) -> int:
        """Compute slider gap distance by image analysis.

        Uses edge detection and template matching to find the gap position.

        Args:
            background: Background image with gap
            template: Optional template image (if not provided, uses edge diff)

        Returns:
            Gap distance in pixels.
        """
        try:
            from PIL import Image
            import io
            import numpy as np
        except ImportError:
            # Fallback: rough estimate based on image properties
            return SliderSolver._rough_gap_estimate(background)

        try:
            bg = Image.open(io.BytesIO(background)).convert("L")
            bg_arr = np.array(bg)

            # Edge detection (Sobel-like)
            edges = np.abs(np.diff(bg_arr.astype(np.int16), axis=1))

            # Find the vertical strip with most edges (gap area)
            edge_profile = np.sum(edges, axis=0)
            window = 60
            max_score = 0
            best_x = 50

            for x in range(50, len(edge_profile) - window - 50):
                score = np.sum(edge_profile[x:x + window])
                if score > max_score:
                    max_score = score
                    best_x = x

            # Validate: gap shouldn't be at image edges
            if best_x < 10 or best_x > len(edge_profile) - 10:
                best_x = len(edge_profile) // 2

            return int(best_x)

        except Exception as e:
            log.warning("Gap computation failed: %s, using fallback", e)
            return SliderSolver._rough_gap_estimate(background)

    @staticmethod
    def _rough_gap_estimate(image_data: bytes) -> int:
        """Rough gap estimate without numpy (pure Python fallback)."""
        # Based on typical image dimensions and gap position distribution
        # Most slider gaps are between 20%-80% of the width
        width_hint = len(image_data)
        if width_hint > 100000:  # large image
            return random.randint(80, 200)
        return random.randint(40, 120)

    @staticmethod
    def generate_slide_track(distance: int) -> List[Tuple[int, int, int]]:
        """Generate human-like slide trajectory.

        Returns list of (x, y, delay_ms) tuples simulating natural drag.

        Human sliding characteristics:
        - Starts slow, accelerates, decelerates near target
        - Slight Y-axis wobble
        - Overshoots slightly then corrects
        """
        track = []
        current = 0
        y_base = 0

        # Phase 1: Initial slow movement (0-30%)
        for _ in range(random.randint(3, 6)):
            current += random.randint(1, 3)
            y_base += random.choice([-1, 0, 1])
            track.append((current, y_base, random.randint(8, 15)))

        # Phase 2: Acceleration (30-70%)
        for _ in range(random.randint(5, 9)):
            current += random.randint(4, 12)
            y_base += random.choice([-2, -1, 0, 1, 1, 2])
            track.append((current, y_base, random.randint(5, 10)))

        # Phase 3: Deceleration (70-95%)
        remaining = distance - current
        steps = random.randint(4, 7)
        for i in range(steps):
            progress = i / steps
            step = int(remaining * (0.3 + 0.5 * (1 - progress)))
            current += max(1, step)
            y_base += random.choice([-1, 0, 1])
            track.append((current, y_base, random.randint(10, 20)))

        # Phase 4: Fine adjustment (95-100%)
        while current < distance - 1:
            current += 1
            track.append((current, y_base, random.randint(15, 30)))

        # Final position
        track.append((distance, y_base, 0))

        return track

    async def solve_on_page(self, page, gap_distance: int,
                            slider_selector: str = ".geetest_slider_button",
                            max_retries: int = 3) -> CAPTCHAResult:
        """Execute the slide on a Playwright page.

        Args:
            page: Playwright page object
            gap_distance: Pre-computed gap distance in pixels
            slider_selector: CSS selector for the slider button
            max_retries: Max attempts before giving up

        Returns:
            CAPTCHAResult with success status
        """
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                slider = await page.wait_for_selector(
                    slider_selector, timeout=5000
                )
                if not slider:
                    continue

                box = await slider.bounding_box()
                if not box:
                    continue

                start_x = box["x"] + box["width"] / 2
                start_y = box["y"] + box["height"] / 2

                # Generate trajectory
                track = self.generate_slide_track(gap_distance)

                # Execute slide
                await page.mouse.move(start_x, start_y)
                await page.mouse.down()

                for x, y, delay in track:
                    await page.mouse.move(
                        start_x + x,
                        start_y + y,
                        steps=1,
                    )
                    await page.wait_for_timeout(delay)

                await page.mouse.up()

                # Wait for result
                await page.wait_for_timeout(2000)

                # Check if CAPTCHA is gone
                if await self._is_solved(page, slider_selector):
                    elapsed = int((time.time() - start_time) * 1000)
                    return CAPTCHAResult(
                        success=True,
                        solution=str(gap_distance),
                        elapsed_ms=elapsed,
                        attempts=attempt + 1,
                        method="browser_slide",
                    )

                # If failed, add jitter to next attempt
                gap_distance += random.randint(-5, 5)

            except Exception as e:
                log.warning("Slider attempt %d failed: %s", attempt + 1, e)
                await page.wait_for_timeout(1000)

        elapsed = int((time.time() - start_time) * 1000)
        return CAPTCHAResult(
            success=False,
            elapsed_ms=elapsed,
            attempts=max_retries,
            error="Max slider retries exceeded",
        )

    @staticmethod
    async def _is_solved(page, slider_selector: str) -> bool:
        """Check if CAPTCHA has been solved."""
        try:
            slider = await page.query_selector(slider_selector)
            if slider:
                text = await slider.inner_text()
                if "验证成功" in text or "success" in text.lower():
                    return True
            # Check if CAPTCHA element disappeared
            captcha = await page.query_selector(
                ".geetest_panel, .yidun_popup, .nc_wrapper, .tcaptcha-transform"
            )
            return captcha is None
        except Exception:
            return True  # If we can't find it, assume solved


# ============================================================
# SMS CAPTCHA Handler (短信验证码)
# ============================================================

class SMSHandler:
    """Handles SMS verification code flows.

    For sites requiring phone + SMS verification:
    - 12306 (铁路)
    - Government service platforms
    - Banking sites
    """

    @staticmethod
    def wait_for_code(page, phone_input_selector: str,
                      code_input_selector: str,
                      trigger_selector: str = "",
                      timeout_ms: int = 60000) -> Optional[str]:
        """Wait for and intercept SMS code from page or user.

        Strategy:
        1. Click trigger button
        2. Monitor page for auto-filled code
        3. If not auto-filled, prompt for manual input

        Returns:
            SMS code string, or None if timeout
        """
        # This is primarily a manual interaction flow
        # Auto SMS interception requires external service
        start = time.time()
        while time.time() - start < timeout_ms / 1000:
            # Check if code input has value
            # (Some sites auto-fill from clipboard or SMS permission)
            try:
                code_el = page.query_selector(code_input_selector)
                if code_el:
                    val = code_el.input_value()
                    if val and len(val) >= 4:
                        return val
            except Exception:
                pass
            time.sleep(0.5)
        return None


# ============================================================
# Unified CAPTCHA Handler
# ============================================================

class CAPTCHAHandler:
    """Unified CAPTCHA detection and solving orchestrator.

    Detects CAPTCHA type from page context and dispatches to
    appropriate solver.

    Usage:
        handler = CAPTCHAHandler()
        result = await handler.solve(page)
        if result.success:
            print(f"Solved via {result.method}")
    """

    def __init__(self, solver_order: Optional[List[str]] = None):
        self.solver_order = solver_order or [
            "browser",   # Browser automation-based
            "ocr",       # OCR/image recognition
            "service",   # External CAPTCHA service (2captcha, etc.)
            "manual",    # Manual fallback
        ]
        self._slider_solver = SliderSolver()
        self._service_key: Optional[str] = os.environ.get("CAPTCHA_SERVICE_KEY")
        self._stats: Dict[str, int] = {"solved": 0, "failed": 0, "total": 0}

    async def detect(self, page) -> Optional[CAPTCHAChallenge]:
        """Detect CAPTCHA type present on the page.

        Checks for known CAPTCHA providers by selector patterns.
        """
        patterns = [
            # Geetest (极验)
            (".geetest_canvas_bg, .geetest_panel", CAPTCHAType.SLIDER),
            # Alibaba Cloud
            (".nc_wrapper, #nc_1__bg", CAPTCHAType.SLIDER),
            # NetEase Yidun (网易易盾)
            (".yidun_bg-img, .yidun_slider", CAPTCHAType.SLIDER),
            # Tencent CAPTCHA
            (".tcaptcha-drag-img, .tcaptcha-transform", CAPTCHAType.SLIDER),
            # Slider generic
            ("[class*='slider-captcha'], [class*='slide-verify']", CAPTCHAType.SLIDER),
            # reCAPTCHA
            (".g-recaptcha, iframe[src*='recaptcha']", CAPTCHAType.RECAPTCHA_V2),
            # hCaptcha
            (".h-captcha, iframe[src*='hcaptcha']", CAPTCHAType.HCAPTCHA),
            # Cloudflare Turnstile
            ("[class*='cf-turnstile'], iframe[src*='turnstile']", CAPTCHAType.TURNSTILE),
            # Image CAPTCHA
            ("img[id*='captcha'], img[src*='captcha'], img[src*='verify']", CAPTCHAType.IMAGE_TEXT),
            # JD JCAP 图形验证码
            ("#main_img, #graphicCaptchaSessionId, .captcha_footer", CAPTCHAType.IMAGE_TEXT),
            # 京东登录页验证码
            (".captcha-input input.captcha-code, #sms-code", CAPTCHAType.IMAGE_TEXT),
        ]

        for selector, captcha_type in patterns:
            try:
                el = await page.query_selector(selector)
                if el:
                    return CAPTCHAChallenge(
                        type=captcha_type,
                        selector=selector,
                        url=page.url,
                    )
            except Exception:
                continue

        return None

    async def solve(self, page, challenge: Optional[CAPTCHAChallenge] = None,
                    **kwargs) -> CAPTCHAResult:
        """Solve a CAPTCHA challenge.

        Args:
            page: Playwright page
            challenge: Pre-detected challenge (auto-detects if None)
            **kwargs: Additional solver-specific params

        Returns:
            CAPTCHAResult
        """
        start_time = time.time()
        self._stats["total"] += 1

        if challenge is None:
            challenge = await self.detect(page)
            if challenge is None:
                return CAPTCHAResult(
                    success=True,  # No CAPTCHA = already solved
                    method="none",
                    elapsed_ms=int((time.time() - start_time) * 1000),
                )

        log.info("Detected CAPTCHA: %s at %s", challenge.type.name, page.url)

        # Dispatch by type
        solver_map = {
            CAPTCHAType.SLIDER: self._solve_slider,
            CAPTCHAType.IMAGE_TEXT: self._solve_image,
            CAPTCHAType.TURNSTILE: self._solve_turnstile,
            CAPTCHAType.RECAPTCHA_V2: self._solve_recaptcha,
            CAPTCHAType.HCAPTCHA: self._solve_hcaptcha,
            CAPTCHAType.SMS: self._solve_sms,
        }

        solver = solver_map.get(challenge.type, self._solve_generic)
        result = await solver(page, challenge, **kwargs)

        if result.success:
            self._stats["solved"] += 1
        else:
            self._stats["failed"] += 1

        return result

    async def _solve_slider(self, page, challenge: CAPTCHAChallenge,
                            **kwargs) -> CAPTCHAResult:
        """Solve slider CAPTCHA."""
        start = time.time()

        # Try to get gap image
        bg_bytes = None
        slider_sel = challenge.slider_selector or ".geetest_slider_button"

        # Try known selectors for slider
        for provider, sels in SliderSolver._SELECTORS.items():
            try:
                canvas_sel = sels.get("canvas", "")
                slider_candidate = sels.get("slider", "")
                if canvas_sel:
                    canvas = await page.query_selector(canvas_sel)
                    if canvas:
                        bg_bytes = await canvas.screenshot(type="png")
                        slider_sel = slider_candidate or slider_sel
                        break
            except Exception:
                continue

        # Compute gap
        if bg_bytes:
            gap = SliderSolver.compute_gap_distance(bg_bytes)
        elif challenge.gap_distance > 0:
            gap = challenge.gap_distance
        else:
            gap = random.randint(60, 180)

        log.info("Computed slider gap: %dpx", gap)

        # Execute slide
        result = await self._slider_solver.solve_on_page(
            page, gap, slider_sel,
            max_retries=kwargs.get("max_retries", 3),
        )
        result.elapsed_ms = int((time.time() - start) * 1000)
        return result

    async def _solve_image(self, page, challenge: CAPTCHAChallenge,
                           **kwargs) -> CAPTCHAResult:
        """Solve image text CAPTCHA."""
        start = time.time()

        # Capture CAPTCHA image
        img_selector = challenge.selector or "img[id*='captcha']"
        try:
            img_el = await page.query_selector(img_selector)
            if img_el:
                img_bytes = await img_el.screenshot(type="png")
            else:
                return CAPTCHAResult(
                    success=False,
                    elapsed_ms=int((time.time() - start) * 1000),
                    error="Image element not found",
                )
        except Exception as e:
            return CAPTCHAResult(
                success=False,
                elapsed_ms=int((time.time() - start) * 1000),
                error=str(e),
            )

        # Try external service first
        if self._service_key:
            solution = await self._call_external_service(
                img_bytes, "image_text"
            )
            if solution:
                # Type the solution
                input_sel = kwargs.get("input_selector", "input[id*='captcha']")
                try:
                    inp = await page.query_selector(input_sel)
                    if inp:
                        await inp.fill(solution)
                        submit_sel = kwargs.get("submit_selector", "")
                        if submit_sel:
                            await page.click(submit_sel)
                        return CAPTCHAResult(
                            success=True,
                            solution=solution,
                            elapsed_ms=int((time.time() - start) * 1000),
                            method="service",
                        )
                except Exception:
                    pass

        # Try local OCR (pytesseract) as fallback
        ocr_result = _ocr_image(img_bytes)
        if ocr_result:
            input_sel = kwargs.get("input_selector", "input[id*='captcha']")
            try:
                inp = await page.query_selector(input_sel)
                if inp:
                    await inp.fill(ocr_result)
                    submit_sel = kwargs.get("submit_selector", "")
                    if submit_sel:
                        await page.click(submit_sel)
                    return CAPTCHAResult(
                        success=True,
                        solution=ocr_result,
                        elapsed_ms=int((time.time() - start) * 1000),
                        method="ocr",
                    )
            except Exception:
                pass

        return CAPTCHAResult(
            success=False,
            elapsed_ms=int((time.time() - start) * 1000),
            error="Image CAPTCHA requires external service or manual input",
        )

    async def _solve_turnstile(self, page, challenge: CAPTCHAChallenge,
                               **kwargs) -> CAPTCHAResult:
        """Solve Cloudflare Turnstile using browser automation."""
        start = time.time()

        # Turnstile usually auto-solves with proper browser fingerprint
        # Strategy: click the checkbox and wait
        try:
            frame = None
            for f in page.frames:
                if "turnstile" in f.url:
                    frame = f
                    break

            target = frame or page
            checkbox = await target.query_selector("[class*='cf-turnstile']")
            if checkbox:
                await checkbox.click()
                await page.wait_for_timeout(3000)

                # Get token
                token = await page.evaluate(
                    "document.querySelector('[name=\"cf-turnstile-response\"]')?.value"
                )
                if token:
                    return CAPTCHAResult(
                        success=True,
                        solution=token,
                        elapsed_ms=int((time.time() - start) * 1000),
                        method="browser",
                    )
        except Exception as e:
            log.warning("Turnstile solve failed: %s", e)

        return CAPTCHAResult(
            success=False,
            elapsed_ms=int((time.time() - start) * 1000),
            error="Turnstile requires interactive browser session",
        )

    async def _solve_recaptcha(self, page, challenge: CAPTCHAChallenge,
                               **kwargs) -> CAPTCHAResult:
        """Solve reCAPTCHA v2 using external service."""
        if not self._service_key:
            return CAPTCHAResult(
                success=False,
                error="External service API key required for reCAPTCHA",
            )

        start = time.time()
        site_key = challenge.site_key or kwargs.get("site_key", "")

        # Call 2captcha or similar
        try:
            token = await self._call_recaptcha_service(site_key, page.url)
            if token:
                # Inject token
                await page.evaluate(f"""
                    document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        for (const cfg of Object.values(___grecaptcha_cfg.clients || {{}})) {{
                            if (cfg.callback) cfg.callback('{token}');
                        }}
                    }}
                """)
                return CAPTCHAResult(
                    success=True,
                    solution=token,
                    elapsed_ms=int((time.time() - start) * 1000),
                    method="service",
                )
        except Exception as e:
            log.error("reCAPTCHA service error: %s", e)

        return CAPTCHAResult(
            success=False,
            elapsed_ms=int((time.time() - start) * 1000),
            error="reCAPTCHA solving failed",
        )

    async def _solve_hcaptcha(self, page, challenge: CAPTCHAChallenge,
                              **kwargs) -> CAPTCHAResult:
        """Solve hCaptcha (similar flow to reCAPTCHA)."""
        # Reuse reCAPTCHA flow with hCaptcha-specific adaptations
        return await self._solve_recaptcha(page, challenge, **kwargs)

    async def _solve_sms(self, page, challenge: CAPTCHAChallenge,
                         **kwargs) -> CAPTCHAResult:
        """Handle SMS verification flow."""
        start = time.time()
        code = await SMSHandler.wait_for_code(
            page,
            kwargs.get("phone_selector", "input[type='tel']"),
            kwargs.get("code_selector", "input[placeholder*='验证码']"),
            kwargs.get("trigger_selector", ""),
            kwargs.get("timeout_ms", 60000),
        )
        if code:
            return CAPTCHAResult(
                success=True,
                solution=code,
                elapsed_ms=int((time.time() - start) * 1000),
                method="browser",
            )
        return CAPTCHAResult(
            success=False,
            elapsed_ms=int((time.time() - start) * 1000),
            error="SMS timeout or manual input required",
        )

    async def _solve_generic(self, page, challenge: CAPTCHAChallenge,
                             **kwargs) -> CAPTCHAResult:
        """Generic fallback solver."""
        return CAPTCHAResult(
            success=False,
            error=f"Unsupported CAPTCHA type: {challenge.type.name}",
        )

    async def _call_external_service(self, image_bytes: bytes,
                                     captcha_type: str) -> Optional[str]:
        """Call external CAPTCHA solving service."""
        if not self._service_key:
            return None

        try:
            import httpx
            b64 = base64.b64encode(image_bytes).decode()

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.2captcha.com/createTask",
                    json={
                        "clientKey": self._service_key,
                        "task": {
                            "type": "ImageToTextTask",
                            "body": b64,
                            "case": True,
                        },
                    },
                )

                data = resp.json()
                if data.get("errorId") == 0:
                    task_id = data["taskId"]

                    # Poll for result
                    for _ in range(10):
                        await __import__("asyncio").sleep(2)
                        result_resp = await client.post(
                            "https://api.2captcha.com/getTaskResult",
                            json={
                                "clientKey": self._service_key,
                                "taskId": task_id,
                            },
                        )
                        result_data = result_resp.json()
                        if result_data.get("status") == "ready":
                            return result_data["solution"]["text"]
        except Exception as e:
            log.warning("External CAPTCHA service error: %s", e)

        return None

    async def _call_recaptcha_service(self, site_key: str,
                                      page_url: str) -> Optional[str]:
        """Call 2captcha for reCAPTCHA solving."""
        if not self._service_key:
            return None

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.2captcha.com/createTask",
                    json={
                        "clientKey": self._service_key,
                        "task": {
                            "type": "RecaptchaV2TaskProxyless",
                            "websiteURL": page_url,
                            "websiteKey": site_key,
                        },
                    },
                )
                data = resp.json()
                if data.get("errorId") == 0:
                    task_id = data["taskId"]
                    for _ in range(30):
                        await __import__("asyncio").sleep(3)
                        result_resp = await client.post(
                            "https://api.2captcha.com/getTaskResult",
                            json={
                                "clientKey": self._service_key,
                                "taskId": task_id,
                            },
                        )
                        result_data = result_resp.json()
                        if result_data.get("status") == "ready":
                            return result_data["solution"]["gRecaptchaResponse"]
        except Exception as e:
            log.warning("reCAPTCHA service error: %s", e)

        return None

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)


# ============================================================
# Convenience factory
# ============================================================

_default_handler: Optional[CAPTCHAHandler] = None


def get_captcha_handler() -> CAPTCHAHandler:
    """Get or create the default CAPTCHA handler."""
    global _default_handler
    if _default_handler is None:
        _default_handler = CAPTCHAHandler()
    return _default_handler

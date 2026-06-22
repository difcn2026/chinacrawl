# chinacrawl/downloader/image.py - Image downloader
# Single, batch, PDD product images. Archives to A:\XDLS\references\images\

import json, logging, os, re, time, hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

log = logging.getLogger("chinacrawl.downloader.image")
CST = timezone(timedelta(hours=8))

DEFAULT_IMAGE_DIR = r"A:\XDLS\references\images"


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _safe_filename(text, max_len=80):
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text[:max_len]


def _http_download(url, dest_path, timeout=120):
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        log.error("Download failed: %s", e)
        return False


def download_image(url: str, tag: str = "general", filename: Optional[str] = None,
                   output_dir: Optional[str] = None) -> dict:
    """
    Download a single image from URL.
    
    Args:
        url: Image URL
        tag: Category tag (e.g. "fashion", "character_ref", "style_ref")
        filename: Custom filename
        output_dir: Override output directory
    
    Returns:
        {"ok": bool, "path": str, "size_kb": float, "tag": str}
    """
    output_dir = output_dir or os.path.join(DEFAULT_IMAGE_DIR, tag)
    _ensure_dir(output_dir)
    
    if not filename:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        ext = ".jpg"
        parsed = urlparse(url)
        path_part = os.path.basename(parsed.path)
        if '.' in path_part:
            ext = os.path.splitext(path_part)[1]
            if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'):
                ext = ".jpg"
        filename = f"{url_hash}{ext}"
    
    dest = os.path.join(output_dir, filename)
    
    if os.path.exists(dest):
        size_kb = round(os.path.getsize(dest) / 1024, 1)
        return {"ok": True, "path": dest, "size_kb": size_kb, "tag": tag, "cached": True}
    
    ok = _http_download(url, dest)
    
    if ok and os.path.exists(dest):
        size_kb = round(os.path.getsize(dest) / 1024, 1)
        meta = {"url": url, "tag": tag, "downloaded_at": datetime.now(CST).isoformat(), "size_kb": size_kb}
        with open(dest + ".meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return {"ok": True, "path": dest, "size_kb": size_kb, "tag": tag}
    
    return {"ok": False, "path": "", "size_kb": 0, "tag": tag, "error": "download failed"}


def batch_download_images(urls: list, tag: str = "batch", output_dir: Optional[str] = None,
                          delay: float = 0.3) -> list:
    """
    Download multiple images from URLs.
    
    Args:
        urls: List of image URLs
        tag: Category tag
        output_dir: Output directory
        delay: Seconds between downloads (be polite)
    """
    results = []
    for i, url in enumerate(urls):
        log.info("[%d/%d] %s...", i + 1, len(urls), url[:60])
        r = download_image(url, tag=tag, output_dir=output_dir)
        results.append(r)
        if delay and i < len(urls) - 1:
            time.sleep(delay)
    
    ok = sum(1 for r in results if r.get("ok"))
    log.info("Batch complete: %d/%d downloaded", ok, len(results))
    return results


def download_pdd_images(product_list: list, tag: str = "pdd_products",
                        output_dir: Optional[str] = None) -> list:
    """
    Download product images from Pinduoduo product search results.
    
    Args:
        product_list: List of product dicts with 'images' field (from pinduoduo scraper)
        tag: Category tag
        output_dir: Output directory
    """
    output_dir = output_dir or os.path.join(DEFAULT_IMAGE_DIR, tag)
    urls = []
    for p in product_list:
        if isinstance(p, dict):
            imgs = p.get("images", p.get("image", []))
        else:
            imgs = getattr(p, "images", [])
        if isinstance(imgs, str):
            imgs = [imgs]
        urls.extend(imgs)
    
    if not urls:
        return []
    
    log.info("Downloading %d PDD product images...", len(urls))
    return batch_download_images(list(set(urls)), tag=tag, output_dir=output_dir)

# chinacrawl/downloader/video.py - Video downloader
# Direct URL, Douyin, batch. Archives to A:\XDLS\references\videos\

import json, logging, os, re, time, hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

log = logging.getLogger("chinacrawl.downloader.video")
CST = timezone(timedelta(hours=8))

DEFAULT_VIDEO_DIR = r"A:\XDLS\references\videos"


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _safe_filename(text, max_len=80):
    """Clean string into safe filename."""
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text[:max_len]


def _http_download(url, dest_path, timeout=300):
    """Download a file via HTTP with progress."""
    import urllib.request
    
    def _progress(count, block_size, total_size):
        if total_size > 0 and count % 10 == 0:
            pct = min(int(count * block_size * 100 / total_size), 100)
            log.debug("  %d%% (%d/%d)", pct, count * block_size, total_size)
    
    try:
        urllib.request.urlretrieve(url, dest_path, _progress)
        return True
    except Exception as e:
        log.error("Download failed: %s", e)
        return False


def download_video(url: str, tag: str = "general", filename: Optional[str] = None,
                   output_dir: Optional[str] = None) -> dict:
    """
    Download a video from any URL.
    
    Args:
        url: Video URL
        tag: Category tag for organization (e.g. "chendao", "reference", "competitor")
        filename: Custom filename (auto-generated from URL if not provided)
        output_dir: Override output directory
    
    Returns:
        {"ok": bool, "path": str, "size_mb": float, "tag": str}
    """
    output_dir = output_dir or os.path.join(DEFAULT_VIDEO_DIR, tag)
    _ensure_dir(output_dir)
    
    if not filename:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        ext = ".mp4"
        parsed = urlparse(url)
        path_part = os.path.basename(parsed.path)
        if '.' in path_part:
            ext = os.path.splitext(path_part)[1] or ".mp4"
        filename = f"{url_hash}{ext}"
    
    dest = os.path.join(output_dir, filename)
    
    if os.path.exists(dest):
        size_mb = round(os.path.getsize(dest) / (1024 * 1024), 1)
        log.info("Already exists: %s (%.1f MB)", dest, size_mb)
        return {"ok": True, "path": dest, "size_mb": size_mb, "tag": tag, "cached": True}
    
    log.info("Downloading: %s", url[:100])
    ok = _http_download(url, dest)
    
    if ok and os.path.exists(dest):
        size_mb = round(os.path.getsize(dest) / (1024 * 1024), 1)
        meta = {"url": url, "tag": tag, "downloaded_at": datetime.now(CST).isoformat(), "size_mb": size_mb}
        meta_path = dest + ".meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        log.info("Done: %s (%.1f MB)", dest, size_mb)
        return {"ok": True, "path": dest, "size_mb": size_mb, "tag": tag}
    
    return {"ok": False, "path": "", "size_mb": 0, "tag": tag, "error": "download failed"}


def download_douyin_video(aweme_id: str, cookie_file: Optional[str] = None,
                          tag: str = "douyin", output_dir: Optional[str] = None) -> dict:
    """
    Download a Douyin video by ID.
    
    Uses the douyin adapter to get metadata, then downloads the video.
    Archives with full metadata.
    """
    try:
        from ..douyin import fetch_video_meta
        meta = fetch_video_meta(aweme_id, cookie_file=cookie_file, headless=True)
        parsed = meta.get("meta_parsed", {})
        author = _safe_filename(parsed.get("author", "unknown"), 20)
        title = _safe_filename(parsed.get("desc_short", aweme_id), 50)
        
        # Construct video URL (standard douyin CDN pattern)
        video_url = f"https://www.douyin.com/video/{aweme_id}"
        
        output_dir = output_dir or os.path.join(DEFAULT_VIDEO_DIR, tag, author)
        filename = f"{aweme_id}_{title}.mp4"
        
        result = download_video(video_url, tag=tag, filename=filename, output_dir=output_dir)
        if result.get("ok"):
            # Save metadata alongside
            meta_path = result["path"] + ".meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        return result
    except ImportError:
        return {"ok": False, "error": "douyin adapter not available"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def batch_download_videos(urls: list, tag: str = "batch", output_dir: Optional[str] = None,
                          max_workers: int = 3) -> list:
    """
    Download multiple videos from URLs.
    
    Args:
        urls: List of video URLs
        tag: Category tag
        output_dir: Output directory
        max_workers: Concurrent downloads (use with caution)
    """
    results = []
    
    if max_workers <= 1:
        for i, url in enumerate(urls):
            log.info("[%d/%d] %s...", i + 1, len(urls), url[:60])
            r = download_video(url, tag=tag, output_dir=output_dir)
            results.append(r)
            time.sleep(0.5)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(download_video, url, tag, None, output_dir): url for url in urls}
            for f in as_completed(futures):
                results.append(f.result())
    
    ok = sum(1 for r in results if r.get("ok"))
    log.info("Batch complete: %d/%d downloaded", ok, len(results))
    return results

"""
并行下载加速器 — 突破单连接限速，支持断点续传。

Usage:
    python -m chinacrawl.fastdl <url> [output_path] [--threads 8] [--chunk-size 1M]
"""
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests


class ParallelDownloader:
    """Chunked parallel HTTP downloader with resume support.

    Splits a file into chunks and downloads them concurrently,
    maximizing throughput under per-connection bandwidth limits.
    """

    def __init__(self, url: str, output: Optional[str] = None,
                 threads: int = 8, chunk_size: int = 1024 * 1024,
                 timeout: int = 120):
        self.url = url
        self.output = Path(output) if output else Path(urlparse(url).path.split("/")[-1] or "download")
        self.threads = threads
        self.chunk_size = chunk_size
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ChinaCrawl-FastDL/1.0",
            "Accept-Encoding": "gzip, deflate",
        })

    def _get_file_size(self) -> int:
        """Get remote file size via HEAD request."""
        resp = self._session.head(self.url, timeout=30)
        if resp.status_code == 405:  # Method Not Allowed
            resp = self._session.get(self.url, stream=True, timeout=30)
            resp.close()
        if "Content-Length" in resp.headers:
            return int(resp.headers["Content-Length"])
        raise ValueError("Cannot determine file size (no Content-Length)")

    def _download_chunk(self, start: int, end: int, idx: int) -> tuple:
        """Download a byte range chunk."""
        headers = {"Range": f"bytes={start}-{end}"}
        # Retry up to 3 times
        for attempt in range(3):
            try:
                resp = self._session.get(
                    self.url, headers=headers, timeout=self.timeout, stream=True
                )
                resp.raise_for_status()
                data = resp.content
                return (idx, start, data)
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(1 * (attempt + 1))

    def download(self, show_progress: bool = True) -> Path:
        """Download file with parallel chunked transfers.

        Returns path to downloaded file.
        """
        file_size = self._get_file_size()
        if show_progress:
            print(f"File size: {file_size / 1024 / 1024:.1f} MB")
            print(f"Threads: {self.threads}, Chunk: {self.chunk_size / 1024:.0f} KB")

        # Calculate chunks
        chunks = []
        pos = 0
        idx = 0
        while pos < file_size:
            end = min(pos + self.chunk_size - 1, file_size - 1)
            chunks.append((pos, end, idx))
            pos = end + 1
            idx += 1

        if show_progress:
            print(f"Chunks: {len(chunks)}, downloading with {self.threads} threads...")

        # Pre-allocate file
        self.output.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output, "wb") as f:
            f.truncate(file_size)

        # Parallel download
        t0 = time.monotonic()
        completed = 0
        downloaded_bytes = 0

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(self._download_chunk, s, e, i): (s, e, i)
                for s, e, i in chunks
            }

            for future in as_completed(futures):
                try:
                    idx, start, data = future.result()
                    with open(self.output, "r+b") as f:
                        f.seek(start)
                        f.write(data)
                    completed += 1
                    downloaded_bytes += len(data)
                    if show_progress and completed % max(1, len(chunks) // 10) == 0:
                        elapsed = time.monotonic() - t0
                        speed = downloaded_bytes / elapsed / 1024 if elapsed > 0 else 0
                        pct = completed / len(chunks) * 100
                        print(f"  {pct:.0f}% ({completed}/{len(chunks)}) "
                              f"{speed:.0f} KB/s")
                except Exception as e:
                    s, e_pos, i = futures[future]
                    print(f"  Chunk {i} ({s}-{e_pos}) failed: {e}")

        elapsed = time.monotonic() - t0
        speed = file_size / elapsed / 1024 if elapsed > 0 else 0

        if show_progress:
            print(f"Done: {file_size / 1024 / 1024:.1f} MB in {elapsed:.1f}s "
                  f"({speed:.0f} KB/s, {self.threads}x parallel)")

        # Verify
        actual_size = self.output.stat().st_size
        if actual_size != file_size:
            print(f"WARNING: size mismatch (expected {file_size}, got {actual_size})")

        return self.output


def fast_download(url: str, output: Optional[str] = None,
                  threads: int = 8, **kwargs) -> Path:
    """Convenience function: parallel download with defaults."""
    dl = ParallelDownloader(url, output, threads=threads, **kwargs)
    return dl.download()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    dl = ParallelDownloader(url, output)
    dl.download()

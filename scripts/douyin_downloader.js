// douyin_downloader.js — Batch download Douyin videos from metadata JSON
// Usage: node douyin_downloader.js [startIndex] [endIndex]

const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");

const VIDEOS_DIR = path.join(__dirname, "..", "projects", "douyin-xiaobing", "videos");
const METADATA_PATH = path.join(__dirname, "..", "projects", "douyin-xiaobing", "data", "ai_xiaobing_metadata.json");

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith("https") ? https : http;
    const req = mod.get(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.douyin.com/"
      },
      timeout: 60000
    }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        // Follow redirect
        downloadFile(res.headers.location, dest).then(resolve).catch(reject);
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      const file = fs.createWriteStream(dest);
      res.pipe(file);
      file.on("finish", () => { file.close(); resolve(fs.statSync(dest).size); });
      file.on("error", reject);
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
  });
}

async function main() {
  const allVideos = JSON.parse(fs.readFileSync(METADATA_PATH, "utf-8"));
  // Sort by likes descending
  allVideos.sort((a, b) => b.digg_count - a.digg_count);

  const startIdx = parseInt(process.argv[2]) || 0;
  const endIdx = parseInt(process.argv[3]) || allVideos.length;

  if (!fs.existsSync(VIDEOS_DIR)) {
    fs.mkdirSync(VIDEOS_DIR, { recursive: true });
  }

  // Get existing files
  const existing = new Set(fs.readdirSync(VIDEOS_DIR));

  console.log(`Total: ${allVideos.length}, Downloading [${startIdx}-${endIdx}), Existing: ${existing.size}`);

  let success = 0, fail = 0, skipped = 0, totalSize = 0;
  const count = Math.min(endIdx, allVideos.length);

  for (let i = startIdx; i < count; i++) {
    const v = allVideos[i];
    const url = v.download_url || v.play_url;
    if (!url) { fail++; continue; }

    const safeName = v.desc.replace(/[\\/:*?"<>|#]/g, "").substring(0, 40) + "_" + v.aweme_id;
    const filePath = path.join(VIDEOS_DIR, safeName + ".mp4");

    // Check if already downloaded
    const alreadyExists = [...existing].some(e => e.includes(v.aweme_id));
    if (alreadyExists) { skipped++; continue; }

    try {
      const size = await downloadFile(url, filePath);
      totalSize += size;
      success++;
      existing.add(safeName + ".mp4");

      if ((i - startIdx + 1) % 10 === 0) {
        const pct = ((i - startIdx + 1) / (count - startIdx) * 100).toFixed(0);
        console.log(`  [${i + 1}/${count}] ${pct}% | OK:${success} Fail:${fail} Skip:${skipped} | ${(size / 1048576).toFixed(1)}MB`);
      }
    } catch (e) {
      fail++;
      // Remove partial file
      try { fs.unlinkSync(filePath); } catch (_) {}
      if (fail <= 5 || fail % 20 === 0) {
        console.log(`  [${i + 1}] FAIL: ${e.message} — ${v.desc.substring(0, 30)}`);
      }
    }
  }

  const totalMB = (totalSize / 1048576).toFixed(1);
  console.log(`\n=== Done [${startIdx}-${endIdx}) ===`);
  console.log(`  Success: ${success}, Failed: ${fail}, Skipped: ${skipped}, Size: ${totalMB}MB`);
}

main().catch(e => { console.error(e); process.exit(1); });

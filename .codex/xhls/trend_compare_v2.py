# -*- coding: utf-8 -*-
"""XHLS v3.0 | Trend Scan: qwen2.5:7b vs phi3:mini Quality Comparison"""
import json, os, time, sys, re

sys.path.insert(0, r"C:\Users\Administrator\Documents\New project\.codex\xhls")

FIRECRAWL_DIR = r"C:\Users\Administrator\Documents\New project\.codex\xhls\.firecrawl"


def load_scraped_content():
    sources = []
    for i in range(5):
        path = os.path.join(FIRECRAWL_DIR, f"scrape-{i}.json")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Structure: {"markdown": "...", "metadata": {...}}
        content = data.get("markdown", "") or data.get("content", "") or ""
        meta = data.get("metadata", {}) or {}
        title = meta.get("title", "") or meta.get("og:title", "") or f"Source #{i}"
        url = meta.get("url", "") or meta.get("og:url", "") or ""
        if content:
            sources.append({
                "index": i, "title": title[:120], "url": url[:200],
                "content": content, "len": len(content)
            })
    return sources


def build_prompt(sources):
    parts = []
    for i, s in enumerate(sources):
        parts.append(f"### Source {i+1}: {s['title']}\nURL: {s['url']}\n\n{s['content'][:3000]}")
    combined = "\n\n---\n\n".join(parts)

    prompt = f"""You are a short-drama market analyst. Read the following articles about 2026 China short-drama industry trends. Output a JSON analysis.

{combined}

Output ONLY valid JSON matching this schema (no explanation):

{{
    "trends": [
        {{
            "topic": "trend topic name",
            "hotness": "S-class/A-class/B-class/C-class",
            "audience": "target audience description",
            "hook_style": "opening hook characteristics",
            "platform_fit": "best platform",
            "duration_advice": "recommended duration",
            "monetization": "monetization direction",
            "example_ref": "reference example"
        }}
    ],
    "meta": {{
        "overall_trend": "one sentence summary of 2026 June short-drama trends",
        "top3_topics": "top 3 trending topics",
        "advice": "key advice for short-drama creators",
        "risk_warning": "risk factors to watch"
    }}
}}

Identify 3-5 major trend directions. Fill each field with concrete information. If not found in sources, write "not mentioned in sources".
"""
    return prompt


def call_ollama(model, prompt, timeout=180):
    import httpx
    client = httpx.Client(timeout=timeout)
    resp = client.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.3}}
    )
    data = resp.json()
    return data.get("response", ""), data


def extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except:
        pass
    for pat in [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```',
                r'\{\s*"trends"\s*:\s*\[[\s\S]*\]\s*,\s*"meta"[\s\S]*\}\s*']:
        m = re.search(pat, text)
        if m:
            try:
                return json.loads(m.group(1) if pat.startswith('```') else m.group(0))
            except:
                continue
    return None


def score(parsed, elapsed_s, model):
    if not parsed:
        return {"score": 0, "parseable": False, "notes": "Cannot parse JSON"}

    trends = parsed.get("trends", [])
    meta = parsed.get("meta", {})

    tc = len(trends)
    ts = min(tc / 5, 1.0) * 30

    fields = ["topic", "hotness", "audience", "hook_style", "platform_fit",
              "duration_advice", "monetization", "example_ref"]
    comps = []
    for t in trends:
        f = sum(1 for k in fields if t.get(k) and "not mentioned" not in str(t.get(k, ""))
                and "string" not in str(t.get(k, "")) and "N/A" not in str(t.get(k, "")))
        comps.append(f / len(fields))
    cs = (sum(comps) / len(comps) if comps else 0) * 35

    mf = ["overall_trend", "top3_topics", "advice", "risk_warning"]
    ms = (sum(1 for k in mf if meta.get(k) and "not mentioned" not in str(meta.get(k, ""))) / len(mf)) * 15

    ss = max(0, (1 - elapsed_s / 120)) * 20

    return {
        "score": round(ts + cs + ms + ss, 1), "parseable": True,
        "trend_count": tc, "avg_completion": round(sum(comps) / len(comps) if comps else 0, 2),
        "elapsed_s": round(elapsed_s, 1),
        "breakdown": {"trends": round(ts, 1), "completeness": round(cs, 1),
                      "meta": round(ms, 1), "speed": round(ss, 1)}
    }


def main():
    os.environ["PYTHONIOENCODING"] = "utf-8"
    print("=" * 60)
    print("  XHLS Trend Compare: qwen2.5:7b vs phi3:mini")
    print("=" * 60)

    sources = load_scraped_content()
    print(f"\n  Loaded {len(sources)} articles:")
    for s in sources:
        print(f"    [{s['index']}] {s['title'][:80]} ({s['len']} chars)")

    if not sources:
        print("  ERROR: No scraped content found!")
        return

    prompt = build_prompt(sources)
    print(f"\n  Prompt size: {len(prompt)} chars")

    models = [("qwen2.5:7b", "A"), ("phi3:mini", "B")]
    all_results = {}

    for model, label in models:
        print(f"\n{'='*40}")
        print(f"  [{label}] Model: {model}")
        print(f"{'='*40}")

        start = time.time()
        try:
            response_text, raw = call_ollama(model, prompt, timeout=180)
            elapsed = time.time() - start
            print(f"  Time: {elapsed:.1f}s")
            print(f"  Output: {len(response_text)} chars")

            # Save raw
            raw_path = os.path.join(FIRECRAWL_DIR, f"raw-{model.replace(':', '-')}.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(response_text)

            prev = response_text[:300].replace("\n", " ")
            print(f"  Preview: {prev}...")

            parsed = extract_json(response_text)
            quality = score(parsed, elapsed, model)

            all_results[model] = {
                "model": model, "label": label,
                "raw": response_text, "parsed": parsed,
                "quality": quality, "elapsed_s": elapsed,
                "token_count": raw.get("eval_count", 0),
                "tps": raw.get("eval_count", 0) / elapsed if elapsed > 0 else 0,
            }

            print(f"  Parse: {'OK' if parsed else 'FAIL'}")
            print(f"  Trends: {quality.get('trend_count', 0)}")
            print(f"  Score: {quality['score']}/100")

        except Exception as e:
            elapsed = time.time() - start
            print(f"  FAIL: {e}")
            all_results[model] = {
                "model": model, "label": label,
                "error": str(e), "elapsed_s": elapsed,
                "quality": {"score": 0, "parseable": False, "notes": str(e)},
            }

    # Summary
    print(f"\n{'='*60}")
    print(f"  Final Result")
    print(f"{'='*60}")

    for model, r in all_results.items():
        q = r.get("quality", {})
        print(f"\n  [{r['label']}] {model}")
        print(f"    Time: {r['elapsed_s']:.1f}s")
        print(f"    Score: {q.get('score', 0)}/100")
        if q.get("breakdown"):
            bd = q["breakdown"]
            print(f"      Trends: {bd['trends']:.1f}/30")
            print(f"      Completeness: {bd['completeness']:.1f}/35")
            print(f"      Meta: {bd['meta']:.1f}/15")
            print(f"      Speed: {bd['speed']:.1f}/20")

    scores = {m: r.get("quality", {}).get("score", 0) for m, r in all_results.items()}
    winner = max(scores, key=scores.get) if any(scores.values()) else None
    if winner:
        loser = min(scores, key=scores.get)
        diff = scores[winner] - scores[loser]
        print(f"\n  WINNER: {winner} (+{diff:.1f})")
        if "qwen" in winner:
            print("  Decision: Use qwen2.5:7b for Chinese short-drama trend analysis.")
        else:
            print("  Decision: phi3:mini is sufficient for this task.")

    report_path = os.path.join(FIRECRAWL_DIR, "trend_compare_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Report: {report_path}")


if __name__ == "__main__":
    main()

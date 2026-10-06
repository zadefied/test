#!/usr/bin/env python3
"""Search YouTube with yt-dlp and return video metadata as JSON.

Examples:
    yt_search.py "AI agents" --limit 25 --sort views --period week
    yt_search.py "AI agents" --limit 10 --sort date --out results.json
    yt_search.py "AI agents" --urls-only

No API key is needed: yt-dlp reads YouTube's public search results page.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import sys
import urllib.parse

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp is not installed. Run: pip install yt-dlp")

# YouTube's `sp` search parameter is a small protobuf message:
#   field 1 (varint)  = sort order
#   field 2 (message) = filters { field 1 = upload date, field 2 = result type }
SORT_CODES = {"relevance": 0, "rating": 1, "date": 2, "views": 3}
PERIOD_CODES = {"hour": 1, "today": 2, "week": 3, "month": 4, "year": 5}
TYPE_VIDEO = 1


def build_search_params(sort: str, period: str | None) -> str:
    filters = bytearray()
    if period:
        filters += bytes([0x08, PERIOD_CODES[period]])
    filters += bytes([0x10, TYPE_VIDEO])

    message = bytearray()
    if SORT_CODES[sort]:
        message += bytes([0x08, SORT_CODES[sort]])
    message += bytes([0x12, len(filters)]) + filters
    return base64.b64encode(bytes(message)).decode()


def build_search_url(query: str, sort: str, period: str | None) -> str:
    params = {"search_query": query, "sp": build_search_params(sort, period)}
    return "https://www.youtube.com/results?" + urllib.parse.urlencode(params)


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def format_date(entry: dict) -> str | None:
    if entry.get("upload_date"):
        d = entry["upload_date"]
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    ts = entry.get("timestamp") or entry.get("release_timestamp")
    if ts:
        return dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat()
    return None


def normalize(entry: dict) -> dict:
    video_id = entry.get("id")
    url = entry.get("webpage_url") or entry.get("url")
    if video_id and (not url or "watch?v=" not in url):
        url = f"https://www.youtube.com/watch?v={video_id}"
    return {
        "title": entry.get("title"),
        "url": url,
        "author": entry.get("channel") or entry.get("uploader"),
        "channel_url": entry.get("channel_url") or entry.get("uploader_url"),
        "views": entry.get("view_count"),
        "duration_seconds": entry.get("duration"),
        "duration": format_duration(entry.get("duration")),
        "upload_date": format_date(entry),
        "live_status": entry.get("live_status"),
        "id": video_id,
    }


def search(query: str, limit: int, sort: str, period: str | None, full: bool,
           min_duration: int, max_duration: int | None) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        # Fetch extra rows so Shorts/live/duration filtering can still fill `limit`.
        "playlistend": limit * 3,
    }
    url = build_search_url(query, sort, period)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = [e for e in (info or {}).get("entries") or [] if e and e.get("id")]
    results = []
    for entry in entries:
        if full:
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                       "skip_download": True}) as ydl:
                    entry = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={entry['id']}", download=False)
            except yt_dlp.utils.DownloadError as exc:
                print(f"warning: skipping {entry['id']}: {exc}", file=sys.stderr)
                continue
        row = normalize(entry)
        dur = row["duration_seconds"]
        if row["live_status"] in ("is_live", "is_upcoming"):
            continue
        if dur is not None and dur < min_duration:
            continue
        if max_duration is not None and dur is not None and dur > max_duration:
            continue
        results.append(row)
        if len(results) >= limit:
            break
    return results


def print_table(rows: list[dict]) -> None:
    for i, r in enumerate(rows, 1):
        views = f"{r['views']:,}" if r["views"] is not None else "?"
        print(f"{i:>2}. {r['title']}\n    {r['author']} | {views} views | "
              f"{r['duration'] or '?'} | {r['upload_date'] or 'date n/a'}\n    {r['url']}",
              file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", help="Search query / topic")
    p.add_argument("--limit", type=int, default=25, help="Number of videos (default 25)")
    p.add_argument("--sort", choices=SORT_CODES, default="relevance",
                   help="Result order (default relevance)")
    p.add_argument("--period", choices=PERIOD_CODES,
                   help="Only videos uploaded within this period")
    p.add_argument("--full", action="store_true",
                   help="Fetch each video page for exact upload date (slower)")
    p.add_argument("--min-duration", type=int, default=61,
                   help="Skip videos shorter than N seconds; default 61 drops Shorts")
    p.add_argument("--max-duration", type=int, help="Skip videos longer than N seconds")
    p.add_argument("--out", help="Also write the JSON results to this file")
    p.add_argument("--urls-only", action="store_true", help="Print only URLs, one per line")
    args = p.parse_args()

    try:
        rows = search(args.query, args.limit, args.sort, args.period, args.full,
                      args.min_duration, args.max_duration)
    except yt_dlp.utils.DownloadError as exc:
        sys.exit(f"YouTube search failed: {exc}")

    payload = {
        "query": args.query,
        "sort": args.sort,
        "period": args.period,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count": len(rows),
        "videos": rows,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"wrote {len(rows)} videos to {args.out}", file=sys.stderr)

    if args.urls_only:
        print("\n".join(r["url"] for r in rows))
    else:
        print_table(rows)
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

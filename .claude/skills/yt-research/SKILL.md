---
name: yt-research
description: Search YouTube by topic with yt-dlp and return video metadata (title, views, author/channel, duration, upload date, URL) as JSON. Use when the user asks to find, research, scrape, or list YouTube videos on a topic, including "latest", "trending", or "most viewed" videos, or wants YouTube URLs to feed into NotebookLM.
---

# YouTube Research (yt-dlp)

Searches YouTube's public results with yt-dlp. No API key needed. Nothing is downloaded, and only
metadata is read.

## Before running

- **A topic is required.** If the user did not name a topic (or left a placeholder such as
  `[YOUR TOPIC]`), ask what they want to research before running anything.
- Dependency: `pip install yt-dlp` (the project SessionStart hook installs it automatically).

## Command

```bash
python3 .claude/skills/yt-research/scripts/yt_search.py "<topic>" \
  --limit 25 --sort views --period week --out research/<slug>-videos.json
```

| Flag | Meaning |
|---|---|
| `--limit N` | Number of videos (default 25) |
| `--sort relevance\|date\|views\|rating` | Result order (default relevance) |
| `--period hour\|today\|week\|month\|year` | Only videos uploaded within this window |
| `--full` | Open each video page for an exact upload date (slower, ~1s per video) |
| `--min-duration S` | Drop videos shorter than S seconds. The default of 61 excludes Shorts. Pass 0 to keep them |
| `--max-duration S` | Drop videos longer than S seconds |
| `--out FILE` | Also save the JSON payload to a file |
| `--urls-only` | Print only the URLs, one per line |

A readable ranked list goes to stderr, and JSON goes to stdout:
`{query, sort, period, retrieved_at, count, videos: [{title, url, author, channel_url, views,
duration_seconds, duration, upload_date, live_status, id}]}`.

## Picking the search mode

- **"Latest trending" / "trending"**: `--sort views --period week`, which gives the most-viewed
  videos uploaded this week. If that returns fewer than requested, widen to `--period month`.
- **"Latest" / "newest"**: `--sort date`.
- **"Most popular" (all time)**: `--sort views` with no period.
- **General research**: the default relevance order.

`upload_date` can be `null` in fast mode because YouTube's search page only shows relative dates.
Add `--full` when exact dates matter.

## Reporting

Show the user a compact numbered table (title, channel, views, duration, date) and say which
sort/period was used. Keep the JSON file path so the URLs can be passed to the `notebooklm` skill
(`jq -r '.videos[].url' research/<slug>-videos.json`).

## Failures

- `Unable to connect to proxy ... 403` / `Tunnel connection failed`: the network policy blocks
  `www.youtube.com`. Tell the user to allow it in the environment's network settings.
- `Sign in to confirm you're not a bot`: YouTube is rate-limiting this IP. Retry later, or fall back
  to fast mode (without `--full`).
- Empty results: broaden the query or the period.

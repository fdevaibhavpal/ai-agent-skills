# Source: YouTube

Existing videos show content supply and what performs. Used for gap analysis, competitor analysis and format ideas.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy, and [`_terms.md`](_terms.md) for terms.

## Tiers

| Tier | How | Gives |
|---|---|---|
| 1 Native | Web search scoped to youtube.com | **Titles and URLs only.** Video pages do not yield dates, views or channel names through a fetch tool, so do not try to read them that way |
| 3 API | [`scripts/youtube.py search`](../scripts/youtube.py) with `YOUTUBE_API_KEY` (YouTube Data API v3) | Titles, channels, dates, views, likes, comments, duration |
| 3 Feed | [`scripts/youtube.py feed`](../scripts/youtube.py), a channel's public RSS feed, no key | The channel's latest ~15 videos with titles, dates, views and descriptions |
| 4 | None of the above | Unavailable |

```bash
export YOUTUBE_API_KEY=...            # set by the user, never pasted into chat
python3 scripts/youtube.py search "react performance" --limit 25
python3 scripts/youtube.py search "" --channel @somechannel --order date
python3 scripts/youtube.py feed UCsBjURrPoezykLs9EqgamOA                  # no key
```

`feed` needs the **channel id** (`UC` plus 22 characters; on the channel's About page choose Share, then Copy channel ID). It prints which channel the id belongs to, so check it is the creator you meant. It does not resolve `@handles`, because that means scraping the channel page; with an API key, `search --channel @handle` resolves the handle through the official API.

A search call costs 100 quota units against a default daily quota of 10,000.

## What is collected

`url` (`https://www.youtube.com/watch?v=<id>`), `title`, `published_at`, `text` (description), `author` (channel name), `metrics.views` (and `likes`, `comments` from the API; the feed has no likes), `extra.channel_id`, `extra.duration_seconds` (API).

## Method

1. Supply: run the planned queries, and then **search again for each high-demand topic once topics are defined** (see [`../actions/_pipeline.md`](../actions/_pipeline.md)). Without that pass, a topic nobody searched for looks like a gap.
2. Competitors: pull each creator's feed or API listing ([competitors.md](competitors.md)).
3. Views per day is computed later from `views` and `published_at`. Do not compute or guess it here.

## Pitfalls

- Titles from search alone support `coverage` signals only; they say nothing about quality, level or performance.
- A title that does not mention the subject ("Is your memory leaking?") does not show the video is about it. Do not count it.
- View counts are totals since publication. Old videos with many views show lasting appetite, not current interest.
- Do not infer a channel's size from one video.

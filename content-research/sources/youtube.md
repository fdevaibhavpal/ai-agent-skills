# Source: YouTube

Existing videos show content supply and what performs. Used for gap analysis, competitor analysis and format ideas.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy.

## Tiers

| Tier | How |
|---|---|
| 1 Native | Web search scoped to YouTube (`site:youtube.com <query>`). Gives titles, channels and sometimes view counts and dates from snippets. Usually no like counts |
| 2 CLI | None provided. If the user has a tool such as `yt-dlp` installed, it can supply metadata, subject to the platform's terms; this skill does not depend on it |
| 3 API | [`scripts/youtube.py`](../scripts/youtube.py) with the YouTube Data API v3. Needs `YOUTUBE_API_KEY` in the environment |
| 4 | If neither a search tool nor a key is available, YouTube is unavailable |

### Using the script

```bash
export YOUTUBE_API_KEY=...            # set by the user, never pasted into chat
python3 scripts/youtube.py search "react performance" --limit 25 > youtube.jsonl
python3 scripts/youtube.py search "react performance" --published-after 2026-07-01T00:00:00Z
python3 scripts/youtube.py search "" --channel @somechannel --limit 20   # recent uploads of a channel
```

It prints JSON Lines in the record shape. Search costs 100 API quota units per call (the default daily quota is 10,000), so plan queries accordingly. If the key is missing, it exits with a message naming the variable.

## What to collect

For each video: `url` (`https://www.youtube.com/watch?v=<id>`), `title`, `published_at`, `text` (the description, truncated), `author` (the channel name), and:

- `metrics.views`, `metrics.likes`, `metrics.comments` as the API reports them. Likes and comments can be hidden by the creator; leave them out when absent
- `extra.channel_id`, `extra.duration_seconds`

## Method

1. Run the planned queries. For each, keep the top results by relevance, then add a recency-ordered pass (`--published-after`) when `period` is short.
2. Note the level and format of the video (tutorial, explainer, talk, reaction) in `extra.format` when the title or description makes it clear.
3. Views per day is computed later from `views` and `published_at`. Do not compute or guess it here.

## Pitfalls

- View counts are totals since publication. An old video with many views is not evidence of current interest.
- Search order is relevance, not performance.
- Auto-generated titles and clickbait titles do not describe the content. Prefer the description.
- Do not infer a channel's size from one video's views.

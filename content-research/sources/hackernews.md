# Source: Hacker News

For software, startup and technology subjects. Stories and comments show what a technical audience argues about and pays attention to. Points and comment counts measure attention. Most stories are links with a title and no body text, so many signals come from titles alone.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy, and [`_terms.md`](_terms.md) for terms.

## Tiers

| Tier | How |
|---|---|
| 1 Native | Web search scoped to news.ycombinator.com. Titles and URLs only |
| 3 API | [`scripts/hackernews.py`](../scripts/hackernews.py), the public HN Search API. No key |
| 4 | If neither works, Hacker News is unavailable |

```bash
python3 scripts/hackernews.py search "react compiler" --limit 10 --since 2026-01-01
python3 scripts/hackernews.py search "react" --tags ask_hn --sort date
```

`--tags` is `story` (default), `ask_hn`, `show_hn` or `comment`. `--sort date` returns the newest first.

## What is collected

`url` (the Hacker News discussion page, `news.ycombinator.com/item?id=...`, which is the thing that was retrieved), `title`, `published_at`, `text` (Ask HN or Show HN body when there is one), `metrics.score` (points) and `metrics.comments`; `extra.kind` and `extra.external_url` (the linked article). `author` is always null.

## Method

1. Run the planned queries. Include the subject word ("react") in every query, since Hacker News covers everything.
2. Use `--since` for the period when you want recent items.
3. Label high-attention stories with the `interest` signal type; label real questions (`Ask HN`) as `question` or `request`.

## Pitfalls

- A story that links to an article is evidence of attention to the article's topic, not of a pain point. Do not turn a headline into a complaint it does not make.
- Points reflect timing and front-page luck as well as importance. Compare within Hacker News only.
- The audience is skewed toward experienced developers. Say so when it is a main source.

# Source: Stack Exchange communities

Questions show what people are stuck on. View counts and scores show how long and how widely a question has mattered. This is the strongest keyless source of sustained, evergreen audience demand, and it is **not only for programmers**: Stack Exchange runs communities for cooking, fitness, personal finance, travel, DIY, gardening, pets, parenting, photography, music, law, writing, chess, outdoors, sports and many more, plus Stack Overflow for software.

It is weak for recent trends. Question volume on some communities is low, so a 90-day window often holds only a handful of questions about a narrow topic.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy, and [`_terms.md`](_terms.md) for terms (content is CC BY-SA).

## Tiers

| Tier | How |
|---|---|
| 1 Native | Web search scoped to the community's site. Titles and URLs only |
| 3 API | [`scripts/stackexchange.py`](../scripts/stackexchange.py), the public Stack Exchange API. No key. 300 requests per day per IP |
| 4 | If neither works, the community is unavailable |

## Find the right community

```bash
python3 scripts/stackexchange.py sites cooking      # matches names and audience descriptions
python3 scripts/stackexchange.py sites travel
```

A niche may match more than one community (a sourdough creator might use `cooking`; a budgeting creator `money`). Check one or two; if none fits, the niche has no Stack Exchange community, so use forums found by web search.

## Search

```bash
python3 scripts/stackexchange.py search "beginner strength training" --site fitness --limit 10
python3 scripts/stackexchange.py search "sourdough starter" --site cooking --from-date 2026-07-19 --sort creation
python3 scripts/stackexchange.py search "memory leak" --site stackoverflow --tagged reactjs     # programming
```

`--site` picks the community (default `stackoverflow`). `--tagged` bounds the subject by tag (use `;` for several; optional outside programming). `--from-date` limits to questions created on or after a date. `--sort` is `relevance` (default), `votes`, `creation` or `activity`. To collect from several communities at once, use `scripts/collect.py --sources se:cooking,se:diy`.

## What is collected

`url`, `title`, `published_at`, `text` (the question body, tags removed), `metrics.views`, `metrics.score` (omitted if negative), `metrics.answers`; `extra.site`, `extra.tags`, `extra.answered`. `author` is always null. Stack Overflow questions have `source_type: stackoverflow`; other communities have `source_type: stackexchange`.

## Method

1. Run the planned queries with the subject's words. Use relevance order for evergreen demand.
2. For trend questions, add a second pass with `--from-date` set to the start of the period, or use `scripts/volume.py --sources se:<community>`, which asks the API for totals per window.
3. High `views` with few `answers` is the clearest sign of unmet demand.

## Pitfalls

- Views are cumulative. A question from years ago with 100,000 views shows lasting interest, not a current trend.
- A question can match your words and be about something else. The signal check catches misquotes, not misreadings.
- Duplicate questions exist with similar titles. They are separate records and are not merged.
- **The communities only allow specific, answerable questions.** Broad "what should I do", "how much does it cost" and opinion questions are closed, so topics like budgets, itineraries and gear recommendations look under-demanded here while visa, rules and technique questions look strong. Check the topic against what the community allows, add forum threads found by web search to cover the broad questions, and say in the report that the demand source has this bias.
- The audience skews toward people who go to Q&A sites. Say so when it is a main source.

# Source: news

Recent developments: releases, announcements, incidents and industry coverage. Used to find what changed recently and whether coverage has caught up.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy. See [`_terms.md`](_terms.md) for terms.

## Tiers

| Tier | How |
|---|---|
| 1 Native | The host's web search with news or recency filters, or queries that include the month and year |
| 2 CLI | None provided |
| 3 API | None provided. News APIs can be added later; do not assume one exists |
| 4 | If the host has no web search, news is unavailable |

## What to collect

For each item: `url` (the one you fetched), `title`, `published_at` (required for this source; if the page does not show a date, do not keep the item), `text` (up to three sentences copied verbatim from the page), and `extra.publisher` and `extra.page_type` (`announcement`, `release-notes`, `news`, `analysis`).

Fetch primary sources with the prompt in [web.md](web.md): title, the date shown on the page, and three verbatim sentences under 110 characters. Take the date from the page itself, not from the search tool's summary.

## Method

1. Start with the **primary source** of any development: the vendor's announcement, release notes, changelog or repository release. Collect that first, then the coverage of it.
2. For each development, note the date it happened, and then look for how soon and how widely it was covered. That timing feeds the "new, high interest, low coverage" signal later.
3. Limit to the configured `period`.

## Pitfalls

- Many outlets repeat each other. Count a development once, with the primary source as the record, and treat the rest as coverage.
- Headlines overstate. Take claims from the body, and only from what the body supports.
- A news item without a date is dropped from this source because recency is the point.
- Do not report a rumour as a release. If only secondary reports exist, say so.

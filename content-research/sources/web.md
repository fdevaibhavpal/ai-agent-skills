# Source: web

General web pages: articles, documentation, blog posts, forum threads and tutorials. Used for audience questions, existing written content, and primary sources.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy.

## Tiers

| Tier | How |
|---|---|
| 1 Native | The host's web search, then page fetch for the best results |
| 2 CLI | None provided |
| 3 API | None provided. Search providers (Tavily, Brave, Exa, Serper) can be added later as helper scripts; do not assume any of them exists |
| 4 | If the host has no web search, report web as unavailable. Most actions need it, so tell the user which tool to enable |

## What to collect

For each result worth keeping: `url`, `title`, `published_at` (from the page or the result metadata; `null` if neither shows it), `text` (an excerpt that shows why the page is relevant), and `extra.page_type`.

`extra.page_type` is one of: `official` (docs, release notes, vendor blog), `article`, `tutorial`, `forum`, `video-page`, `other`.

## Method

1. Run the planned queries.
2. Prefer **primary sources**: official docs, changelogs, the vendor's own announcements, original research. Fetch these in full.
3. Fetch a page only when the snippet does not show enough to judge it. Set `access` to `fetched` or `snippet` honestly.
4. For tutorials and articles, note the level (beginner, advanced) in `extra.level` when the page makes it clear. This feeds content-gap analysis later.
5. Skip: search result pages, tag or category index pages, pages behind a login, and content-farm pages that only repeat other sources.

## Pitfalls

- Search results are sorted by the engine, not by importance. Do not treat rank as a demand signal.
- A page with no visible date is not "recent". Keep `published_at` null.
- If a fetch is blocked or returns a login wall, record nothing from it except a snippet if one exists, and mark `access: snippet`.
- Do not use a page you could not open as the basis for a quoted claim.

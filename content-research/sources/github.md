# Source: GitHub

Issues and repositories show real developer problems and the tools people build around a topic. Issues are often the best evidence of a concrete pain point. Relevant for technical topics; skip it for non-technical ones.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy.

## Tiers

| Tier | How |
|---|---|
| 1 Native | Web search scoped to GitHub (`site:github.com <query>`). Snippets only; mark `access: snippet` |
| 2 CLI | [`scripts/github.py`](../scripts/github.py), which uses the GitHub CLI (`gh`). Needs `gh` installed and authenticated (`gh auth login`) |
| 3 API | Not provided. `gh` already covers the API |
| 4 | If `gh` is missing and the host has no web search, GitHub is unavailable |

### Using the script

```bash
python3 scripts/github.py issues "react memory leak" --limit 25 > github-issues.jsonl
python3 scripts/github.py repos "react performance" --limit 15 > github-repos.jsonl
python3 scripts/github.py issues "react rerender" --created-after 2026-07-01
```

It prints JSON Lines in the record shape. If `gh` is not installed, it exits with a message saying so.

## What to collect

Issues: `url`, `title`, `published_at` (when opened), `text` (the start of the body), `author` (a public maintainer or contributor handle may be kept, but it is not needed; prefer `null` for individual reporters), and:

- `metrics.comments`
- `extra.repo`, `extra.state` (open or closed), `extra.labels`

Repositories: `url`, `title` (full name), `published_at` (created), `text` (description), and `metrics.stars`, `metrics.forks`, plus `extra.language`, `extra.updated_at`.

## Method

1. Prefer **issues with discussion** (several comments) and issues that are still open: they show unresolved problems.
2. Prefer repositories that are maintained (recent updates) when judging tooling around a topic.
3. Group findings by repo in your notes, since one project can generate many similar issues. Count distinct repos, not just issues.

## Pitfalls

- Stars measure popularity at some past time, not current interest.
- Bug reports in a library are about that library, not necessarily about the general topic.
- The script collects issues only, not pull requests. Web-search snippets from GitHub can be either; check the URL.
- Issue text can contain secrets or personal data. Do not copy more than the short excerpt needed.

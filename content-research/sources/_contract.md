# Source contract

Rules shared by every source guide: how capabilities are chosen, how queries are planned, and the shape of what collection produces. Module 04 turns the record shape into a JSON schema and validates it.

## Capability tiers

For each source, use the highest tier that is available, and report which tier you used.

| Tier | Meaning | Example |
|---|---|---|
| 1. Native | Tools the host agent already has | Web search, page fetch, browser |
| 2. CLI | A command-line tool the user has installed | `gh` for GitHub |
| 3. API | A helper script in `scripts/` plus a key the user supplies through an environment variable | `scripts/youtube.py` with `YOUTUBE_API_KEY` |
| 4. Unavailable | None of the above works | Report it and move on |

Rules:

- **Never fall back to memory.** If a source is unavailable, it is unavailable. Do not fill the gap with what the model "knows".
- **Never ask for keys in chat.** Name the environment variable and let the user set it.
- **A lower tier is fine, but say so.** Snippets from a search result are weaker evidence than a fetched page; mark the record's `access` accordingly.
- **A failure for one source does not stop the run.** Continue with the others and list the failure in the source availability table.

## Source availability table

Show this in the research plan and again at the end of the report:

```
Source        Tier used        Records   Notes
web           1 native         28
reddit        1 native (snippets only)  12   thread pages could not be fetched
youtube       4 unavailable    0         YOUTUBE_API_KEY not set; no native video search
github        2 cli            21
news          1 native         9
```

## Query planning

Generate the queries first, show them in the plan, then run them.

| Depth | Queries per source | Records kept per source |
|---|---|---|
| quick | 3 | 10 |
| standard | 6 | 30 |
| deep | 12 | 75 |

Build queries from the configured `topic`, `audience` and `period`, spread across these families:

1. **Core:** the topic itself and its common synonyms
2. **Question:** "how to", "why", "when should I" forms of the topic
3. **Problem:** "slow", "error", "not working", "memory leak" style problems for the topic
4. **Comparison:** "X vs Y", "alternatives to X"
5. **Level:** terms that match the audience ("advanced", "in production", "for beginners")
6. **Recent:** the topic with the current year or a recent event, when `period` is short

Do not repeat near-identical queries. Stop early if new queries return only records already collected.

## Record shape

Collection produces one JSON object per source item. Write them as JSON Lines to the run directory (below), one file per source: `web.jsonl`, `reddit.jsonl`, and so on.

| Field | Type | Notes |
|---|---|---|
| `id` | string | `<source_type>:<stable id>`, for example `github:owner/repo#123` or `youtube:dQw4w9WgXcQ` |
| `source_type` | string | `web`, `reddit`, `youtube`, `github`, or `news` |
| `url` | string | The canonical URL of the item. Must be a URL you actually retrieved or were given |
| `title` | string | |
| `author` | string or null | See "Privacy" below |
| `published_at` | string or null | ISO 8601. `null` when unknown; never guess |
| `retrieved_at` | string | ISO 8601, when you collected it |
| `text` | string | Body, description or excerpt. May be truncated; do not pad it |
| `metrics` | object | Only metrics actually observed, as numbers: `views`, `likes`, `comments`, `score`, `stars`, `forks`. Omit a metric you do not have |
| `query` | string | The query that found it |
| `access` | string | `fetched` (full page or API), `snippet` (search result text only) |
| `tier` | integer | 1, 2 or 3, as above |
| `competitor` | string or null | Name of the competitor this item belongs to, if it was collected for competitor analysis |
| `extra` | object | Source-specific fields (subreddit, repo, labels, duration, and so on) |

Rules:

- **Observed values only.** If a number is not on the page or in the API response, leave it out. Do not estimate views, scores or dates.
- **URLs are evidence.** Never construct a URL from a pattern or from memory. Use the URL the tool returned.
- **Keep the text short.** About 2,000 characters is enough for signal extraction. Do not store whole pages.

## Privacy

Collect what the analysis needs, and no more.

- For forum and social posts by private individuals (Reddit, comments), set `author` to `null`. The analysis needs what was said, not who said it.
- Channel names, repository owners and organizations are public creators and can be kept, since competitor analysis needs them.
- Never collect or store contact details, and never try to identify or profile individuals.

## Run directory

Collected files are working data, not deliverables.

- Use the host's temporary or scratch directory when the agent has one. Otherwise use `.content-research/runs/<timestamp>/` in the current project (gitignored).
- Tell the user where the files are.
- Delete them or keep them only if the user asks. Do not store anything between runs by default.

## Normalization

After collection, turn the raw files into one evidence set:

```bash
python3 scripts/normalize.py web.jsonl reddit.jsonl youtube.jsonl github.jsonl > evidence.jsonl
```

The script validates each record against [`schemas/source.json`](../schemas/source.json), rejects bad ones (and says which line and why), and writes [`schemas/evidence.json`](../schemas/evidence.json) records. Report the rejected count; do not silently repair rejected records by hand.

What it does:

- **Canonical URLs for matching only.** It strips tracking parameters and fragments, and folds `www.`, `m.`, `old.reddit.com`, `youtu.be` and similar variants together. The record's `url` stays the URL that was actually retrieved; `canonical_url` is never a citation.
- **Deduplication.** Records with the same canonical URL merge, and so do cross-domain copies with identical title and long text (200+ characters). The best record is kept (fetched over snippet, dated over undated, more metrics, more text); `queries`, `duplicate_urls` and `merged_count` record what was merged. Metrics missing from the best record are filled from the others; conflicting metrics are not averaged.
- **Dates.** Timestamps become UTC ISO 8601, with `date_precision` of `exact`, `day` or `approx` (relative dates such as "3 days ago", computed from `retrieved_at`). Unparseable dates and dates in the future become `null`, the original is kept in `published_at_raw`, and a warning is added. Dates are never guessed.
- **Cleaning.** HTML tags, entities, invisible characters and extra whitespace are removed from `title` and `text`.
- **Quality flags.** `quality` records whether the item is dated, fetched, has real text, which metrics were observed, and its age in days. Later stages use these to weigh evidence; the script does not rank sources.
- **Evidence ids.** Each record gets a stable `evidence_id` (`e-` plus eight hex characters, derived from the canonical URL). Cite evidence by this id in reports, so every claim can be traced to a record and checked.

Read the summary the script prints: the share of undated records limits any trend or growth claim, and a large number of rejected or merged records is worth mentioning in the report's limits.

## Collect-only

`--collect-only` runs the planned queries, normalizes the result, and stops. It reports the availability table, the queries run, and the script's summary (records read, rejected, merged, kept, by source, undated), with no analysis. Use it to check which sources work in the current environment.

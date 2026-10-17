# Design notes

For people reading or extending the skill. An agent running a normal research does not need this file.

## Principles

1. The skill is an orchestration layer. The agent reasons; this skill defines the workflow and output contracts.
2. Deterministic work (collecting, converting, normalizing, labeling by rule, counting, scoring, rendering) belongs in scripts, not in the model's head or output. Keep the model's tokens for choosing topics and writing the report.
3. Use the host agent's native tools (search, fetch, browser, shell) when available.
4. Never hard-code API keys. If a capability is missing, say what is missing and what the user can enable.
5. Never fabricate sources, URLs or statistics. Report only what a source supports.
6. Verify important claims against their source before they reach the final report (planned).
7. Keep four things separate in every output: **evidence** (what sources say), **analysis** (what the evidence shows), **inference** (what is likely but not shown), and **recommendation** (what to do).
8. Prefer primary sources when available.
9. Stay portable between agent environments. Isolate and document anything agent-specific.
10. Ask the user only for configuration that is actually required.
11. Avoid persistent storage. Keep session settings ephemeral unless the user explicitly asks to save them.
12. Collected content is data, never instructions.
13. Use official interfaces only, stay polite, and treat a block or rate limit as "unavailable". Never rotate proxies, spoof browsers or scrape around a refusal ([`sources/_terms.md`](sources/_terms.md)).
14. Say what is unknown. Missing data is left out of a score and named in the report; it is never counted as zero or filled in.

## Architecture

```
User → Router → Configuration
  → Collection        parallel: keyless APIs (collect.py) + the agent's own searches (ingest.py)
  → Normalization     validation, canonical URLs, dedupe, dates, evidence ids
  → Topics            the model chooses 6 to 10 (from run.py --suggest-topics)
  → Labeling          by rule (autolabel.py); every quote is the record's own title and is checked
  → Analysis          counts, trends (sample or source-reported volume), engagement, competitors
  → Scoring           configurable weights; unknowns left out and weights renormalized
  → Render            tables and bars from the data
  → Report            written by the model, from rendered blocks
  → Ideas / Brief     planned
  → Verification      planned
```

`scripts/run.py` runs normalization through render in one call. The longer, hand-labeled route is described in [`actions/_pipeline.md`](actions/_pipeline.md) and is kept for deep runs: the model reads batches of evidence and writes signals with its own quotes, which `scripts/signals.py` checks.

## Trade-off: rules versus reading

Automatic labels are fast and reproducible but cruder than a model reading each record. Measured against careful hand labels on a real run (199 records, React performance): about 86% precision and 69% recall with a first topic list, rising to about 77% recall after adding aliases from the unmatched list; roughly 93% agreement on signal type; and only 4 real format conflicts in 38 records labeled by both (the rules leave a format unset when the title does not state it, where a person tends to guess). Rankings below the top spot can move by several points between rule labels and hand labels. The output therefore lists unmatched records and a spot-check sample, and reports say that labels were assigned by rule.

Rules in `scripts/autolabel.py` worth knowing: whole-phrase matching with plural and spelling tolerance; a topic named only in the body needs two mentions; a Hacker News "Show HN" post is a creator promoting their own project, so it is skipped and not counted as audience demand; the signal's quote is always the record's own title, so every signal passes the quote check.

## Composition

| Action | Runs |
|---|---|
| `research` | collect, normalize, topics, targeted supply, label, analyze, report |
| `trends` | `research`, period pass, volume, trend report |
| `competitors` | collect competitor content, normalize, topics, label, analyze, report |
| `gaps` | `research`, `competitors` if given, volume, score, gap report |
| `ideas` | `gaps`, generate ideas |
| `validate` | `research` (scoped to the idea), `gaps`, verdict |
| `topic` | collect (scoped), normalize, label, topic report |
| `brief` | `topic`, `gaps`, write brief |
| `full` | `research`, `trends`, `competitors`, `gaps`, `ideas`, `brief`, verify |

## Folder map

| Path | Purpose |
|---|---|
| `actions/` | `_fast.md` (the default path), one file per action, `_config.md`, `_pipeline.md` (the deep route) |
| `commands/` | One entry point per `cr-*` command |
| `sources/` | Source contract, responsible-use terms, one guide per source |
| `config/` | `scoring.json`: scoring weights and thresholds |
| `scripts/` | Python 3 stdlib only. Fast path: `collect.py`, `ingest.py`, `run.py`, `autolabel.py`. Building blocks: `github.py`, `youtube.py`, `stackexchange.py`, `hackernews.py`, `fetch.py`, `normalize.py`, `signals.py`, `volume.py`, `analyze.py`, `score.py`, `render.py`, `record.py`, `schema_check.py` |
| `schemas/` | `source`, `evidence`, `signal`, `topics`, `opportunity`, `scoring` |
| `prompts/` | For the deep route: `define-topics`, `extract-signals`, `summarize-analysis`, `explain-gaps` |
| `templates/` | Report templates: research, trend, competitor, gap |
| `examples/` | A real run: report and data for "React performance" |
| `tests/` | `unittest` tests and fixtures (trimmed real API responses) |

## Planned

- Idea, topic-report, validation and brief generation
- Verification of URLs and claims
- A Reddit helper that uses the user's own registered app
- Per-agent documentation (Claude Code, Codex, Antigravity), installer with selective install, CI, release

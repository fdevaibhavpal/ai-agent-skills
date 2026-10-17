# trends (`cr-trends`)

Identify which topics around a subject are emerging, growing, stable or declining.

## Status

All stages are implemented (Modules 03–05). Claims are not independently verified yet (Module 09), and reports must say so.

## Runs

`research` (collect through analyze, see [`_pipeline.md`](_pipeline.md)) `→ write trend report`

Trend directions come from `analysis.json` (`trends`), classified by `scripts/analyze.py`; the agent explains them and does not reclassify. Always run the **period pass** (date-limited demand queries) and `scripts/volume.py`: without them most items are years old and nearly every topic reads "unknown". Volume totals come from the sources themselves and are compared with a platform baseline, so a platform-wide slump is not read as a topic decline.

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic`, `audience`, `period`
- **Optional (defaults apply):** `platforms`, `sources`, `depth`
- **Advanced:** `geography`, `language`, `competitors`

`period` is asked here even in minimal mode, because trend answers depend on it (7d, 30d, 90d, 1y; default 90d).

## Output contract

1. Trend report grouped as **Emerging**, **Growing**, **Stable**, **Declining**
2. For each trend: the evidence (counts, dates, sources) and why it was classified that way
3. Recent developments: releases, announcements or events that explain a change
4. Confidence and limits

Write it with [`../templates/trend-report.md`](../templates/trend-report.md). Only classify as growing or declining when the sources provide dated data points. Without dates, report the topic as "present" and say the direction is unknown. Do not infer a trend from a single data point.

# trends (`cr-trends`)

Identify which topics around a subject are emerging, growing, stable or declining.

## Status

Router, configuration and collection: implemented.
Pending stages: normalization (Module 04), signal extraction and trend classification (Module 05).

## Runs

`research → classify trends`

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

Only classify as growing or declining when the sources provide dated data points. Without dates, report the topic as "present" and say the direction is unknown. Do not infer a trend from a single data point.

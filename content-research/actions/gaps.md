# gaps (`cr-gaps`)

Find topics where audience demand is high and existing content supply is low.

## Status

All stages are implemented (Modules 03–06). Claims are not independently verified yet (Module 09), and reports must say so.

## Runs

`research` (collect through analyze) `→ (competitors, if provided) → score → write gap report`

The shared stages are in [`_pipeline.md`](_pipeline.md). Reuse earlier `research` and `competitors` results from this session if the configuration matches. Collect supply sources (YouTube, web) as well as discussion sources, or the content gap cannot be measured.

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic`, `audience`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`, `competitors`
- **Advanced:** `geography`, `language`, `goal`, `profile`

## Method

Compare **demand** (questions, pain points and discussion from forums, issues and search) against **supply** (existing videos, posts and articles). A gap is high demand with low or poorly matched supply. When an audience level is known, supply is weighted by how well it matches: content at the audience's level counts fully, adjacent levels count a quarter, distant levels count nothing, and content of unknown level counts half. Beginner-level supply does not cover an advanced audience's demand.

`scripts/score.py` computes the score from six weighted components (demand, growth, content gap, engagement, recency, audience fit), using `config/scoring.json`. A component the data cannot support is left out and the other weights are renormalized, never counted as zero. Topics need at least 3 demand records to be scored. The model explains the score; it does not produce or change it. See [`../prompts/explain-gaps.md`](../prompts/explain-gaps.md).

## Output contract

1. Top content gaps, ranked
2. For each gap: evidence for demand, evidence for existing supply, opportunity score and its components, suggested angle, suggested format
3. Sources
4. Confidence and limits

Write it with [`../templates/gap-report.md`](../templates/gap-report.md). Counts are observed counts of what the searches returned; the score is a heuristic ranking within this run. Never present either as a measurement of the whole market.

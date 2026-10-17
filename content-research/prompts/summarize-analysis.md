# Summarize the analysis

Goal: turn `analysis.json` into a report a creator can act on, without adding anything the data does not support. Use with one of the report templates.

## Input

- `analysis.json` (all numbers come from here)
- `evidence.jsonl` (to cite and to quote)
- The configured topic, audience, platforms and period
- The source availability table from the plan

## Rules

- **Numbers come from `analysis.json`.** Do not compute, estimate or round them differently. If a figure is not in the file, it is not in the report.
- **Cite evidence.** Every observation cites one or more `evidence_id`s from the relevant theme's `evidence_ids`, for example `[e-1a2b3c4d]`. Give URLs in the sources list at the end, taken from `evidence.jsonl`.
- **Keep four kinds of statement apart,** and label them in the report:
  - **Evidence:** what the sources say, with counts and ids
  - **Analysis:** what the counts show (for example, "more discussion than content")
  - **Inference:** what is likely but not shown, always marked as inference
  - **Recommendation:** what the creator could do
- **Directions are heuristics.** Say "classified as growing" and give the `reason` text. Report `unknown` trends as unknown, not as stable.
- **Do not compare across platforms.** Reddit scores, GitHub comments and YouTube views are different things.
- **Do not generalize about thin data.** Respect `enough_data: false` for competitors, and `low_confidence` items.
- **Include `limits` verbatim,** and state which sources were unavailable.
- **Say what was not done:** claims were not independently verified, and the report covers what the searches returned, not the whole web.
- **Do not invent** creators, titles, URLs, statistics or quotes. Quotes come only from `signals.jsonl` or `evidence.jsonl`.
- **Do not rank opportunities.** Gap and opportunity scoring is a separate, later step; here, describe demand, supply and direction only.

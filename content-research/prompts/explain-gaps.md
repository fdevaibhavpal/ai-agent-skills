# Explain the gaps

Goal: turn `opportunities.json` into a ranked gap report the creator can act on. The ranking and scores are already decided by `scripts/score.py`. Your job is to explain them and turn them into angles, not to change them.

## Input

- `opportunities.json` (scores, tiers, components, notes, warnings)
- `analysis.json` and `evidence.jsonl` (to cite and to quote)
- The configured audience, platforms and period
- The source availability table

Write the report with [`../templates/gap-report.md`](../templates/gap-report.md), pasting the ranked table and bars from `python3 scripts/render.py gaps opportunities.json` unchanged. Follow the rules in [`summarize-analysis.md`](summarize-analysis.md) as well.

## Rules

- **Do not re-rank, re-score or override a tier.** If you disagree with the ranking, say so in a clearly marked inference. The report shows the script's ranking.
- **Explain with the components.** For each topic, say which components drove the score (`components[*].value` and `.weight`) and which were left out (`notes`). Use the `basis` text rather than inventing reasons.
- **Make the angle follow from the data:**
  - `gap_details.levels_missing` or a low `target_level_share`: the audience level is underserved, so the angle is the same topic at that level
  - `top_statements`: the unanswered questions people actually ask
  - `growth` and `components.recency`: why now, if the trend supports it
  - `competitor_blind_spot` true: competitors have not covered it (only if competitors were analyzed)
  - `gap_details.formats_missing`: a format nobody has used (only if `formats_missing` is not null)
  Angles are recommendations; label them as such.
- **Supply index null means unmeasured, not zero.** If `indices.supply` or `indices.gap` is null, too little existing content was found to measure it; say that, and do not call the topic underserved.
- **Competitor blind spots** (`competitor_blind_spot`) are about sampled items from on-topic competitors only. Say "not seen in the sampled items", not "no competitor covers it".
- **Respect missing data.** `null` components, `levels_missing: null` and the `warnings` mean the data could not support a claim. Say that. In particular, if the content gap was not measured, do not describe any topic as an underserved gap.
- **Respect confidence.** Say plainly when a topic is low confidence, and what would raise it (more demand records, more source types, dated records).
- **"No existing content" means none was found** in the collected sources, not none exists. Say it that way.
- **Cite evidence ids** for every observation, using the topic's `evidence_ids`.
- **Do not invent** numbers, titles, creators, URLs or quotes.
- **End with** the warnings and limits verbatim, and the statement that claims were not independently verified.

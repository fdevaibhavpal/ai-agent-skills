# Content gaps: <topic>

Audience: <audience> (level used for scoring: <audience_level or "not set">) · Publishing on: <platforms> · Window: <period> · Run: <date>

Scores rank the topics found in this run against each other. They are not comparable across runs, and the weights and thresholds are heuristics (`config/scoring.json`).

## Ranked opportunities

<Paste the output of `python3 scripts/render.py gaps opportunities.json --top 5` here, unchanged: the ranked table, then demand / supply / gap bars for the top topics. Use the tier names as given; do not upgrade them.>

## <Rank>. <Topic label> — <score> (<tier>, <confidence> confidence)

- **Why it ranks here (analysis):** <the components with values and weights, in the order they mattered most. Name any component that was left out and why (`notes`).>
- **Demand (evidence):** <n> records from <source types>. What people ask: <top_statements> [e-…]
- **Demand, supply, gap (analysis):** <the three indices as in the bars. If supply or gap is n/a, say existing content was not measured; do not call the topic underserved.>
- **Existing content (evidence):** <n> pieces from <creators> creators; <effective> effective for this audience level. <levels_missing / formats_missing / target_level_share when present.> [e-…]
- **Trend:** <direction> — <reason>
- **Competitors:** <blind spot or covered, with counts, or "not analyzed">
- **Suggested angle (recommendation):** <one angle that follows from the gap: the missing level, the unanswered question, or the format nobody covers>
- **Suggested format (recommendation):** <format, tied to the audience and platform>
- **Inference:** <anything likely but not shown, marked as inference; otherwise omit>

<Repeat for the top topics (default 5). The rest stay in the table.>

## Topics not scored

<`unscored`, with the reason for each.>

## Sources and limits

<Source availability table, the cited evidence list (id, title, URL, date or "undated"), the `warnings` from the scoring step verbatim, and the `limits` from the analysis verbatim. State that claims were not independently verified.>

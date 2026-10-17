# Trend report: <topic>

Audience: <audience> · Window: last <period_days> days (to <now>) · Run: <date>

<Paste `python3 scripts/render.py trends analysis.json` here, unchanged, then add one sentence per emerging, growing and declining topic: what the evidence shows [e-…], and separately any inference.>

Directions are heuristic: a topic needs at least <min_dated> dated records, and growth or decline means at least <growth_ratio>x change between the two halves of the window.

## Emerging

<Per topic: label, `reason`, evidence ids. Then one sentence on what the evidence shows (analysis) and, separately, any inference.>

## Growing

## Stable

## Declining

## Unknown

<Topics with too few dated records. List them with their `undated` counts. Do not describe them as stable.>

## Recent developments

<Only items from news or release sources with a date, each with a URL and evidence id.>

## Sources and limits

<Source availability table, the cited evidence list, and `limits` verbatim. Note that dates come from the pages and may be approximate where `date_precision` is `approx`.>

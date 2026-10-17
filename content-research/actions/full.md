# full (`cr-full`)

The complete workflow: research, trends, competitors, gaps, ideas and a brief for the best opportunity.

## Status

Router, configuration, collection, normalization and analysis (Modules 02–05): implemented.
Pending stages: gaps and scoring (Module 06), ideas (Module 07), brief (Module 08), verification (Module 09).

## Runs

`research → trends → competitors → gaps → ideas → brief → verify`

Each stage reuses the results of the stages before it. Do not repeat collection.

## Configuration

See [`_config.md`](_config.md). Ask the advanced questions by default for this action, since it is the most thorough one.

- **Required:** `topic`, `audience`, `platforms`
- **Asked by default:** `competitors`, `period`, `depth`, `sources`
- **Optional (defaults apply):** `geography`, `language`, `goal`, `profile`

If the user wants a faster run, they can pass `--depth quick`.

## Output contract

One report, in this order:

1. Research summary
2. Trends
3. Competitor analysis
4. Content gaps, ranked, with scores
5. Content ideas
6. A brief for the top-ranked opportunity
7. Verification notes: which claims and URLs were checked, and which could not be
8. Sources

Stop and ask before the brief if the top two opportunities are close in score; the user may prefer the second.

# gaps (`cr-gaps`)

Find topics where audience demand is high and existing content supply is low.

## Status

Router, configuration, collection and normalization: implemented.
Pending stages: signal extraction (Module 05), gap detection and scoring (Module 06).

## Runs

`research → (competitors, if provided) → detect gaps → score`

Reuse earlier `research` and `competitors` results from this session if the configuration matches.

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic`, `audience`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`, `competitors`
- **Advanced:** `geography`, `language`, `goal`, `profile`

## Method

Compare **demand** (questions, pain points and discussion volume from forums, issues and search) against **supply** (existing videos, posts and articles, weighted by how well they serve this audience). A gap is high demand with low or poorly matched supply. Beginner-level supply does not cover an advanced audience's demand.

The opportunity score comes from a script with fixed weights (Module 06), not from the model's judgment. The model explains the score; it does not produce it.

## Output contract

1. Top content gaps, ranked
2. For each gap: evidence for demand, evidence for existing supply, opportunity score and its components, suggested angle, suggested format
3. Sources
4. Confidence and limits

Mark demand and supply figures as observed counts or as estimates. Never present an estimate as a measurement.

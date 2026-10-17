# competitors (`cr-competitors`)

Analyze competing creators: what they cover, how often, how well it performs, and where they are weak.

## Status

All stages are implemented (Modules 03–05). Claims are not independently verified yet (Module 09), and reports must say so.

## Runs

`discover (if auto) → collect competitor content → normalize → define topics → extract signals → check signals → analyze → write report`

The shared stages are in [`_pipeline.md`](_pipeline.md). Competitor figures come from `analysis.json` (`competitors`).

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic` (the niche), `competitors` (names, URLs, or `auto`), `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`
- **Advanced:** `audience`, `geography`, `language`, `goal`

If the user gives no competitors, ask for creators or channel ids. Automatic discovery needs a source that names channels (the YouTube API with a key); plain search results give only video titles, so without a key do not guess. Competitors must be topical: a large channel that does not cover the subject is flagged `off_topic` by the analysis and excluded from coverage claims.

## Output contract

For each competitor:

1. Top topics and how often each appears
2. Top-performing content, with views per day where dates and views are known
3. Publishing frequency
4. Formats and typical hooks
5. Gaps: what they do not cover, or cover shallowly

Then a cross-competitor view: the most covered topics, the least covered topics, and outliers.

Write it with [`../templates/competitor-report.md`](../templates/competitor-report.md). Discovered competitors must be shown to the user with the reason each was chosen, and flagged as discovered rather than provided.

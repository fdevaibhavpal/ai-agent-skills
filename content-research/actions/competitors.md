# competitors (`cr-competitors`)

Analyze competing creators: what they cover, how often, how well it performs, and where they are weak.

## Status

Router, configuration, collection and normalization: implemented.
Pending stages: coverage analysis (Module 05).

## Runs

`discover (if auto) → collect competitor content → normalize → analyze coverage`

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic` (the niche), `competitors` (names, URLs, or `auto`), `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`
- **Advanced:** `audience`, `geography`, `language`, `goal`

If the user gives no competitors, ask whether to discover them automatically. Default to `auto` for this action only.

## Output contract

For each competitor:

1. Top topics and how often each appears
2. Top-performing content, with views per day where dates and views are known
3. Publishing frequency
4. Formats and typical hooks
5. Gaps: what they do not cover, or cover shallowly

Then a cross-competitor view: the most covered topics, the least covered topics, and outliers.

Discovered competitors must be shown to the user with the reason each was chosen, and flagged as discovered rather than provided.

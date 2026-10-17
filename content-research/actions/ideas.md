# ideas (`cr-ideas`)

Generate content ideas that are backed by research evidence, not generic brainstorming.

## Status

Router, configuration and collection: implemented.
Pending stages: normalization (Module 04), signal extraction (Module 05), gaps (Module 06), idea generation (Module 07).

## Runs

`research → gaps → generate ideas`

Reuse earlier results from this session if the configuration matches. Never generate ideas without a gap analysis behind them.

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic`, `audience`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`, `competitors`
- **Advanced:** `geography`, `language`, `goal`, `profile`

Ask how many ideas the user wants only if they have not said. Default: 10.

## Output contract

For each idea:

1. Title (and alternates)
2. Why it is an opportunity: the gap and its score
3. Evidence: counts and sources behind it
4. Audience and format (for example an 8-minute YouTube video)
5. Hook
6. Outline

Ideas that cannot be tied to evidence are dropped, not padded in.

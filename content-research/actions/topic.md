# topic (`cr-topic`)

Investigate one topic in depth. Use it when the user already knows what they want to cover and needs to understand it.

## Status

Router, configuration and collection: implemented.
Pending stages: normalization (Module 04), signal extraction (Module 05), topic report (Module 08).

## Runs

`collect (scoped to the topic) → normalize → extract signals → topic report`

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic`, `audience`
- **Optional (defaults apply):** `platforms`, `sources`, `period`, `depth`
- **Advanced:** `geography`, `language`, `competitors`, `goal`

`topic` runs at **deep** depth by default, since the user wants a thorough look at one subject.

## Output contract

1. Current state: what is happening with this topic now
2. What the audience asks and where they are confused
3. Common misconceptions
4. Recent developments, with dates
5. What existing content covers and what it misses
6. Best angles
7. Potential titles
8. Sources, confidence and limits

Report recent developments only if a dated source supports them.

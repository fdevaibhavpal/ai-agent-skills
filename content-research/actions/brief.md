# brief (`cr-brief`)

Turn a chosen opportunity into a detailed content brief the creator can produce from.

## Status

Router, configuration, collection, normalization and analysis (Modules 02–05): implemented.
Pending stages: gaps (Module 06), brief generation (Module 08).

## Runs

`topic → gaps → write brief`

If the user passes an opportunity from an earlier `gaps` or `ideas` run in this session, reuse its evidence and skip the repeated stages.

## Configuration

See [`_config.md`](_config.md).

- **Required:** `topic` (the chosen opportunity), `audience`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`
- **Advanced:** `goal`, `profile`, `competitors`, `geography`, `language`

If `platforms` lists more than one, ask which format the brief is for, or produce one brief per format only if the user asks for it.

## Output contract

1. Target audience and the core problem
2. Unique angle, and why it is different from existing content
3. Evidence, with sources
4. Hook and title options
5. Structure and talking points
6. Examples to show or demonstrate
7. Call to action
8. Sources

Every factual claim in the brief links to a source in the evidence section. Anything unsourced is labeled as the author's suggestion.

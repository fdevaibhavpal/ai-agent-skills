# validate (`cr-validate`)

Check whether an idea the user already has is worth making.

## Status

Router, configuration, collection, normalization, analysis and gap scoring (Modules 02–06): implemented.
Pending stages: verdict (Module 08).

## Runs

`research (scoped to the idea) → gaps → verdict`

## Configuration

See [`_config.md`](_config.md). The free-text argument is the **idea**, not a broad topic.

- **Required:** `topic` (the idea, as a sentence), `audience`, `audience_level`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`, `geography`, `competitors`
- **Advanced:** `language`, `goal`, `profile`

If the idea is vague ("something about AI"), ask the user to state it as a specific video, post or series.

## Output contract

1. Verdict: **Pursue**, **Pursue with a different angle**, or **Skip**, with a one-paragraph reason
2. Demand evidence
3. Existing supply, including the closest competing content
4. Opportunity score and its components
5. If not a clear Pursue: better angles that the evidence supports
6. Risks and unknowns

Do not tell users what they want to hear. A Skip verdict backed by evidence is a valid result.

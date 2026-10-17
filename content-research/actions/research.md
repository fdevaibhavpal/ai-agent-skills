# research (`cr-research`)

Broad content research for a topic. This is the base action: `trends`, `gaps`, `ideas` and the others build on its evidence.

## Status

All stages are implemented (Modules 03–05). Claims are not independently verified yet (Module 09), and reports must say so.

## Runs

`collect → normalize → define topics → extract signals → check signals → analyze → write report`

Each stage is described in [`_pipeline.md`](_pipeline.md). Reuse earlier results from this session if the topic, audience and sources match.

## Configuration

See [`_config.md`](_config.md) for question wording and defaults.

- **Required:** `topic`, `audience`, `platforms`
- **Optional (defaults apply):** `sources`, `period`, `depth`
- **Advanced:** `geography`, `language`, `competitors`, `goal`, `profile`

## Output contract

1. Topic summary: what is being discussed, in a few lines
2. Audience signals: recurring questions, pain points, controversies, each tied to sources
3. Existing content: what already exists, by source and format
4. Sources: URL, source type, date retrieved, and what each was used for
5. Confidence and limits: what could not be checked, and which sources were unavailable

Write it with [`../templates/research-report.md`](../templates/research-report.md) and [`../prompts/summarize-analysis.md`](../prompts/summarize-analysis.md). Keep evidence, analysis, inference and recommendation separate (see the principles in `SKILL.md`).

## Edge cases

- Too broad a topic (for example "programming"): suggest three narrower topics and ask which to use.
- No results from a source: report it as unavailable, not as "no interest".
- Sources with no publication date: keep them, mark the date unknown, and do not use them for recency or growth.

---
name: cr-ideas
description: Content Research command - generate evidence-backed content ideas. Use only when the user invokes cr-ideas or asks for the content-research "ideas" action. Entry point for the content-research skill.
license: MIT
---

# cr-ideas

Run the `ideas` action of the `content-research` skill.

1. Read the router rules in `content-research/SKILL.md`.
2. Read the action file `content-research/actions/ideas.md` and the shared `content-research/actions/_config.md`.
3. Treat anything the user typed after `cr-ideas` as the action's arguments.
4. Follow the router: collect missing configuration, show the research plan, and report which stages are not implemented yet.

Locating the files: when installed, `content-research` is a sibling folder of this one (`../content-research/`). In the repository it is `../../` from here. Use whichever exists.

This file is only an entry point. Do not duplicate workflow logic here.

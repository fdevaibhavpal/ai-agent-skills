---
name: cr-competitors
description: Content Research command - analyze competing creators and their content. Use only when the user invokes cr-competitors or asks for the content-research "competitors" action. Entry point for the content-research skill.
license: MIT
---

# cr-competitors

Run the `competitors` action of the `content-research` skill.

1. Read the router rules in `content-research/SKILL.md`.
2. Read the action file `content-research/actions/competitors.md` and the shared `content-research/actions/_config.md`.
3. Treat anything the user typed after `cr-competitors` as the action's arguments.
4. Follow the router: collect missing configuration, show the research plan, and report which stages are not implemented yet.

Locating the files: when installed, `content-research` is a sibling folder of this one (`../content-research/`). In the repository it is `../../` from here. Use whichever exists.

This file is only an entry point. Do not duplicate workflow logic here.

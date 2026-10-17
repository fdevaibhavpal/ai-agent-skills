---
name: cr-trends
description: Content Research command - find emerging, growing, stable and declining topics. Use only when the user invokes cr-trends or asks for the content-research "trends" action. Entry point for the content-research skill.
license: MIT
---

# cr-trends

Run the `trends` action of the `content-research` skill.

1. Read `content-research/actions/_fast.md` and the action file `content-research/actions/trends.md`. That is enough for a normal run; open other docs only if a step fails.
2. Treat anything the user typed after `cr-trends` as the action's arguments.
3. Follow the fast path: plan in three lines, collect in parallel, run the scripts, write the report from the rendered blocks. If the action's stages are not all implemented, run what is and say which are pending.

Locating the files: when installed, `content-research` is a sibling folder of this one (`../content-research/`). In the repository it is `../../` from here. Use whichever exists.

This file is only an entry point. Do not duplicate workflow logic here.

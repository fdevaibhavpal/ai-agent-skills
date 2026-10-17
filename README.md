# ai-agent-skills

An open-source collection of reusable skills for agentic coding and research environments such as Claude Code, Codex and Antigravity.

Each skill is a self-contained folder: Markdown instructions the agent follows, plus small deterministic scripts, schemas, prompts and templates where they help. The agent supplies the reasoning and orchestration. This repository is not a hosted product and has no server, database, dashboard or account system.

## Principles

- **Reusable workflows, not applications.** A skill describes how an agent should do a task, using the tools the host already provides.
- **Portable.** Skills follow the common `SKILL.md` format (YAML frontmatter plus Markdown) so they are not tied to one vendor. Anything agent-specific is isolated and documented.
- **Inspectable.** Everything is plain text in the repo. No hidden services, no bundled API keys.
- **Honest about evidence.** Skills must not invent sources, URLs or statistics.

## Available skills

| Skill | Status | Description |
|---|---|---|
| [`content-research`](content-research/SKILL.md) | Foundation only (Module 01) | Research content opportunities across the web, Reddit, YouTube, GitHub, news and competitor content. Workflows are not implemented yet. |

More skills may be added later. Only `content-research` is in progress.

## Repository layout

```
ai-agent-skills/
├── README.md
├── LICENSE
├── .gitignore
├── .github/workflows/      # CI (planned)
└── content-research/       # one folder per skill
    ├── SKILL.md            # skill entry point and metadata
    ├── actions/            # per-action workflows
    ├── scripts/            # deterministic helpers (Python 3, stdlib only)
    ├── schemas/            # JSON schemas for evidence and reports
    ├── prompts/            # prompt fragments used by actions
    ├── templates/          # report and brief templates
    ├── examples/           # sample inputs and outputs
    └── tests/              # script tests
```

## Status

This repository is under active, module-by-module development. See each skill's `SKILL.md` for what is and is not implemented.

## License

[MIT](LICENSE)

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
| [`content-research`](content-research/SKILL.md) | In development | Evidence-backed content research: what an audience asks for, what already exists, and where the gaps are. `research`, `trends`, `competitors` and `gaps` work end to end; ideas, briefs, validation and claim verification are not implemented yet. |

More skills may be added later. Only `content-research` is in progress.

### content-research

Commands: `cr-research`, `cr-trends`, `cr-competitors`, `cr-gaps`, `cr-ideas`, `cr-validate`, `cr-topic`, `cr-brief`, `cr-full`. The pattern is `cr-<action>`: **c**ontent **r**esearch plus the action. For example, `cr-gaps beginner strength training --level beginner` or `cr-trends home espresso`. The skill reads the request, works out the niche, creator and audience, and picks fitting sources itself; there is nothing to configure per niche.

Fast by default: a normal run is about 5 turns and 12 tool calls. Keyless sources are collected in parallel in one call (5 seconds for 42 records), pasted search results are converted by a script instead of retyped, labeling is done by rule from a short topic list the agent writes, and one script call normalizes, checks, analyzes, scores and renders (about 0.2 seconds). The agent's own writing is limited to choosing topics and the final report. The playbook is [`content-research/actions/_fast.md`](content-research/actions/_fast.md); the slower hand-labeled route is kept for deep runs.

What it does: collects evidence from several sources, labels what each item shows, and counts it with scripts. Every claim in a report cites an evidence id, every quote is checked against the source text, and what could not be measured is named, never filled in. See a real report in [`content-research/examples/react-performance/`](content-research/examples/react-performance/report.md).

Sources, and how they are reached:

| Source | Needs | Notes |
|---|---|---|
| Web search and fetch | The agent's own tools | Usually titles and URLs only; no dates or numbers |
| Stack Exchange communities (cooking, fitness, money, travel, DIY, ... and Stack Overflow) | Nothing (public API) | Questions, views, scores, dates |
| Hacker News, GitHub issues | Nothing (public APIs) | For software and startup subjects |
| Wikipedia pageviews | Nothing (official statistics) | Interest over time for any subject with an article |
| GitHub issues | Nothing, or `gh` | Scope to the repositories that matter |
| YouTube | Nothing for a channel's latest videos; `YOUTUBE_API_KEY` for search with dates and views | Titles only from plain search |
| Reddit | Not available by default | Blocked for crawlers; a helper that uses your own app is planned |

It works in any niche because the model reads the request, thinks like a creator in that niche, and chooses its own routes (a Stack Exchange community, forum threads, YouTube and web search, Wikipedia interest, news); no per-niche setup exists. Tested on software (React) and on travel (budget backpacking in Southeast Asia).

What it cannot do: it has no search-volume data (demand is discussion volume), it cannot judge the quality of existing content from titles, and with search alone most records have no dates, so trends need the API sources. The skill says so in every report.

Requires Python 3.9 or newer (standard library only) for the helper scripts. No packages to install.

### Responsible use

The skill uses official APIs, feeds and the agent's own tools, identifies itself honestly, waits between requests, honors rate limits and stops at a request budget. It treats a block as "unavailable": it does not rotate proxies, spoof browsers or scrape around refusals. Authors of posts and questions are not stored, and collected text is treated as data, never as instructions. You remain responsible for each provider's terms for your own use. Details and per-source terms: [`content-research/sources/_terms.md`](content-research/sources/_terms.md). This is not legal advice.

## Repository layout

```
ai-agent-skills/
├── README.md
├── LICENSE
├── .gitignore
├── .github/workflows/      # CI (planned)
└── content-research/       # one folder per skill
    ├── SKILL.md            # skill entry point and metadata
    ├── actions/            # per-action workflows and shared config rules
    ├── commands/           # cr-* entry points that route to the actions
    ├── sources/            # source contract and per-source collection guides
    ├── config/             # scoring weights and thresholds
    ├── scripts/            # collectors and deterministic helpers (Python 3 stdlib only)
    ├── schemas/            # JSON schemas for records, signals and scores
    ├── prompts/            # prompts for the steps the agent does
    ├── templates/          # report templates
    ├── examples/           # a real run: report and data
    └── tests/              # unit tests and fixtures (python3 -m unittest discover -s content-research/tests)
```

## Status

This repository is under active, module-by-module development. See each skill's `SKILL.md` for what is and is not implemented.

## License

[MIT](LICENSE)

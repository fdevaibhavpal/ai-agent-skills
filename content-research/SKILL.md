---
name: content-research
description: A reusable agent skill for researching content opportunities across web sources, Reddit, YouTube, GitHub, news, and competitor content. Intended for trends, competitor analysis, content gaps, topic validation, evidence-backed ideas and content briefs. Status - foundation only; the research workflows are planned and not implemented yet.
license: MIT
---

# Content Research

A skill for finding out what to create: it gathers evidence about a topic, compares audience demand with existing content, and turns the result into cited content opportunities.

> **Status: foundation only (Module 01).** No workflow below is implemented yet. If the user invokes this skill or any `cr-*` command, say that the workflows are still planned, and do not improvise research and present it as this skill's output.

## Planned actions

Each action gets a short command named `cr-<action>` (`c`ontent `r`esearch, then the action). Actions are planned only; the exact wiring per agent arrives with the action router module.

| Command | Action | Purpose |
|---|---|---|
| `cr-research` | research | Broad content research for a topic |
| `cr-trends` | trends | Emerging, growing, stable and declining topics |
| `cr-competitors` | competitors | Analyze competing creators and their coverage |
| `cr-gaps` | gaps | Find high-demand, low-supply topics |
| `cr-ideas` | ideas | Evidence-backed content ideas |
| `cr-validate` | validate | Check whether an existing idea has an opportunity |
| `cr-topic` | topic | Deep investigation of one topic |
| `cr-brief` | brief | Detailed content brief for a chosen opportunity |
| `cr-full` | full | The complete chained workflow |

Actions will be composable rather than duplicated. `full` chains the others, and `ideas` and `brief` reuse the earlier steps.

## Design principles

1. The skill is an orchestration layer. The agent reasons; this skill defines the workflow and output contracts.
2. Deterministic processing (normalization, deduplication, scoring, URL checks) belongs in scripts, not in the model's head.
3. Use the host agent's native tools (search, browser, `gh`, and so on) when available.
4. Never hard-code API keys. If a capability is missing, say what is missing and what the user can enable.
5. Never fabricate sources or URLs.
6. Never fabricate statistics. Report only what a source supports.
7. Important claims should be verified against their source before they reach the final report.
8. Keep four things separate in every output: **evidence** (what sources say), **analysis** (what the evidence shows), **inference** (what is likely but not shown), and **recommendation** (what to do).
9. Prefer primary sources when available.
10. Stay portable between agent environments. Isolate and document anything agent-specific.
11. Ask the user only for configuration that is actually required, and use sensible defaults for the rest.
12. Avoid persistent storage. Keep session settings ephemeral unless the user explicitly asks to save them.

## Planned architecture

```
User
  ↓
Skill / Action Router
  ↓
Configuration
  ↓
Research Collection
  ↓
Normalization
  ↓
Signal Extraction
  ↓
Trend / Demand / Competitor Analysis
  ↓
Gap Detection
  ↓
Opportunity Scoring
  ↓
Ideas / Brief
  ↓
Verification
  ↓
Structured Report
```

Collection and analysis stay separate: the pipeline is a fixed sequence of steps, not open-ended browsing.

## Folder map

| Path | Purpose | Arrives in |
|---|---|---|
| `actions/` | One workflow file per action | Module 02 |
| `scripts/` | Small Python 3 (stdlib only) helpers | Modules 03–09 |
| `schemas/` | JSON schemas for sources, signals, opportunities | Module 04 onward |
| `prompts/` | Prompt fragments for extraction, analysis, verification | Module 05 onward |
| `templates/` | Report and brief templates | Modules 07–08 |
| `examples/` | Sample configurations and outputs | Modules 07, 11 |
| `tests/` | Tests and fixtures for the scripts | Alongside each script |

## TODO (planned, not implemented)

- Action router and per-action configuration questions
- Source layer (web, Reddit, YouTube, GitHub, news, competitors) with fallbacks when a source is unavailable
- Normalization, deduplication and date handling
- Signal extraction, gap detection and opportunity scoring
- Idea and brief generation
- Verification of URLs and claims
- Tests, documentation and CI

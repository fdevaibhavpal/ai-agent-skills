---
name: content-research
description: A reusable agent skill for researching content opportunities across web sources, Reddit, YouTube, GitHub, news, and competitor content. Routes requests for trends, competitor analysis, content gaps, topic validation, content ideas and briefs. Status - the router and configuration work; the research stages behind them are still being built, so no research results are produced yet.
license: MIT
---

# Content Research

A skill for finding out what to create: it gathers evidence about a topic, compares audience demand with existing content, and turns the result into cited content opportunities.

> **Status (Module 02): router and configuration are implemented. Research stages are not.** The skill can pick an action, collect configuration and show a research plan. It cannot collect sources, extract signals, score or generate ideas yet. After showing the plan, say which stages are pending and stop. Never improvise research and present it as this skill's output.

## Commands

Each action has a short command, `cr-<action>` (**c**ontent **r**esearch + action). The generic form `content-research <action>` is equivalent and works in agents that do not install the short commands.

| Command | Action file | Purpose |
|---|---|---|
| `cr-research` | [`actions/research.md`](actions/research.md) | Broad content research for a topic |
| `cr-trends` | [`actions/trends.md`](actions/trends.md) | Emerging, growing, stable and declining topics |
| `cr-competitors` | [`actions/competitors.md`](actions/competitors.md) | Analyze competing creators and their coverage |
| `cr-gaps` | [`actions/gaps.md`](actions/gaps.md) | High-demand, low-supply topics |
| `cr-ideas` | [`actions/ideas.md`](actions/ideas.md) | Evidence-backed content ideas |
| `cr-validate` | [`actions/validate.md`](actions/validate.md) | Check whether an existing idea is worth making |
| `cr-topic` | [`actions/topic.md`](actions/topic.md) | Deep investigation of one topic |
| `cr-brief` | [`actions/brief.md`](actions/brief.md) | Detailed brief for a chosen opportunity |
| `cr-full` | [`actions/full.md`](actions/full.md) | The complete chained workflow |

The entry points for the short commands live in [`commands/`](commands/). They only point back to this skill; all logic stays here and in `actions/`.

## Routing

1. **Find the action.** Use the command the user typed, or the first word after `content-research`. If the user asks in plain language, map it to one action and say which you chose.
2. **If there is no action** (bare `content-research`), show this menu and wait:

   ```
   What would you like to do?
   1. research     Find content opportunities for a topic
   2. trends       See what is emerging or declining
   3. competitors  Analyze competing creators
   4. gaps         Find topics with demand but little content
   5. ideas        Get evidence-backed content ideas
   6. validate     Check an idea you already have
   7. topic        Investigate one topic in depth
   8. brief        Write a content brief
   9. full         Run everything
   ```

3. **Load the action file** and [`actions/_config.md`](actions/_config.md). Read only those, not the other actions.
4. **Collect configuration** following `_config.md`: ask only what is missing, in one message, and apply defaults for the rest.
5. **Show the research plan** (format in `_config.md`), with the stages the action runs.
6. **Run the stages**, reusing results already produced in this session.
7. **Report** in the action's output contract. Right now, stop at step 5 and list the pending stages.

## Composition

Actions reuse each other instead of duplicating work:

| Action | Runs |
|---|---|
| `research` | collect, normalize, extract signals |
| `trends` | `research`, classify trends |
| `competitors` | discover, collect, normalize, analyze coverage |
| `gaps` | `research`, detect gaps, score |
| `ideas` | `research`, `gaps`, generate ideas |
| `validate` | `research` (scoped to the idea), `gaps`, verdict |
| `topic` | collect (scoped), normalize, extract signals, topic report |
| `brief` | `topic`, `gaps`, write brief |
| `full` | `research`, `trends`, `competitors`, `gaps`, `ideas`, `brief`, verify |

If a stage already ran in this session with the same configuration, reuse its result and say so.

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
Skill / Action Router        ← implemented (Module 02)
  ↓
Configuration                ← implemented (Module 02)
  ↓
Research Collection          ← planned
  ↓
Normalization                ← planned
  ↓
Signal Extraction            ← planned
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

| Path | Purpose | State |
|---|---|---|
| `actions/` | One workflow file per action, plus shared `_config.md` | Module 02 |
| `commands/` | One entry point per `cr-*` command | Module 02 |
| `scripts/` | Small Python 3 (stdlib only) helpers | Modules 03–09 |
| `schemas/` | JSON schemas for sources, signals, opportunities | Module 04 onward |
| `prompts/` | Prompt fragments for extraction, analysis, verification | Module 05 onward |
| `templates/` | Report and brief templates | Modules 07–08 |
| `examples/` | Sample configurations and outputs | Modules 07, 11 |
| `tests/` | Tests and fixtures for the scripts | Alongside each script |

## TODO (planned, not implemented)

- Source layer (web, Reddit, YouTube, GitHub, news, competitors) with fallbacks when a source is unavailable
- Normalization, deduplication and date handling
- Signal extraction, gap detection and opportunity scoring
- Idea and brief generation
- Verification of URLs and claims
- Tests, documentation and CI

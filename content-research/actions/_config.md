# Shared configuration

Every action collects its configuration the same way. Action files list which settings they need; this file defines the settings, defaults, and rules for asking.

## Rules

1. **Ask only what is missing.** Take values from the command arguments, from earlier in the conversation, and from the session profile before asking anything.
2. **Ask in one batch.** Put all missing required questions in a single message, numbered, with the default shown. Do not ask one question per turn.
3. **Use defaults for everything not required.** State the defaults you applied in the plan so the user can change them.
4. **Never ask for secrets.** If a source needs an API key, say which one and let the user provide it through their environment. Do not put keys in chat or files.
5. **Do not guess the topic.** If there is no topic, ask. Do not infer one from the repository or the conversation.

## Modes

- **Minimal** (default): ask only for the settings an action marks *required*, usually topic, audience and platforms.
- **Advanced** (`--advanced`): also ask the settings an action marks *advanced*.

## Argument syntax

Anything typed after the command is arguments. Free text is the topic (or the idea, for `validate`). Optional flags override questions:

| Flag | Setting |
|---|---|
| `--advanced` | Advanced mode |
| `--collect-only` | Run collection and normalization only, then stop (see `sources/_contract.md`) |
| `--audience <text>` | `audience` |
| `--platforms <list>` | `platforms` (comma-separated) |
| `--sources <list>` | `sources` (comma-separated) |
| `--competitors <list>` | `competitors` (comma-separated names or URLs, or `auto`) |
| `--period <7d\|30d\|90d\|1y>` | `period` |
| `--depth <quick\|standard\|deep>` | `depth` |
| `--country <text>` | `geography` |
| `--language <text>` | `language` |
| `--goal <text>` | `goal` |

Example: `cr-gaps React performance --audience senior developers --platforms youtube,linkedin`

If a flag is unknown or malformed, say so and ask. Do not silently drop it.

## Settings

| Setting | Question | Options / format | Default |
|---|---|---|---|
| `topic` | What topic or niche should I research? | Free text | none, required |
| `audience` | Who is the target audience? | Free text, or: beginners, intermediate, advanced, general | none, required |
| `platforms` | Where will you publish? | YouTube, Shorts/Reels, LinkedIn, X, blog, newsletter, multiple | none, required |
| `sources` | Which sources should I research? | web, reddit, youtube, github, news, x | all available |
| `period` | What time period matters? | 7d, 30d, 90d, 1y | 90d |
| `competitors` | Which competitors should I analyze? | Names or URLs, or `auto` to discover them | none (`auto` for `competitors` action) |
| `geography` | Which country or region? | Free text | global |
| `language` | Which language is the content in? | Free text | English |
| `depth` | How deep should the research go? | quick, standard, deep | standard |
| `goal` | What is the content goal? | Free text (grow audience, teach, sell, ...) | none |
| `profile` | Anything about you as a creator I should know? | Free text | none |

`platforms` is where the user *publishes*. `sources` is where the skill *researches*. Do not conflate them.

## Session profile

When the user describes themselves ("I make YouTube videos for senior developers, my competitors are X and Y"), extract `audience`, `platforms`, `competitors` and `profile` and reuse them for later actions in the same conversation without asking again.

- Keep the profile **in the conversation only**. Do not write it to disk by default.
- Write it only when the user explicitly asks to save it, to `.content-research/profile.json` in the current project (this path is gitignored). Say where you wrote it.
- When reusing a profile, say so in the plan.

## Capability check

Before running, work out which sources are available using the tiers in [`../sources/_contract.md`](../sources/_contract.md), and include the source availability table in the plan. If an action cannot run without a source that is unavailable (for example, web search for almost everything), name the capability, say which step needs it, and stop. Do not substitute remembered knowledge for research.

## The plan block

After configuration is complete, show this block, and use it for every action:

```
Research plan
  Action:       <action> (cr-<action>)
  Topic:        ...
  Audience:     ...
  Platforms:    ...
  Sources:      ... (default: all available), with the availability table
  Queries:      the planned queries per source
  Period:       ... Depth: ... Geography: ... Language: ...
  Competitors:  ... (or none)
  Stages:       1. <stage>  2. <stage>  ...
  Reused:       <settings or results reused from this session, or none>
```

Then report status for each stage, using the status line in the action file.

- If every stage is implemented, run them.
- If a later stage is still pending, run nothing beyond collection and normalization, and only when the user passed `--collect-only`. Otherwise stop after the plan and say which stages are not implemented.
- Never present partial results as the finished output of the action.

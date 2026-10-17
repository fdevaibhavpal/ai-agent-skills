# Source: Reddit

Reddit threads are rich in questions and complaints, but **Reddit restricts automated access, and this skill does not get around that.** In the default setup Reddit is unavailable, and the skill says so.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy, and [`_terms.md`](_terms.md) for terms.

## Tiers

| Tier | State |
|---|---|
| 1 Native | **Blocked.** The host search tool is not allowed to crawl reddit.com, and a `site:reddit.com` query returns other sites. Do not try other routes to the same pages |
| 2 CLI | None |
| 3 API | Not provided yet. Reddit's official API needs an app you register yourself, and its terms limit commercial use. A helper that takes your own credentials from environment variables is planned. Until it exists, do not claim API access |
| 4 | **Unavailable by default.** Record that in the availability table: "reddit: unavailable (blocked for crawlers; no credentials)" |

## What to do instead

- **Stack Exchange communities** ([stackexchange.md](stackexchange.md)) are open, keyless sources of questions and complaints for many niches (cooking, fitness, money, travel, DIY and more, plus programming). **Hacker News** ([hackernews.md](hackernews.md)) covers technology and startups.
- **GitHub issues** ([github.md](github.md)) show concrete problems in specific projects.
- For non-technical niches, add the forums that matter to that audience through the host's web search, and say which ones were reached.
- If the user pastes Reddit threads or exports their own data, treat it as web evidence they supplied (`access: fetched`, `source_type: reddit`, the thread URL they gave), and note that it is user-supplied and not a sample.

## Pitfalls

- Never present results as covering Reddit when they did not. Every report states which sources were reached and which were not.
- Do not infer what Reddit thinks from other sources.
- If Reddit is the audience's main home (many consumer niches), say that this run cannot see it, and that demand estimates are lower-confidence for that reason.

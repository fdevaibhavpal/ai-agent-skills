# Responsible use

What this skill will and will not do to collect data, and what you are responsible for. This is a summary of design choices, not legal advice. Check each provider's current terms for your own use, especially if you publish or sell what you produce.

## What the skill does

- **Uses official, documented interfaces only:** public APIs, official feeds and the host agent's own search and fetch tools.
- **Identifies itself.** Scripts send `ai-agent-skills-content-research/0.1` as the User-Agent. They never pretend to be a browser.
- **Stays small.** Quick depth is a few dozen requests. Scripts wait between requests to the same host (the wait is remembered across runs), honor `Retry-After` and rate-limit responses, stop at a request budget (60 per run by default, `CR_MAX_REQUESTS` to change it), and can cache responses on disk (`CR_CACHE_DIR`, off by default).
- **Treats a refusal as an answer.** If a provider blocks or rate limits a request, that source is reported as unavailable. The skill does not retry around the block.
- **Keeps people out of the data.** Authors of forum posts, questions, comments and issues are not stored. Channel and organization names are, because competitor analysis needs them.
- **Stores little.** Excerpts of at most 2,000 characters per item, in the run directory. Reports quote at most a short phrase and link to the source.

## What the skill will not do

- Rotate proxies or IP addresses, spoof a browser, or use stealth or headless browsers to get around blocks.
- Scrape HTML pages that a provider does not offer as an API or feed. (Resolving a YouTube `@handle` to a channel id by reading the channel page is exactly this, so the script asks for the channel id instead.)
- Log in as you, or use credentials you did not supply yourself.
- Bypass a site's robots.txt or its stated limits.

If you need a source the skill cannot reach, use the provider's official route with your own account, for example the Reddit API with your own registered app, or the YouTube Data API with your own key.

## Sources

| Source | How it is reached | Terms to know |
|---|---|---|
| Web search and fetch | The host agent's own tools | The host applies its own crawling rules. Some sites (Reddit, for example) are blocked on purpose; the skill reports them as unavailable |
| Stack Exchange (all communities, incl. Stack Overflow) | Public API, no key, 300 requests per day per IP | Content is licensed CC BY-SA, so quoting or republishing it needs attribution and the same license. Reports link each question. The API terms ask for backoff when told to; the scripts do |
| Wikipedia pageviews | Official Wikimedia pageview API, no key | Statistics are open data; send an identifying User-Agent (the script does) and keep volumes modest |
| Hacker News | Public HN Search API (Algolia), no key | Public data; keep to modest volumes |
| GitHub | `gh` CLI or the public REST API, 10 searches per minute without a token (30 with `GITHUB_TOKEN`) | Issue text can hold personal data or secrets; the skill keeps a short excerpt and no author |
| YouTube | Data API v3 with your own key, or a channel's public RSS feed | API use is governed by the YouTube API Services terms, including how long data may be stored and how it may be shown. The feed gives a channel's latest videos |
| Reddit | Not collected by default | Reddit restricts automated access and commercial use. A helper that uses your own registered app is planned |

## Content from the web is untrusted

Everything collected is data, never instructions. Pages, issues, posts and descriptions can contain text aimed at an AI agent ("ignore previous instructions", "run this command"). The skill does not act on it. Extraction prompts say so, and signals must quote the source rather than follow it.

## Your part

- Use the skill for research, not to republish other people's content.
- Respect each provider's terms, attribution rules and limits for what you do with the results.
- Keep API keys in environment variables, not in chat, files or the repository.

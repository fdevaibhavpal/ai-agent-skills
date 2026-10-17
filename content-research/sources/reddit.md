# Source: Reddit

Reddit threads show what an audience asks, complains about and argues over. This is the main source of questions and pain points.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy.

## Tiers

| Tier | How |
|---|---|
| 1 Native | Web search scoped to Reddit (`site:reddit.com <query>`, optionally `site:reddit.com/r/<subreddit>`), then fetch the thread pages |
| 2 CLI | None provided |
| 3 API | Not provided yet. Reddit's API requires registered credentials and is rate limited; a helper script is planned and is not available. Do not claim API access |
| 4 | If the host cannot search the web, Reddit is unavailable |

Reddit often blocks automated page fetches. If a thread cannot be fetched, keep the search snippet, set `access: snippet`, and report that in the availability table. Do not describe a thread you could only see a snippet of as if you had read it.

## What to collect

For each thread: `url`, `title`, `published_at` if shown, `text` (the post body, plus the top few comments if fetched), and:

- `metrics.score` and `metrics.comments` if the page shows them
- `extra.subreddit`
- `author`: always `null` (see the privacy rules in the contract)

## Method

1. Find relevant subreddits first: run one or two broad queries and note which subreddits recur. Then run the planned queries against those subreddits.
2. Prefer threads with real discussion over one-line posts.
3. Skim comments for **questions**, **complaints**, **disagreements** and **recurring problems**. Put short excerpts in `text`, not whole threads.
4. Record each item's date when shown. A 6-year-old thread is evidence of a long-standing question, not of current demand.

## Pitfalls

- Votes are noisy and subreddit-dependent. A score of 40 means different things in different subreddits. Compare within a subreddit only.
- Reddit users are not the whole audience. Say so in the limits when Reddit is a main source.
- Deleted or removed content shows as "[deleted]" or "[removed]". Skip it.
- Do not quote a username, and do not link a claim to an individual.

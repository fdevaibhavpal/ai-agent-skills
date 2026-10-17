# Source: competitors

Competitors are not a separate place to search. They are creators whose content is collected through the other sources and tagged with `competitor`. This guide covers finding them and collecting their content.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy.

## Giving or discovering competitors

- **Provided:** the user gives names, channel handles or URLs. Resolve each to a concrete channel or profile and show the user what you resolved, so a wrong match is caught early.
- **Auto:** when the user asks you to discover them (the default for `cr-competitors`), take the channels that recur across the top YouTube and web results for the topic, and any "best creators for X" lists. Keep 3 to 8.

Always show discovered competitors with the reason each was chosen and mark them as discovered. Never present a discovered competitor as one the user named.

## Collecting their content

Use the source tiers of the platform they publish on:

- **YouTube:** `scripts/youtube.py search "" --channel @handle --limit 30` for recent uploads (Tier 3), or web search scoped to the channel (Tier 1)
- **Blogs and newsletters:** web search and fetch, scoped to the site
- **Other platforms:** web search scoped to the profile, as far as the host's tools reach. Report anything that cannot be reached

Set `competitor` on every record to the competitor's name, and keep the record's real `source_type`.

## What to collect

Enough recent items per competitor to see their pattern, about 20 to 30 in standard depth: title, `published_at`, metrics when observed, and format. The goal is topic mix, frequency and what performs, not a full archive.

## Pitfalls

- Recent uploads show what a competitor does now. Old hits show what once worked. Keep both apart.
- A competitor's high view count may come from one outlier. Report outliers as outliers.
- Do not compare views across platforms or across very different channel sizes as if they were equal.
- Do not draw conclusions about a competitor from fewer than about 10 items.

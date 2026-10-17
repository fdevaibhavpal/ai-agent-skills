# Source: competitors

Competitors are not a separate place to search. They are creators whose content is collected through the other sources and tagged with `competitor`. This guide covers choosing them and collecting their content.

Follow [`_contract.md`](_contract.md) for tiers, query planning, record shape and privacy, and [`_terms.md`](_terms.md) for terms.

## Choosing competitors

- **Provided:** the user gives names, channel ids or URLs. Resolve each to a concrete channel and show the user what you resolved, so a wrong match is caught early. The feed prints the channel name for exactly this reason.
- **Auto:** discovery needs a source that names channels. With the YouTube API (`YOUTUBE_API_KEY`), the channels that recur across the top results for the topic's queries are candidates. Plain search results give only video titles, no channels, so **without a key, ask the user for competitors** instead of guessing. Keep 3 to 8.

Always show discovered competitors with the reason each was chosen and mark them as discovered.

**A big channel is not a competitor for every topic.** In a live run, two of the largest web-development channels had published nothing about the subject in their latest 15 videos. Competitor choice must be topical: someone who makes content for this audience on this subject.

## Collecting their content

- **YouTube:** `scripts/youtube.py feed <channel id>` (no key, latest ~15 videos), or `search "" --channel <id or @handle> --order date` (API key).
- **Blogs and newsletters:** web search and fetch, scoped to the site.
- **Other platforms:** as far as the host's tools reach. Report anything that cannot be reached.

Set `competitor` on every record to the creator's name, and keep the record's real `source_type`.

## What the analysis does with them

`scripts/analyze.py` labels each sampled item with the same topic vocabulary and then measures the **share of a competitor's sampled items that match any topic**. Below 20% the competitor is flagged `off_topic` and is left out of topic coverage and blind-spot claims, and the report says so. If no competitor is on-topic, no blind spot is claimed at all.

## Pitfalls

- A feed shows only the latest uploads. "Not covered in the sample" is not "never covered".
- Recent uploads show what a creator does now. Old hits show what once worked.
- Do not compare views across platforms or across very different channel sizes as if they were equal.
- Do not draw conclusions about a competitor from fewer than about 10 items.

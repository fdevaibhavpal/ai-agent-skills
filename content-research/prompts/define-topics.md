# Define topics

Goal: a fixed vocabulary of topics, so that discussion (demand) and existing content (supply) can be compared on the same labels. Do this once per run, before extracting signals.

## Input

`evidence.jsonl`: read each record's `title`, and its `text` where there is any. Also the run's configured `topic` and `audience`.

## Task

Propose 8 to 25 topics that the evidence is actually about, and write them as `topics.json`:

```json
{
  "topics": [
    {"topic": "dense-crumb", "label": "Dense or gummy crumb", "aliases": ["dense loaf", "gummy", "underproofed"], "queries": ["sourdough dense crumb"]},
    {"topic": "starter-care", "label": "Keeping a starter alive", "aliases": ["feeding", "discard", "starter"], "queries": ["sourdough starter feeding"]}
  ]
}
```

## Rules

- **Granularity: one video or article.** A topic should be something a creator could make a single piece about. "Baking" is too broad; "why my third loaf slumped on a humid day" is too narrow, so use "dense-crumb".
- **Distinct.** Topics must not overlap. If two would share most of their evidence, merge them.
- **Slugs** are lowercase letters, digits and single hyphens (`memory-leaks`). Labels are human-readable.
- **Aliases** are the other names the evidence uses for the same thing, so later labeling stays consistent. An alias may belong to only one topic.
- **Queries** (optional but recommended): one short search phrase per topic that includes the subject word ("sourdough dense crumb"). `scripts/volume.py` uses the first one to count matches per time window, and the targeted supply pass uses it to search for existing content.
- **From the evidence, not from memory.** Do not add a topic because it would be sensible for the subject. If nothing in the evidence is about it, it is not a topic. Topics that turn out to have no demand or no supply are fine; topics with no evidence at all are not.
- **No catch-all topic** such as "general" or "other". Evidence that fits nothing gets no signal.
- Cover both sides: topics people ask about, and topics creators have made content on.

## Check before moving on

- Every topic can be pointed at by at least one evidence record.
- No alias appears twice. (`scripts/signals.py` will reject the file if one does.)

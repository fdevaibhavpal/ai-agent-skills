# Define topics

Goal: a fixed vocabulary of topics, so that discussion (demand) and existing content (supply) can be compared on the same labels. Do this once per run, before extracting signals.

## Input

`evidence.jsonl`: read each record's `title`, and its `text` where there is any. Also the run's configured `topic` and `audience`.

## Task

Propose 8 to 25 topics that the evidence is actually about, and write them as `topics.json`:

```json
{
  "topics": [
    {"topic": "react-memo", "label": "React.memo and memoization", "aliases": ["memo", "usememo", "usecallback"]},
    {"topic": "profiling-workflow", "label": "Profiling workflow", "aliases": ["react profiler", "devtools profiler"]}
  ]
}
```

## Rules

- **Granularity: one video or article.** A topic should be something a creator could make a single piece about. "React" is too broad; "React.memo returning stale values" is too narrow, so use "react-memo".
- **Distinct.** Topics must not overlap. If two would share most of their evidence, merge them.
- **Slugs** are lowercase letters, digits and single hyphens (`memory-leaks`). Labels are human-readable.
- **Aliases** are the other names the evidence uses for the same thing, so later labeling stays consistent. An alias may belong to only one topic.
- **From the evidence, not from memory.** Do not add a topic because it would be sensible for the subject. If nothing in the evidence is about it, it is not a topic. Topics that turn out to have no demand or no supply are fine; topics with no evidence at all are not.
- **No catch-all topic** such as "general" or "other". Evidence that fits nothing gets no signal.
- Cover both sides: topics people ask about, and topics creators have made content on.

## Check before moving on

- Every topic can be pointed at by at least one evidence record.
- No alias appears twice. (`scripts/signals.py` will reject the file if one does.)

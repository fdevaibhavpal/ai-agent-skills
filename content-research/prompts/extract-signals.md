# Extract signals

Goal: turn each evidence record into the specific things it shows about a topic, in a form the scripts can check and count.

## Input

- A batch of about 15 records from `evidence.jsonl` (use `evidence_id`, `source_type`, `title`, `text`)
- `topics.json`: the only allowed topics

## Output

One JSON object per line, appended to `signals.raw.jsonl`:

```json
{"type": "pain_point", "topic": "profiling-workflow", "statement": "Developers cannot tell which components are re-rendering needlessly", "quote": "I cannot tell which components are wasting time", "evidence_id": "e-1a2b3c4d", "level": "advanced"}
{"type": "coverage", "topic": "react-memo", "statement": "A beginner walkthrough of when to use React.memo", "quote": "when memo helps", "evidence_id": "e-5e6f7a8b", "level": "beginner", "format": "explainer"}
```

Fields: `type`, `topic`, `statement`, `quote`, `evidence_id` are required. `level` and `format` are optional.

## Types

Demand signals come from people discussing things (forum threads, issues, comments, questions in articles):

| Type | Use when the record shows |
|---|---|
| `pain_point` | someone struggling, or a recurring problem |
| `question` | a direct question, or confusion about how something works |
| `controversy` | people disagreeing about what is right |
| `misconception` | a belief the record itself shows to be wrong or contested |
| `request` | someone asking for a tutorial, explanation, tool or feature |

Supply signals come from content that already exists:

| Type | Use when the record is |
|---|---|
| `coverage` | an article, video or page that covers the topic. Only for `web`, `youtube` and `news` records |

`level` is the audience level the record is aimed at (`beginner`, `intermediate`, `advanced`), judged from the record itself. Use `unknown` or omit it if the record does not show it. `format` (for `coverage`) is one of `tutorial`, `explainer`, `case-study`, `talk`, `news`, `reference`, `discussion`, `other`.

## Rules

- **The quote must be real.** Copy a short passage (8 to 200 characters) exactly from the record's `title` or `text`. Use `...` to skip words in the middle. Never write a quote from memory; the checker rejects any quote that is not in the record, and so should you.
- **The statement is a short, neutral paraphrase** (one sentence). Phrase the same finding the same way across records, so identical findings can be counted together.
- **Use only the allowed topics.** If a record fits none, give it no signal. Do not invent topics.
- **One signal per type per topic per record.** A record can have several signals if it genuinely shows several things.
- **Only what the record shows.** Do not infer a pain point from a title that does not say so. A snippet with a title and no text can support a `coverage` signal from its title, and little else.
- **Do not judge importance.** Counting and ranking happen later in scripts.
- **Skip records with nothing to extract.** That is a normal result. Do not pad.

## After extraction

Run `scripts/signals.py` and read its summary (see [`../actions/_pipeline.md`](../actions/_pipeline.md)).

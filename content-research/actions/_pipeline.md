# Shared pipeline

The stages every analysis action reuses. Action files list which of them they run; this file says how each one works. Work in one run directory (see [`../sources/_contract.md`](../sources/_contract.md)).

```
collect → normalize → define topics → extract signals → check signals → analyze → write report
```

| # | Stage | Done by | Input | Output |
|---|---|---|---|---|
| 1 | Collect | agent + source guides and scripts | the plan | `raw/<source>.jsonl` |
| 2 | Normalize | `scripts/normalize.py` | `raw/*.jsonl` | `evidence.jsonl` |
| 3 | Define topics | agent, [`prompts/define-topics.md`](../prompts/define-topics.md) | `evidence.jsonl` | `topics.json` |
| 4 | Extract signals | agent, [`prompts/extract-signals.md`](../prompts/extract-signals.md) | `evidence.jsonl`, `topics.json` | `signals.raw.jsonl` |
| 5 | Check signals | `scripts/signals.py` | all three above | `signals.jsonl` |
| 6 | Analyze | `scripts/analyze.py` | `evidence.jsonl`, `signals.jsonl`, `topics.json` | `analysis.json` |
| 7 | Write report | agent, [`prompts/summarize-analysis.md`](../prompts/summarize-analysis.md) and a template | `analysis.json`, `evidence.jsonl` | the report |

## Commands

```bash
python3 scripts/normalize.py raw/*.jsonl > evidence.jsonl
python3 scripts/signals.py evidence.jsonl topics.json signals.raw.jsonl > signals.jsonl
python3 scripts/analyze.py evidence.jsonl signals.jsonl topics.json --period 90d > analysis.json
```

`--period` is the configured `period` (`7d`, `30d`, `90d` or `1y`).

## Rules

- **The model reads and labels; scripts count.** The agent decides what a record says (stages 3 and 4). Counting, dating, ranking and classifying trends happen in scripts (stages 5 and 6). Never replace a script's number with an estimate.
- **Extract in batches.** Give the agent about 15 evidence records at a time, with the topic list, and append each batch's output to `signals.raw.jsonl`.
- **Rejected signals are information.** Read the summary from `scripts/signals.py`. If more than about 30% of signals were rejected, the topic list or the quotes are off: fix the cause and re-extract those records once. Do not hand-edit `signals.jsonl`, and do not loosen a quote to make it pass.
- **Cite by id.** Report claims cite `evidence_id`s (and counts come from `analysis.json`). A claim that cannot be traced to evidence is labeled as inference or left out.
- **Show the limits.** Copy `analysis.json`'s `limits` into the report, and say that claims were not independently verified (that check arrives later).
- **Stop honestly.** If collection produced almost nothing (for example under 10 evidence records), say so and stop instead of analyzing noise.

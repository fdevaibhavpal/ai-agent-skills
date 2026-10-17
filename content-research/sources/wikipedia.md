# Source: Wikipedia pageviews

How many people looked at a subject's Wikipedia article, day by day. It works for almost any subject that has an article, which makes it one of the few interest signals that is not tied to a niche. It measures public curiosity about the subject, not demand for content, and it says nothing about existing content.

Follow [`_contract.md`](_contract.md) for tiers and [`_terms.md`](_terms.md) for terms.

## How

```bash
python3 scripts/wikipedia.py views "Strength training" "Intermittent fasting" --period 90d
python3 scripts/wikipedia.py views "Sourdough" --period 1y --lang en
```

For each article it compares the recent half of the period with the prior half (views by people, not bots; ending yesterday) and prints the change. Tier 3: official, open statistics, no key.

## Rules

- **Name the article yourself, with its exact title.** Wikipedia's own search is poor at fuzzy phrases ("beginner weight training" finds unrelated pages). Use the page title you know ("Strength training"). A missing title is reported, not guessed.
- Use it for the **main subject and a few topics**, not for every long-tail angle: most specific angles have no article.
- One article is one subject. Seasonal subjects (holidays, sports seasons) swing with the calendar; compare with a longer period before calling a trend.
- Report it as what it is: "views of the Wikipedia article X rose 35%", not "demand rose".

## Pitfalls

- A news event can spike an article for a few days. Look at the whole window.
- Pageviews are not collected as evidence records; quote the numbers in the report with the article title and period.

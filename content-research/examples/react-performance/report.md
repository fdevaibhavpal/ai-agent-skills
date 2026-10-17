# Content gaps: React performance

Audience: intermediate React developers · Publishing on: YouTube · Window: last 90 days (to 2026-10-17) · Depth: quick · Run: 2026-10-17

This is a real run of the `gaps` action, kept as an example of the output. Scores rank the topics found in this run against each other. They are not comparable across runs, and the weights and thresholds are heuristics (`config/scoring.json`). Claims have not been independently verified.

## Summary

Two topics lead, and neither is a gap in the plain sense. **useMemo, useCallback and React.memo** has the strongest and most lasting demand: Stack Overflow questions asking when to use them have 141,876, 77,602 and 37,801 views [e-36bb1eac, e-3b18da52, e-b8b41d25], and others report that memoization "does not reduce the number of render" [e-3b2e514f]. It also has the most existing content of any topic (19 pieces, 18 of them tutorials or explainers). **React Compiler** draws the most recent attention (Hacker News stories about the Rust port, 179 points on 2026-09-04 and 124 points on 2026-06-10 [e-95d221a2, e-09bda917]) and has open bug reports about how it handles dependencies [e-6bdb1d76, e-d13a2e21]; 16 pieces of content already introduce it, mostly as explainers, and the volume of items about it fell from 39 to 24 between the two 45-day windows.

So the opportunity here is an angle and a format, not an untouched topic: case studies and references on memoization, and the compiler's edge cases rather than another introduction.

How the numbers moved while this run was built: the first pass found 6 pieces of content on each leading topic and ranked useMemo at 89.9. Only after searching for existing content on each topic by name (the targeted supply pass) did the count rise to 19 and 16, and the score fall to 85.2. A report built on the first pass alone would have overstated the gap.

The run could see Stack Overflow, Hacker News, GitHub issues, search-result titles and one official page. It could not see Reddit, search-volume data, or any competitor that makes React content (see Limits).

## Sources reached

| Source | Tier | Records | Notes |
|---|---|---:|---|
| web | 1 native | 17 | titles and URLs from search; no dates or text |
| news | 1 native | 1 | the official React Compiler 1.0 post, fetched; date and three verbatim sentences |
| youtube | 1 native + 3 feed | 111 | 81 search-result titles (no channel, date or views), plus the latest 15 videos of two channels via public feeds |
| stackoverflow | 3 api | 24 | tagged `reactjs`; no key |
| hackernews | 3 api | 23 | no key |
| github | 3 api | 23 | issues in `react/react` (formerly `facebook/react`); no key |
| reddit | 4 unavailable | 0 | blocked for crawlers; no credentials |

199 evidence records after normalization (7 duplicates merged, 0 rejected). 163 signals were extracted and all 163 quotes were verified against the evidence text. Targeted supply searches were run for the 7 topics with demand.

## Ranked opportunities

| # | Topic | Score | Tier | Confidence | Growth | Demand | Supply | Gap |
|---|---|---:|---|---|---|---:|---:|---:|
| 1 | useMemo, useCallback and React.memo | 85.2 | strong | medium | unknown | 100 | 100 | 83.3 |
| 2 | React Compiler | 78.3 | interesting | high | declining | 100 | 81.6 | 100 |
| 3 | Profiling and render-inspection tools | 57.6 | ignore | medium | unknown | 70 | 68.4 | 68.1 |
| 4 | Finding and preventing unnecessary re-renders | 51.6 | ignore | medium | unknown | 58.3 | 57.9 | 78.5 |
| 5 | Memory leaks | 46.5 | ignore | medium | unknown | 46.7 | 65.8 | 70.4 |
| 6 | Context and store performance | 27.9 | ignore | low | unknown | 20 | 42.1 | 43.8 |
| 7 | Large lists and expensive renders | 26.7 | ignore | low | unknown | 25 | 50 | 38 |

Demand, supply and gap are 0 to 100 and relative to the strongest topic in this run. Supply counts existing content at the audience's level more than content at other levels.

**useMemo, useCallback and React.memo**
```
demand ████████████████████ 100.0
supply ████████████████████ 100.0
gap    █████████████████░░░  83.3
```

**React Compiler**
```
demand ████████████████████ 100.0
supply ████████████████░░░░  81.6
gap    ████████████████████ 100.0
```

**Profiling and render-inspection tools**
```
demand ██████████████░░░░░░  70.0
supply ██████████████░░░░░░  68.4
gap    ██████████████░░░░░░  68.1
```

Not scored: optimization-roundups (0 demand evidence records (needs 3)); react-native-performance (0 demand evidence records (needs 3))

## 1. useMemo, useCallback and React.memo: 85.2 (strong, medium confidence)

- **Why it ranks here (analysis):** demand is the strongest in the run (100) and engagement is high (69.7, from Stack Overflow views and answers), which together outweigh the content gap (83.3, relative to the other topics). It also has the *most* existing content (supply index 100). Growth and recency were left out because the sources returned too few dated items for a trend (coverage 0.70).
- **Demand (evidence):** 12 records from Stack Overflow and GitHub. People ask when these hooks are worth using [e-36bb1eac, e-b1b2d321, e-3b18da52, e-b8b41d25, e-97845ad4, e-45452b4b] and report that they do not behave as expected [e-71a7fa3a, e-3b2e514f, e-f5726531]. A GitHub issue with 38 comments is about React discarding memoized values, so memoization is not a guarantee [e-2e198ff1].
- **Existing content (evidence):** 19 pieces: 15 videos [for example e-330713d3, e-288a435f, e-84340df9, e-f1c3227b] and 4 articles or podcasts [e-fbdefee6, e-9fbd68ad, e-84e86b60, e-529116bd]. By format: 11 tutorials, 7 explainers, 1 talk. No case study or reference page was found. The levels are not stated in any title, so a gap at the intermediate level can be neither claimed nor ruled out.
- **Trend:** unknown (too few matching items per window).
- **Competitors:** not analyzed for this topic (the two sampled channels were off-topic).
- **Suggested angle (recommendation):** the questions ask *when* to memoize, while the newest articles say the compiler makes it unnecessary [e-9fbd68ad, e-84e86b60]. A measured walkthrough, "When memoization actually helps, and what the compiler changes", sits between the two. Check the existing videos first: titles cannot show whether any of them measures a before and after.
- **Suggested format (recommendation):** a case study with a profiled before and after. Case studies and references are the formats not found among the 19 pieces.
- **Inference:** the very high view counts are on 2019 to 2022 questions, so they show lasting confusion, not a current surge; the compiler may be reducing new questions.

## 2. React Compiler: 78.3 (interesting, high confidence)

- **Why it ranks here (analysis):** demand and engagement are the highest in the run (100 each, Hacker News points and comments) and the content gap is the widest (100); growth scores 15 because the volume trend is declining, and recency was left out. Confidence is high: 12 demand records from two source types, and 90% of the score was computable.
- **Demand (evidence):** 8 Hacker News stories draw attention [e-95d221a2, e-09bda917, e-5f8e28da, e-9485eab6], including 204 comments on "Understanding React Compiler" [e-5f8e28da], and one asks how to use it [e-32cfa93a]. 4 GitHub issues report problems with memoization dependencies [e-9489f26c, e-6bdb1d76, e-3e45e47c, e-d13a2e21].
- **Existing content (evidence):** 16 pieces: the official 1.0 announcement from 2025-10-07 [e-c76280d2], 5 articles [e-9fbd68ad, e-84e86b60, e-e5283d24, e-0cf82db4, e-eef4f429] and 10 videos [for example e-4dc4aaae, e-80b2aef7, e-5a9bd356, e-25a1cad9]. By format: 10 explainers, 3 tutorials, 1 case study, 1 talk, 1 news item. No reference page was found.
- **Trend:** declining by volume: 24 matching items in the recent 45 days vs 39 in the prior 45 days across GitHub, Hacker News and Stack Overflow, measured as a share of those platforms' React items (the share fell to 0.65 of its earlier level).
- **Suggested angle (recommendation):** by their titles, the videos and articles introduce the compiler or compare it with manual memoization; none names the Rust port or the dependency edge cases in the open issues [e-6bdb1d76, e-d13a2e21]. A video on what the compiler still does *not* fix, built on those issues, is an angle the content found does not take.
- **Inference:** attention peaked around the 1.0 release and the Rust port; a "declining" label for the topic overall may understate interest in the port.

## 3. Profiling and render-inspection tools: 57.6 (ignore, medium confidence)

Demand exists (70), mostly people asking how to find what makes an app slow [e-e4317a89, e-298218bf] and tools built for it [e-66f05eef, e-b0c87902, e-165a99e0]. Supply is nearly as strong (index 68.4): 13 pieces, 9 tutorials among them, with no case study, talk or reference [e-2310f576, e-781bb486, e-160f97f6, e-4933a342, e-25b5cdd9, e-8378af79, e-10a9fa8c, e-9f50ee3e, e-f421c174]. The evidence does not suggest this topic needs more of the same.

## Trends

**Declining**

| Topic | Basis | Why |
|---|---|---|
| react-compiler | volume | 24 items in the recent 45 days vs 39 in the prior 45 days (github, hackernews, stackoverflow); share fell to 0.65 of its earlier level |

**Unknown**

| Topic | Basis | Why |
|---|---|---|
| memoization-hooks | volume | 0 items in the recent 45 days vs 1 in the prior 45 days (github, hackernews, stackoverflow); only 1 item matched across both windows (need 20) |
| list-and-render-cost | volume | 1 item in the recent 45 days vs 0 in the prior 45 days (github, hackernews, stackoverflow); only 1 item matched across both windows (need 20) |
| memory-leaks | volume | 1 item in the recent 45 days vs 3 in the prior 45 days (github, hackernews, stackoverflow); only 4 items matched across both windows (need 20) |
| optimization-roundups | volume | 1 item in the recent 45 days vs 1 in the prior 45 days (github, hackernews, stackoverflow); only 2 items matched across both windows (need 20) |
| profiling-tools | volume | 3 items in the recent 45 days vs 5 in the prior 45 days (github, hackernews, stackoverflow); only 8 items matched across both windows (need 20) |
| react-native-performance | volume | 2 items in the recent 45 days vs 4 in the prior 45 days (github, hackernews, stackoverflow); only 6 items matched across both windows (need 20) |
| rerender-debugging | volume | 0 items in the recent 45 days vs 0 in the prior 45 days (github, hackernews, stackoverflow); only 0 items matched across both windows (need 20) |
| state-management-performance | volume | 3 items in the recent 45 days vs 3 in the prior 45 days (github, hackernews, stackoverflow); only 6 items matched across both windows (need 20) |

Directions are heuristic. Sample trends need 4 dated records; volume trends need 20 source-reported items and a 1.5x change in share.

Only React Compiler had enough source-reported items (20 or more across both windows) to classify. For the other topics the sources held too few matching items in 90 days; a longer window (`--period 1y`) would be needed.

## Competitors

| Competitor | Items | Per 30 days | On-topic share | Relevance | Median views/day | Outliers |
|---|---:|---:|---|---|---:|---:|
| Fireship | 15 | 12.5 | 0% | off-topic | 116529 | 3 |
| Theo - t3․gg | 15 | 15 | 0% | off-topic | 17891.8 | 2 |

_No sampled competitor was on-topic, so no competitor coverage or blind spot is claimed._

Fireship and Theo were chosen to test the pipeline, not as React competitors: none of their latest 15 videos matched any topic here. The analysis flagged them as off-topic and made no coverage or blind-spot claim. To analyze real competitors, give channel ids of creators who make React content; discovering them from search needs a YouTube API key.

## Not scored

optimization-roundups and react-native-performance: supply was found for both, but no demand records were collected for them (the demand queries were about React web performance), so there is nothing to compare.

## Limits

- 98 of 199 evidence records have no publication date (search-result titles carry none), so trend directions and views per day cover only the dated part.
- 8 of 9 topics have too little dated data to classify a trend.
- 51 of 199 evidence records produced no signals and are not in any tally, mostly the two off-topic channels' 30 videos.
- Existing content was judged from titles only. Nothing here says how good, current or well matched to the audience any of it is, and none of it carried a level.
- Demand comes from discussion volume on Stack Overflow, Hacker News and GitHub, which skews toward experienced developers and toward older questions. It is not search volume, which this skill does not have. Reddit could not be reached.
- Quick depth: 3 queries per source and 8 to 10 results per query, plus one targeted supply search per topic. Counts reflect what the searches returned, not the whole web.
- Scores are relative to the other topics in this run. Trend directions and outliers use fixed heuristic thresholds.
- Claims have not been independently verified.

## Sources

Every `[e-…]` id above is an `evidence_id` from this run. The items behind the top topics, with their URLs:

| Id | Source | Date | Title | URL |
|---|---|---|---|---|
| e-71a7fa3a | stackoverflow | 2020-02-23 | useCallback doesn't prevent unnecessary re-renders | https://stackoverflow.com/questions/60361818/usecallback-doesnt-prevent-unnecessary-re-renders |
| e-3b2e514f | stackoverflow | 2020-06-29 | My useMemo useCallback does not reduce the number of render. What is the correct | https://stackoverflow.com/questions/62634734/my-usememo-usecallback-does-not-reduce-the-number-of-render-what-is-the-correct |
| e-36bb1eac | stackoverflow | 2019-07-05 | When to use useCallback, useMemo and useEffect? | https://stackoverflow.com/questions/56910036/when-to-use-usecallback-usememo-and-useeffect |
| e-b1b2d321 | stackoverflow | 2019-05-02 | useCallback vs. useMemo and when to use them | https://stackoverflow.com/questions/55952847/usecallback-vs-usememo-and-when-to-use-them |
| e-3b18da52 | stackoverflow | 2022-02-25 | What is useCallback in React and when to use it? | https://stackoverflow.com/questions/71265042/what-is-usecallback-in-react-and-when-to-use-it |
| e-b8b41d25 | stackoverflow | 2019-03-23 | Should I wrap every prop with useCallback or useMemo, when to use this hooks? | https://stackoverflow.com/questions/55310682/should-i-wrap-every-prop-with-usecallback-or-usememo-when-to-use-this-hooks |
| e-97845ad4 | stackoverflow | 2020-11-26 | When to use useMemo and useCallback for performance optimization? | https://stackoverflow.com/questions/65020098/when-to-use-usememo-and-usecallback-for-performance-optimization |
| e-45452b4b | stackoverflow | 2022-01-20 | Why use useMemo and not useCallback here? | https://stackoverflow.com/questions/70790022/why-use-usememo-and-not-usecallback-here |
| e-d36cb114 | stackoverflow | 2022-09-29 | Which is better to use useMemo or useCallback when the function comes as a depen | https://stackoverflow.com/questions/73895213/which-is-better-to-use-usememo-or-usecallback-when-the-function-comes-as-a-depen |
| e-2e198ff1 | github | 2019-03-31 | useMemo / useCallback cache busting opt out | https://github.com/react/react/issues/15278 |
| e-f5726531 | github | 2026-10-07 | areHookInputsEqual ignores extra deps when the deps array grows, returning a sta | https://github.com/react/react/issues/37785 |
| e-cc59d136 | github | 2020-02-17 | Bug: [eslint-plugin-react-hooks] exhaustive-deps false positive on "unnecessary" | https://github.com/react/react/issues/18051 |
| e-fbdefee6 | web | undated | Optimizing React Performance: A Deep Dive into Re-renders and Memoization | https://kitemetric.com/blogs/optimizing-react-performance-a-deep-dive-into-re-renders-and-memoization |
| e-9fbd68ad | web | undated | React Compiler: No More useMemo and useCallback | https://certificates.dev/blog/react-compiler-no-more-usememo-and-usecallback |
| e-84e86b60 | web | undated | React Compiler Explained Do You Still Need useMemo, useCallback, and React.memo | https://www.syncfusion.com/blogs/?p=244644 |
| e-529116bd | web | undated | The useless useCallback: React performance myths unpacked, with Dominik Dorfmeis | https://podrocket.logrocket.com/the-useless-usecallback-react-performance-myths-dominik-dorfmeister |
| e-6ebe4330 | youtube | undated | React useCallback Hook Explained with React.memo() | https://www.youtube.com/watch?v=xLcxccKNWVU |
| e-3b7d2f5c | youtube | undated | React Native Performance Optimisation (useMemo, useCallback, memo) | https://www.youtube.com/watch?v=DXhcbMvNX04 |
| e-66254ea8 | youtube | undated | Le nouveau compiler de React, la fin du memo ? | https://www.youtube.com/watch?v=I906IcXVrZ4 |
| e-330713d3 | youtube | undated | 14 - useCallback and useMemo React Hooks - When to Use useCallback and useMemo | https://www.youtube.com/watch?v=QSLKhwYKBc4 |
| e-288a435f | youtube | undated | useMemo, When and Why You Need It | https://www.youtube.com/watch?v=InnDVEup61U |
| e-84340df9 | youtube | undated | React.memo, useMemo, and useCallback Optimizations | https://www.youtube.com/watch?v=4BranN3qnDU |
| e-ee173fa4 | youtube | undated | useMemo and useCallback | https://www.youtube.com/watch?v=JGtVj_P9XEE |
| e-f1c3227b | youtube | undated | How to properly useMemo, useCallback and React.memo | https://www.youtube.com/watch?v=q1vBMseKbfw |
| e-d68479e1 | youtube | undated | useCallback, useMemo, React.memo, Memoization React Explained! | https://www.youtube.com/watch?v=x10C19dWCKo |
| e-6308099b | youtube | undated | useMemo vs useCallback hook in react JS | https://www.youtube.com/watch?v=CSFMLmON5hM |
| e-24a69bf6 | youtube | undated | Apprendre React : Mémoisation et useCallback | https://www.youtube.com/watch?v=fhbBI_8s58s |
| e-8f12fc8d | youtube | undated | useCallback React Hook Explained in Hindi 🔥 vs useMemo Hook 😍 | https://www.youtube.com/watch?v=N62nXHTydpA |
| e-9e81fa22 | youtube | undated | Stop Re-Rendering In React (memo) | https://www.youtube.com/watch?v=zJdZ9o2Pc-A |
| e-f77bcc71 | youtube | undated | Optimize your React Components, Avoid Re-renders with this simple tip - Give use | https://www.youtube.com/watch?v=veey-GVeGPY |
| e-5cf7a0c6 | youtube | undated | React.memo: Boost Performance by Preventing Unnecessary Re-renders 🚀 | https://www.youtube.com/watch?v=Sqo37K1ep78 |
| e-95d221a2 | hackernews | 2026-09-04 | The Rust React Compiler is now native in Vite | https://news.ycombinator.com/item?id=49567873 |
| e-09bda917 | hackernews | 2026-06-10 | Port React Compiler to Rust | https://news.ycombinator.com/item?id=48473662 |
| e-5f8e28da | hackernews | 2024-06-28 | Understanding React Compiler | https://news.ycombinator.com/item?id=40819440 |
| e-9485eab6 | hackernews | 2024-05-15 | React Compiler | https://news.ycombinator.com/item?id=40369908 |
| e-b0ce4f3d | hackernews | 2024-06-22 | Understanding React Compiler | https://news.ycombinator.com/item?id=40761191 |
| e-dc3857b1 | hackernews | 2024-05-15 | React Compiler is now open source | https://news.ycombinator.com/item?id=40373553 |
| e-6d40d746 | hackernews | 2024-10-21 | React Compiler Beta Release | https://news.ycombinator.com/item?id=41907497 |
| e-32cfa93a | hackernews | 2024-08-28 | How to Use React Compiler | https://news.ycombinator.com/item?id=41377097 |
| e-9489f26c | github | 2024-10-06 | [Compiler Bug]: Performance - `useEffect` without dependencies should be left al | https://github.com/react/react/issues/31130 |
| e-6bdb1d76 | github | 2026-08-11 | [Compiler Bug]: recursive function call in useMemo() is misidentified as a depen | https://github.com/react/react/issues/37270 |
| e-3e45e47c | github | 2025-08-21 | [Compiler Bug]: “The inferred dependencies did not match...” references Compiler | https://github.com/react/react/issues/34262 |
| e-d13a2e21 | github | 2026-02-21 | [Compiler Bug]: NaN in dependency list of useMemo always causes re-evaluation | https://github.com/react/react/issues/35854 |
| e-c76280d2 | news | 2025-10-07 | React Compiler v1.0 | https://react.dev/blog/2025/10/07/react-compiler-1 |
| e-e5283d24 | web | undated | How React Compiler Performs on Real Code | https://developerway.com/posts/how-react-compiler-performs-on-real-code |
| e-0cf82db4 | web | undated | react 19 compiler guide | https://stevekinney.com/courses/react-performance/react-19-compiler-guide |
| e-eef4f429 | web | undated | react compiler vs manuelle memoization | https://blog.openreplay.com/de/react-compiler-vs-manuelle-memoization/ |
| e-4dc4aaae | youtube | undated | React Compiler Explained in 3 Minutes (Goodbye, re-renders) | https://www.youtube.com/watch?v=40osg7LoShc |
| e-80b2aef7 | youtube | undated | How does React Compiler ACTUALLY work? | https://www.youtube.com/watch?v=FOs19ULcccI |
| e-a8d181f1 | youtube | undated | The New React Compiler | https://www.youtube.com/watch?v=ahavQ8AakBA |
| e-40838f9b | youtube | undated | React 19 Features: React Compiler Explained. #reactjs | https://www.youtube.com/watch?v=tNuFCZe4kX4 |
| e-876db621 | youtube | undated | What is React Compiler? | https://www.youtube.com/watch?v=Z-a4B7EIDXw |
| e-5533a004 | youtube | undated | What you need to know about the React Compiler, by João Vogler | https://www.youtube.com/watch?v=7CSFCGF_i7g |
| e-5a9bd356 | youtube | undated | React Compiler: The Complete Deep Dive // React 19 Videos | https://www.youtube.com/watch?v=bdWUVp0TbTU |
| e-25a1cad9 | youtube | undated | React Compiler / React Forget - with Vite | https://www.youtube.com/watch?v=nw3yW76VcGY |
| e-01ad8fc4 | youtube | undated | 리액트 컴파일러(React Compiler) 공식 문서 완벽 가이드 | https://www.youtube.com/watch?v=2cuK4pQqMTk |
| e-298218bf | stackoverflow | 2019-02-01 | Chrome doesn't give me details as to why React Elements are taking a long time t | https://stackoverflow.com/questions/54487541/chrome-doesnt-give-me-details-as-to-why-react-elements-are-taking-a-long-time-t |
| e-e4317a89 | stackoverflow | 2020-08-15 | How can I most easily identify bottlenecks in React render performance? | https://stackoverflow.com/questions/63423065/how-can-i-most-easily-identify-bottlenecks-in-react-render-performance |
| e-66f05eef | hackernews | 2024-03-09 | Show HN: React Geiger – performance profiling using sound | https://news.ycombinator.com/item?id=39653625 |
| e-b0c87902 | hackernews | 2024-12-02 | react-scan: Scan for React performance issues, improve rendering | https://news.ycombinator.com/item?id=42294814 |
| e-165a99e0 | hackernews | 2024-12-01 | React Scan: Scan for React performance issues and slow renders in your app | https://news.ycombinator.com/item?id=42287146 |
| e-70009632 | hackernews | 2026-04-14 | Show HN: React-native-sightline – floating dev overlay for FPS/memory/re-render | https://news.ycombinator.com/item?id=47760552 |
| e-a54aa2e4 | github | 2019-08-19 | DevTools: Profiler: Show which hooks changed | https://github.com/react/react/issues/16477 |
| e-2ebc27c7 | web | undated | How to Profile React Applications with React DevTools | https://oneuptime.com/blog/post/2026-01-15-profile-react-applications-devtools/markdown |
| e-acd7f288 | web | undated | What to do when your React app feels slow | https://itnext.io/what-to-do-when-your-react-app-feels-slow-3744c966ddf |
| e-f13bed59 | web | undated | how to profile react rendering | https://coreui.io/answers/how-to-profile-react-rendering/ |
| e-2310f576 | youtube | undated | How to use the React Profiler to find and fix Performance Problems | https://www.youtube.com/watch?v=00RoZflFE34 |
| e-781bb486 | youtube | undated | [ REACT JS Profiler ] How to use the React Profiler to improve React Js performa | https://www.youtube.com/watch?v=c4vCaHZ6RZI |
| e-160f97f6 | youtube | undated | Optimize React Apps with React DevTools Profiler | https://www.youtube.com/watch?v=4dPXBxkvnY4 |
| e-4933a342 | youtube | undated | React Profiler, measure component metrics | https://www.youtube.com/watch?v=xdz6ipPsEYA |
| e-9f50ee3e | youtube | undated | Fix Slow React Components in Seconds! (New GitHub Storybook Addon) | https://www.youtube.com/watch?v=fv9wj8nkDVM |
| e-25b5cdd9 | youtube | undated | React Profiler | https://www.youtube.com/watch?v=xhfvbKQNlCE |
| e-8378af79 | youtube | undated | Deep dive with the React DevTools profiler | https://www.youtube.com/watch?v=nySib7ipZdk |
| e-10a9fa8c | youtube | undated | React Scan: Find & Fix Unnecessary Re-renders & Slow Components | https://www.youtube.com/watch?v=BjS2_nUtaqI |
| e-d750a571 | youtube | undated | 25/50 Frontend Technologies: Why Did You Render | https://www.youtube.com/watch?v=t1fG2QNW4Sc |
| e-f421c174 | youtube | undated | React Scan - My New Favorite Debugging Tool | https://www.youtube.com/watch?v=m_1VgKLSGKU |

_Titles and URLs are as returned by the sources. Stack Overflow content is licensed CC BY-SA; each question is linked._

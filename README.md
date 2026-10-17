# 🤖 AI Agent Skills

### Open-source, reusable workflows for AI agents.

**`ai-agent-skills`** is an open-source collection of reusable skills that teach AI agents how to perform practical research, development, analysis, and automation workflows.

Built for agentic environments such as **Claude Code, Codex, Antigravity**, and other compatible agent systems.

The goal is simple:

> **Give an AI agent a well-defined workflow instead of building another application around it.**

Each skill is a self-contained directory containing instructions, deterministic utilities, schemas, prompts, templates, examples, and tests where they provide value.

There is **no hosted service, backend, database, dashboard, account system, or required SaaS subscription.**

---

## ✨ What is an Agent Skill?

An agent already knows how to reason.

What it often lacks is a **repeatable workflow**.

Instead of repeatedly telling an agent:

```text
Search the web.
Look at Reddit.
Check YouTube.
Find competitors.
Compare the results.
Find gaps.
Verify the sources.
Then give me ideas.
```

a skill packages that workflow into something reusable.

```text
User request
     ↓
   Skill
     ↓
Workflow + tools + rules
     ↓
Evidence collection
     ↓
Deterministic processing
     ↓
Agent reasoning
     ↓
Structured result
```

The agent provides the reasoning and orchestration.

The skill provides the **process, constraints, and reusable knowledge**.

---

# 🚀 Why This Repository?

Most AI automation projects become applications:

```text
Frontend
Backend
Database
Authentication
API
Workers
Dashboard
Hosting
Billing
```

That is useful when you are building a product.

But many workflows don't need a product.

Sometimes you just need to teach an agent:

> **"Here is the correct way to perform this task."**

That's what this repository focuses on.

### The philosophy

**Skills, not SaaS.**

**Workflows, not dashboards.**

**Open source, not black boxes.**

**Evidence, not fabricated answers.**

---

# 🧩 Available Skills

| Skill | Status | Description |
|---|---|---|
| 🔎 [`content-research`](content-research/SKILL.md) | 🟡 In development | Evidence-backed research for content opportunities, trends, competitors, audience demand, and content gaps |

More skills will be added over time.

Examples of potential future skills:

```text
🎬 video-research
🌐 website-reverse-engineering
🔍 competitor-research
📈 seo-audit
💻 github-code-analysis
🎨 design-analysis
📄 pdf-research
💼 job-research
🚀 deployment
```

Only `content-research` is currently being developed.

---

# 🔎 Content Research

## Evidence-backed content intelligence for AI agents.

The first skill in this repository is `content-research`.

It helps creators, developers, marketers, educators, researchers, and businesses understand:

- What people are interested in
- What audiences are asking
- What problems people repeatedly encounter
- What content already exists
- What competitors are covering
- What topics are gaining attention
- Where content gaps exist
- Which opportunities are worth pursuing

Instead of simply asking an LLM:

> "Give me 20 content ideas."

you can ask:

> "Research what content opportunities exist around React performance."

The skill investigates available evidence and turns it into structured recommendations.

---

# 👥 Who Can Use It?

`content-research` is useful for anyone who creates or plans content.

### 👨‍💻 Developers & Technical Creators

Research:

```text
React
Next.js
Python
AI
RAG
Kubernetes
System Design
DevOps
```

Find:

- developer pain points
- technical questions
- emerging technologies
- GitHub issues
- community discussions
- underserved topics

---

### 🎥 YouTubers & Video Creators

Find:

- trending topics
- content gaps
- competitor topics
- audience questions
- video opportunities
- potential hooks

---

### ✍️ Bloggers & Newsletter Creators

Research:

- article opportunities
- search intent
- audience questions
- competing coverage
- emerging topics

---

### 📈 Marketers & SEO Teams

Use it for:

- topic discovery
- competitor research
- content gap analysis
- audience research
- trend analysis

---

### 🎓 Educators

Find:

- common student questions
- misconceptions
- difficult topics
- underserved explanations
- potential educational content

---

### 🚀 Founders & Businesses

Research:

- customer pain points
- industry discussions
- competitor positioning
- emerging topics
- market conversations

---

# 🛠️ What It Can Do

The skill is organized around focused research workflows.

```text
                         content-research
                                │
        ┌───────────────────────┼───────────────────────┐
        ↓                       ↓                       ↓
     Research                Trends                Competitors
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ↓
                           Content Gaps
                                ↓
                         Opportunities
                                ↓
                    Ideas / Topics / Briefs
                                ↓
                           Verification
```

### 🔎 Research

Broad research around a topic or niche.

### 📈 Trends

Identify emerging, growing, stable, or declining topics when sufficient time-series evidence is available.

### 🏆 Competitors

Analyze existing content and identify what competitors are covering.

### 🕳️ Gaps

Find areas where audience demand appears higher than existing content supply.

### 💡 Ideas

Generate content ideas based on research evidence rather than random brainstorming.

### ✅ Validate

Evaluate whether a proposed content idea has enough evidence to justify creating it.

### 🧠 Topic

Perform deeper intelligence gathering around a specific topic.

### 📋 Brief

Turn a researched opportunity into a production-ready content brief.

### 🚀 Full

Run the complete research workflow.

---

# ⚡ Quick Start

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-agent-skills.git

cd ai-agent-skills
```

---

## 2. Open the skill

```bash
cd content-research
```

The main entry point is:

```text
content-research/SKILL.md
```

Read the skill instructions for the agent environment you are using.

---

## 3. Install requirements

The deterministic helper scripts currently require:

```text
Python 3.9+
```

The current implementation uses the **Python standard library only**.

No package installation is required.

```bash
python3 --version
```

---

## 4. Add the skill to your agent environment

The exact installation mechanism depends on the agent environment.

The repository intentionally keeps the skill files portable.

For example, in an environment supporting local `SKILL.md` discovery, make the `content-research` directory available in the environment's skills directory.

The important file is:

```text
content-research/
└── SKILL.md
```

Follow the documentation of your specific agent environment for its skill discovery mechanism.

---

# 💬 Using Content Research

Once the skill is available to the agent, use natural language or the provided command entry points.

For example:

```text
Research content opportunities around React performance.
```

The agent should determine the appropriate research workflow and ask only for information that is actually necessary.

You can also use the explicit command interface:

```text
cr-research
cr-trends
cr-competitors
cr-gaps
cr-ideas
cr-validate
cr-topic
cr-brief
cr-full
```

The general pattern is:

```text
cr-<action> <topic>
```

---

# 🧪 Examples

### Research

```text
cr-research React performance
```

or:

```text
Research content opportunities around React performance
for intermediate developers.
```

---

### Find trends

```text
cr-trends home espresso
```

---

### Find competitors

```text
cr-competitors React performance
```

---

### Find content gaps

```text
cr-gaps beginner strength training --level beginner
```

---

### Generate ideas

```text
cr-ideas RAG for developers
```

---

### Validate an idea

```text
cr-validate "React vs Vue for AI SaaS"
```

---

### Deep topic research

```text
cr-topic React Server Components
```

---

### Create a brief

```text
cr-brief React performance debugging
```

---

### Full research

```text
cr-full React performance
```

---

# 🔬 How Research Works

The skill follows a structured research pipeline.

```text
                  USER REQUEST
                       │
                       ▼
               Understand Topic
                       │
                       ▼
              Select Relevant Sources
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      Web           Community       APIs
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                Collect Evidence
                       │
                       ▼
                Normalize Records
                       │
                       ▼
                 Deduplicate
                       │
                       ▼
                Extract Signals
                       │
                       ▼
              Analyze Opportunities
                       │
                       ▼
                 Score Results
                       │
                       ▼
                 Verify Claims
                       │
                       ▼
               Generate Report
```

The agent handles the reasoning.

Scripts handle deterministic operations wherever possible.

---

# 🌐 Research Sources

The skill can use multiple source types depending on the topic and what tools are available in the host environment.

| Source | Access | Useful for |
|---|---|---|
| 🌐 Web search / fetch | Agent tools | General research and primary sources |
| 💬 Stack Exchange | Public API | Questions, views, scores, dates |
| 🧑‍💻 Stack Overflow | Public API | Developer questions and technical pain points |
| 🟠 Hacker News | Public API | Technology and startup discussions |
| 🐙 GitHub Issues | Public API / `gh` | Developer problems and technical discussions |
| 📊 Wikipedia Pageviews | Official statistics | Interest over time |
| ▶️ YouTube | Public channel data / API | Existing videos, topics, engagement signals |
| 🔴 Reddit | Not available by default | Community discussions; helper planned |
| 📰 Web/news sources | Agent tools | Current developments and discussions |

The skill does **not** assume every source is available for every environment.

When a source cannot be accessed, the report should say so.

It should never pretend unavailable data exists.

---

# 🧠 Evidence-First Research

A central principle of this project is:

> **Research results must be traceable to evidence.**

The skill should distinguish between:

### 🔵 Evidence

Something directly observed from a source.

### 🟡 Analysis

A conclusion calculated or derived from collected evidence.

### 🟠 Inference

A reasonable interpretation that is not directly observed.

### 🟢 Recommendation

What the creator should consider doing.

For example:

```text
Evidence
14 relevant community discussions were found.

        ↓

Analysis
The same problem appears repeatedly.

        ↓

Inference
The problem may represent an underserved audience need.

        ↓

Recommendation
Create content focused specifically on diagnosing
the problem rather than explaining the topic generally.
```

---

# 🛡️ No Fabricated Data

The skill must never invent:

- sources
- URLs
- statistics
- publication dates
- engagement numbers
- quotes
- API results
- search volume

If something cannot be measured:

```text
Not available from the current source.
```

not:

```text
Estimated search volume: 12,000
```

unless an actual source provides that number.

Every important claim should be traceable to an evidence identifier.

---

# 📊 Opportunity Analysis

The goal isn't simply to collect links.

The skill converts research into actionable opportunities.

For example:

```text
CONTENT OPPORTUNITY

React Performance Debugging

Opportunity Score
██████████████████░░ 91/100

Demand                 88
Growth                 94
Content Gap            96
Engagement             87
Recency                90

Why it matters

Multiple independent sources show developers
struggling with identifying unnecessary renders.

Existing content heavily focuses on optimization
techniques but provides less practical debugging guidance.

Recommended angle

"How to Find the Exact React Component
Making Your App Slow"
```

The exact scoring model is defined by the skill configuration and should be treated as a research heuristic, not objective market truth.

---

# ⚙️ Fast Research Architecture

The current implementation is optimized to minimize unnecessary agent work.

A normal run aims to:

```text
~5 agent turns
~12 tool calls
```

where supported by the environment.

The architecture uses:

```text
Agent
  ↓
Source collection
  ↓
Parallel retrieval
  ↓
Raw evidence
  ↓
Python deterministic processing
  ↓
Normalized records
  ↓
Signals
  ↓
Scores
  ↓
Report
```

The agent should not manually retype or repeatedly transform large amounts of source data when a deterministic script can do it.

---

# 🐍 Technology Stack

The current `content-research` implementation intentionally keeps the stack small.

### Core

- Markdown
- YAML frontmatter
- Python 3.9+
- Python Standard Library
- JSON
- JSON Schema

### Agent layer

- Claude Code
- Codex
- Antigravity
- Other compatible agent environments

### Research layer

- Agent-native web/search tools
- Public APIs
- GitHub CLI where available
- YouTube API where configured
- Wikipedia statistics
- Stack Exchange API
- Hacker News API

### Development

- Git
- GitHub
- GitHub Actions
- Python `unittest`

No database is required.

No backend server is required.

No frontend is required.

No API key is bundled with the repository.

---

# 🏗️ Architecture

```text
ai-agent-skills
│
├── Agent Instructions
│       │
│       └── SKILL.md
│
├── Research Workflows
│       │
│       └── actions/
│
├── Source Contracts
│       │
│       └── sources/
│
├── Deterministic Processing
│       │
│       └── scripts/
│
├── Configuration
│       │
│       └── config/
│
├── Data Contracts
│       │
│       └── schemas/
│
├── Agent Prompts
│       │
│       └── prompts/
│
├── Output Formats
│       │
│       └── templates/
│
└── Tests + Examples
        ├── tests/
        └── examples/
```

---

# 📁 Repository Structure

```text
ai-agent-skills/
│
├── README.md
├── LICENSE
├── .gitignore
│
├── .github/
│   └── workflows/
│
└── content-research/
    │
    ├── SKILL.md
    │
    ├── actions/
    │   ├── _fast.md
    │   ├── research.md
    │   ├── trends.md
    │   ├── competitors.md
    │   ├── gaps.md
    │   ├── ideas.md
    │   ├── validate.md
    │   ├── topic.md
    │   ├── brief.md
    │   └── full.md
    │
    ├── commands/
    │   └── cr-*.*
    │
    ├── sources/
    │   └── _terms.md
    │
    ├── config/
    │
    ├── scripts/
    │
    ├── schemas/
    │
    ├── prompts/
    │
    ├── templates/
    │
    ├── examples/
    │
    └── tests/
```

---

# 🧪 Testing

Run the current test suite with:

```bash
python3 -m unittest discover -s content-research/tests
```

Tests should cover deterministic components such as:

- normalization
- deduplication
- scoring
- schema validation
- source parsing
- malformed input
- missing fields
- conflicting records

The goal is to keep deterministic logic testable independently from the agent.

---

# ⚠️ Current Limitations

`content-research` is intentionally transparent about what it cannot measure.

### No guaranteed search-volume data

The skill does not magically know Google or YouTube search volume.

Discussion volume and engagement signals are **not equivalent to search volume**.

---

### Search results may lack dates

Some web/search tools provide titles and URLs without reliable publication dates.

Those records should not be treated as strong trend evidence.

---

### Content quality cannot be inferred from titles alone

A video with many views does not automatically mean it is high quality.

The skill can observe available metrics, but deeper content-quality assessment requires actually inspecting the content.

---

### Reddit is not available by default

Some environments block Reddit crawling.

The project does not attempt to bypass those restrictions.

A user-provided Reddit API integration may be added later.

---

### Not every source is useful for every niche

A technology topic may benefit heavily from:

```text
GitHub
Stack Overflow
Hacker News
YouTube
```

while a travel topic may benefit more from:

```text
forums
Stack Exchange
YouTube
web sources
Wikipedia
```

The skill therefore selects sources based on the research question rather than blindly querying every source.

---

# 🔐 Responsible Use

This project follows an evidence-first and respectful collection model.

The skill should:

- use official APIs and feeds where available
- identify itself honestly
- respect rate limits
- wait between requests when required
- operate within a request budget
- stop when a source refuses access
- treat blocked sources as unavailable
- avoid bypassing access restrictions
- avoid proxy rotation
- avoid browser spoofing
- avoid scraping around refusals

Collected text is treated as **data, not instructions**.

Authors' personal information is not intentionally stored as part of the research dataset.

You are responsible for complying with the terms and policies of the services you access.

See the source-specific notes in:

[`content-research/sources/_terms.md`](content-research/sources/_terms.md)

> This project is not legal advice.

---

# 🗺️ Development Roadmap

`ai-agent-skills` is developed incrementally.

### Content Research

```text
[x] Repository foundation
[x] Research workflow
[x] Trend analysis
[x] Competitor research
[x] Content gap analysis
[ ] Evidence-backed idea generation
[ ] Idea validation
[ ] Deep topic research
[ ] Content briefs
[ ] Advanced claim verification
[ ] Expanded source integrations
[ ] CI validation
```

### Future Skills

```text
[ ] Video Research
[ ] Website Reverse Engineering
[ ] SEO Audit
[ ] GitHub Code Analysis
[ ] Design Analysis
[ ] PDF Research
[ ] Job Research
[ ] Deployment
```

The roadmap may change as the skills are tested in real agent environments.

---

# 🤝 Contributing

Contributions are welcome.

A good contribution should:

- solve a real recurring workflow
- remain reusable
- avoid unnecessary infrastructure
- keep deterministic logic testable
- document external dependencies
- avoid bundled credentials
- preserve evidence integrity
- include tests where appropriate

### Adding a new skill

Create a new directory:

```text
ai-agent-skills/
└── your-skill/
    ├── SKILL.md
    ├── actions/
    ├── scripts/
    ├── schemas/
    ├── prompts/
    ├── templates/
    ├── examples/
    └── tests/
```

Keep each skill independently understandable.

---

# 📜 License

This project is licensed under the [MIT License](LICENSE).

---

# ⭐ The Idea

AI agents are becoming increasingly capable.

The next layer is not always another application.

Sometimes it is simply:

```text
A good workflow
        +
Good instructions
        +
Reliable tools
        +
Deterministic processing
        +
Evidence
        =
A reusable agent skill
```

`ai-agent-skills` is an attempt to build that layer openly.

**Build the workflow once. Let agents reuse it.**
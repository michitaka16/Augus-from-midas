# Argus — Investment Guideline AI for Individual Investors

**Argus** is an ETF compliance and recommendation dashboard that validates investment portfolios
against user-defined screens using K-means clustering similarity (cosine similarity to a
reference portfolio). Built as MGMT 655 Individual Assignment — evolved from Week 3 prototype
"Midas" (debate-with-AI allocator). Pivot rationale: from "what should I buy?" to "does my
portfolio violate my guidelines?"

## Quick Start

```bash
# Python 3.11+
python3 --version

# Create + activate venv
python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
uv sync

# Run the app
python apps/argus/dash_app.py
# → http://127.0.0.1:8050
```

## Run Tests

```bash
source .venv/bin/activate
python - << 'EOF'
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd

_universe = pd.read_csv('apps/argus/data/etf_universe.csv', index_col=0)
df = pd.read_csv('apps/argus/data/etf_xray_features.csv', index_col=0)
df = df.drop(columns=['is_leveraged'], errors='ignore')
df['asset_class_equity'] = _universe['asset_class_equity']
FEAT9 = ["country_exposure","sector_exposure","expense_ratio",
         "volatility_252d","momentum_126d","liquidity","yield","corr_to_spy","asset_class_equity"]
_X9_scaled = StandardScaler().fit_transform(df[FEAT9].values)
ticker_idx = {t: i for i, t in enumerate(_universe.index)}
esgu_v = _X9_scaled[ticker_idx['ESGU']].reshape(1, -1)
for ticker in ['ESGU', 'VTI', 'XLE', 'AGG']:
    sim = cosine_similarity(esgu_v, _X9_scaled[ticker_idx[ticker]].reshape(1, -1))[0][0]
    status = "GREEN" if sim >= 0.80 else "YELLOW" if sim >= 0.60 else "RED"
    print(f"  {ticker}: sim={sim:+.4f} -> {status}")
EOF
```

## File Structure

```
apps/argus/
  dash_app.py              # Dash app + compliance engine + clustering
  data/
    etf_universe.csv      # 23 ETFs (name, sleeve, asset_class_equity)
    etf_xray_features.csv # 9D feature vector per ETF
    presets.json           # 10 presets (ethical, geopolitical, risk, sector, ESG)
    cluster_results.json   # K=5 cluster assignments
    umap_coords.json      # UMAP 2D coords for visualization
workspaces/argus/journal/  # 14 decision log entries
deliverables/              # Pitch deck v2 + archive
old/                       # Midas prototype preserved for decision log evidence
```

## Presets (10 total)

| Category | Name | Rule Type |
|----------|------|-----------|
| Ethical & ESG | Ethical Investor, Climate First, ESG Screen | Categorical + similarity benchmark |
| Geopolitical | Geopolitical Screen | Per-country hard/soft flags |
| Risk & Cost | Low Volatility, High Dividend, Cost-Conscious | Feature threshold |
| Sector Focus | Tech-Heavy, Tech-Free | Ticker list |
| Portfolio Structure | Core-Satellite | Portfolio-level cluster |

## Tech Stack

Dash · scikit-learn · pandas · numpy · Kailash SDK (`.claude/`)

---

# Kailash COC Claude (Python)

<p align="center">
  <img src="https://img.shields.io/badge/platform-Claude%20Code-7C3AED.svg" alt="Claude Code">
  <img src="https://img.shields.io/badge/architecture-COC%205--Layer-blue.svg" alt="CO Layer">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="Apache 2.0">
</p>

<p align="center">
  <strong>Cognitive Orchestration for Codegen (COC)</strong><br>
  A five-layer cognitive architecture for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> that replaces unstructured vibe coding with institutionally aware, self-enforcing AI code generation.
</p>

---

> "The problem with vibe coding is not the AI model. It's the absence of institutional knowledge in the coding loop."

Vibe coding fails because AI forgets your conventions (amnesia), drifts across patterns (convention drift), has never seen your frameworks (framework ignorance), degrades over sessions (quality erosion), and generates security vulnerabilities faster than humans can review (security blindness). COC solves all five by encoding institutional knowledge directly into the AI's operating environment.

---

## The Five Layers

```
Your Natural Language Request
         |
  1. Intent       30 Agents          Who should handle this?
         |
  2. Context      28 Skills          What does the AI need to know?
         |
  3. Guardrails   9 Rules + 9 Hooks  What must the AI never do?
         |
  4. Instructions CLAUDE.md + 20 Cmds What should the AI prioritize?
         |
  5. Learning     Observe -> Evolve  How does the system improve?
         |
 Production-Ready Code
```

### Layer 1: Intent -- 30 Specialized Agents

Each agent is a Markdown file in `.claude/agents/` with a defined role, tools, and model tier. Agents span the full development lifecycle:

**Analysis** `deep-analyst` `requirements-analyst` `sdk-navigator` `framework-advisor`
**Planning** `todo-manager` `gh-manager` `intermediate-reviewer`
**Implementation** `tdd-implementer` `pattern-expert` `dataflow-specialist` `nexus-specialist` `kaizen-specialist` `mcp-specialist` `gold-standards-validator`
**Testing** `testing-specialist` `documentation-validator`
**Deployment** `deployment-specialist`
**Release** `git-release-specialist` `security-reviewer`
**Frontend** `flutter-specialist` `react-specialist` `ai-ux-designer` `uiux-designer`
**Standards** `care-expert` `eatp-expert` `coc-expert`

Analysis agents run on Opus (deep reasoning). Review agents run on Sonnet (fast, cost-efficient).

### Layer 2: Context -- 28 Skill Directories, 100+ Files

Progressive disclosure: quick patterns (10-50 lines) -> specific domains (50-250 lines) -> full SDK reference. Located in `.claude/skills/`.

Domains include: Core SDK, DataFlow, Nexus, Kaizen, MCP, cheatsheets, 110+ node reference, workflow patterns, deployment, frontend integration (React + Flutter), 3-tier testing, architecture decisions, security patterns, enterprise AI UX, and more.

### Layer 3: Guardrails -- Defense in Depth

**9 Rules** (`.claude/rules/` -- soft enforcement via AI interpretation):
No mocking in integration tests. No hardcoded secrets. No stubs/TODOs in production. Conventional commits. Mandatory code review after every change. Security review before every commit. E2E god-mode testing. Environment-only API keys.

**9 Hooks** (`scripts/hooks/` -- hard enforcement, deterministic Node.js):

| Hook                            | What It Does                                                  |
| ------------------------------- | ------------------------------------------------------------- |
| `session-start.js`              | Validates `.env`, detects active framework + workspace        |
| `user-prompt-rules-reminder.js` | **Anti-amnesia**: re-injects rules + workspace state per turn |
| `validate-bash-command.js`      | Blocks destructive commands (`rm -rf /`, fork bombs)          |
| `validate-workflow.js`          | Blocks hardcoded models, detects 13 API key patterns          |
| `auto-format.js`                | Runs `black`/`prettier` on every write                        |
| `pre-compact.js`                | Saves state before context compression + workspace reminder   |
| `session-end.js`                | Persists session stats for learning                           |
| `stop.js`                       | Emergency state save + workspace reminder                     |
| `detect-package-manager.js`     | Detects npm/pnpm/yarn/bun                                     |

Critical rules have 5-8 independent enforcement layers. If any four fail, the fifth catches it.

### Layer 4: Instructions -- CLAUDE.md + 19 Slash Commands

`CLAUDE.md` is auto-loaded every session with framework context, relationship mapping, and directive escalation. Slash commands are context-efficient entry points:

**Framework**: `/sdk` `/db` `/api` `/ai` `/test` `/validate` `/design` `/i-audit` `/i-harden` `/learn` `/evolve` `/checkpoint`
**Workspace**: `/analyze` `/todos` `/implement` `/redteam` `/codify` `/ws` `/wrapup`

### Layer 5: Learning -- Closed Loop Evolution

```
Session Activity -> Observations (JSONL) -> Instinct Processor -> Evolver
                                                                     |
                                                    0.85+ conf -> New Skill
                                                    0.90+ conf -> New Command
                                                    0.95+ conf -> New Agent
```

The system discovers recurring patterns and automatically generates new skills, commands, and agents. It gets smarter with every session.

---

## Quick Start (Kailash COC)

```bash
# Clone
git clone https://github.com/terrene-foundation/kailash-coc-claude-py.git
cd kailash-coc-claude-py

# Configure
cp .env.example .env   # Edit with your API keys

# Go
claude
```

The `session-start.js` hook validates your environment automatically. Then just describe what you want -- COC handles agent selection, skill loading, pattern enforcement, and quality gates.

---

## Repository Structure

```
.claude/
  agents/          30 specialist agents (Markdown + YAML frontmatter)
  skills/          28 domain knowledge directories, 100+ files
  rules/           9 behavioral constraint files
  commands/        20 slash command definitions (13 framework + 7 workspace)
  learning/        Observation-instinct-evolution pipeline

scripts/
  hooks/           9 Node.js lifecycle hooks (deterministic enforcement)
  learning/        Learning system scripts
  ci/              CI validation scripts

workspaces/
  instructions/    5 phase templates (analyze, todos, implement, validate, codify)
  <project>/       Per-project workspace directories

README.md          This file (Argus project overview + Kailash COC docs)
pyproject.toml     Python dependencies
.env.example       Environment template
```

---

## Relationship to CARE/EATP

COC applies the same trust architecture from the [Kailash SDK's CARE/EATP framework](https://github.com/terrene-foundation/kailash-py) to codegen: humans define the operating envelope (Trust Plane), AI executes within those boundaries at machine speed (Execution Plane). Rules and hooks form the Operating Envelope. Mandatory review gates maintain Trust Lineage. Hook enforcement provides Audit Anchors.

---

## Built For Kailash, Designed For Everyone

Built for the [Kailash SDK](https://github.com/terrene-foundation/kailash-py) ecosystem ([Core SDK](https://github.com/terrene-foundation/kailash-py), [DataFlow](https://github.com/terrene-foundation/kailash-py), [Nexus](https://github.com/terrene-foundation/kailash-py), [Kaizen](https://github.com/terrene-foundation/kailash-py)), but the COC architecture is framework-agnostic. Fork this repo, replace the Kailash-specific skills and agents with your own framework knowledge, and you have COC for any stack.

---

## License

Apache License, Version 2.0. See [LICENSE](LICENSE).

<p align="center">
  <a href=".claude/guides/claude-code/README.md">Full Documentation</a> |
  <a href="https://github.com/terrene-foundation/kailash-py">Kailash SDK</a>
</p>

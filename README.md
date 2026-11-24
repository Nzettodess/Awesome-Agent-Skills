# Awesome Agent Skills

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)
[![Sync Upstream Skills](https://github.com/Nzettodess/Awesome-Agent-Skills/actions/workflows/sync-skills.yml/badge.svg)](https://github.com/Nzettodess/Awesome-Agent-Skills/actions/workflows/sync-skills.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Last Updated:** 2026-11-25 04:15 (UTC+08:00)

A personal library of `SKILL.md` instructions, scripts, and references for AI coding agents. Upstream repos sync via [`sources.json`](sources.json) and [`sync-skills.ps1`](sync-skills.ps1); custom skills live alongside them.

---

## Table of Contents

- [Skills Catalog](#skills-catalog)
- [Upstream Sync](#upstream-sync)
- [Quick Start](#quick-start)
- [Contributing](#contributing)
- [License](#license)

---

## Skills Catalog

### Career
- **cv-writer**: Draft and structure CVs.
- **professional-proofreader**: Proofread career documents.
- **rendercv**: Generate CVs from YAML and LaTeX (`rendercv/rendercv`).
- **review-resume**: Review resumes and give structured feedback.

### Charts
- **mermaidjs-v11**: Build diagrams with Mermaid.js v11 syntax.
- **oh-my-mermaid**: Author and manage Mermaid diagrams (`oh-my-mermaid/oh-my-mermaid`).
- **plotly**: Plot interactive scientific and statistical charts.
- **seaborn**: Plot statistical charts with Seaborn and Matplotlib.

### Data Analytic
- **Business Analyst**: `strategy-advisor`
- **Data Cleaning**: `pandas-pro`, `preprocessing-data-with-automated-pipelines`
- **Data Modeling**: `data-analyst`, `data-scientist`, `powerbi-modeling`, `scikit-survival`, `senior-data-engineer`, `senior-data-scientist`, `statsmodels`
- **Power BI**: `power-bi-dax-optimization`, `power-bi-model-design-review`, `power-bi-performance-troubleshooting`, `power-bi-report-design-consultation`, `powerbi-modeling`, `powerbi-modeling-mcp`
- **Spreadsheets & General**: `Data Scientist`, `data-classification-prompt-standard`, `excel-analysis`, `xlsx`

### Engineering
- **Agentic AI Development**:
  - `AI-research-SKILLs-1.1.0` *(82 AI research engineering skills)*
  - `agent-evaluation`, `autonomous-agent-patterns`, `autonomous-agents`, `context-engineering`, `context-window-management`, `llm-evaluation`, `openrig-context-engineering`, `prompt-engineering`, `thought-based-reasoning`
- **Development**:
  - `architecture-copilot`, `code-review`, `codegraph`, `readme-ai`
  - `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `ponytail-review`
- **Skill Packs**:
  - `matt-skills-main` *(39 engineering workflow skills)*
  - `pstack-main` *(62 engineering and workflow skills)*
  - `rea` *(`morluto/rea`)*
  - `reverse-api-engineer-main` *(reverse-engineer web and API traffic)*

### Frontend
- **Emil-skills-main** *(20 UI, animation, and design-engineering skills)*
- **canvas-design**: Generate static art, posters, and PDFs with Canvas.
- **design.md**: Google Labs `design.md` specification and tooling.
- **frontend-design.md** & **frontend-ui-ux**: UI/UX patterns and component rules.
- **impeccable-design-polish**: Refine layout, spacing, and visual polish.
- **modern-web-guidance-main** *(2 modern web guidance skills)*
- **taste-skill-main**: Design taste and UI styling rules.
- **ui-ux-pro-max**: Searchable database of UI styles, palettes, and UX guidelines.

### Misc
- **aihot**: Query daily AI news from `aihot.news` (`v2.0.0`).
- **storage-analyzer**: Read-only macOS and Windows disk analyzer with HTML output.

### Reports
- **meeting-notes**: Format structured meeting notes.
- **notebooklm-slides**: Turn notebook content into presentation slides.
- **pdf-generator**: Build PDF documents from scripts.

### Skill Creators
- **Claude Skill Creator**: Author, test, and evaluate skills with `eval-viewer`.
- **One4All Skill Creator (`skill-from-masters-main`)**: Search and synthesize skills from curated sources.

### Stakeholder Management
- **RACI Matrix**: Build RACI responsibility matrices.

### Tampermonkey Scripts
- Local userscripts and settings (`Bilibili to Blanc Redirector`, `DuonaoVOD - MacCMS Web Audio Fixer`, `bewly-settings.json`, `网盘直链下载助手`).

### Writing
- **humanizer**: Strip AI writing patterns from prose.
- **professional-communication**: Draft workplace emails, memos, and updates.
- **professional-proofreader**: Check grammar, clarity, and tone.
- **stop-slop**: Remove filler, passive voice, and AI tells from text.

---

## Upstream Sync

[`sources.json`](sources.json) maps **47** tracked skills and packs to their upstream repositories. [`sync-skills.ps1`](sync-skills.ps1) groups entries by repo and branch, runs one shallow sparse checkout per repo, and mirrors only the configured paths. A monthly GitHub Actions workflow in [`.github/workflows/sync-skills.yml`](.github/workflows/sync-skills.yml) runs on the 1st of each month at 03:00 UTC and opens a PR when upstream files change.

<details>
<summary>Tracked Upstream Sources (47 entries in sources.json)</summary>

| Local Path (`Skills/...`) | Scope | Upstream Repository |
| :--- | :--- | :--- |
| `Claude Skill Creator` | Subfolder (`skills/skill-creator`) | https://github.com/anthropics/skills |
| `Data Analytic/xlsx/xlsx` | Subfolder (`skills/xlsx`) | https://github.com/anthropics/skills |
| `Frontend/canvas-design` | Subfolder (`skills/canvas-design`) | https://github.com/anthropics/skills |
| `Frontend/ui-ux-pro-max` | Subfolder (`src/ui-ux-pro-max`) | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| `Writing/stop-slop` | Full repo | https://github.com/hardikpandya/stop-slop |
| `Charts/mermaidjs-v11` | Subfolder (`.claude/skills/mermaidjs-v11`) | https://github.com/mrgoonie/claudekit-skills |
| `Charts/plotly` | Subfolder (`cli-tool/components/skills/scientific/plotly`) | https://github.com/davila7/claude-code-templates |
| `Charts/seaborn/seaborn` | Subfolder (`skills/seaborn`) | https://github.com/K-Dense-AI/scientific-agent-skills |
| `Writing/professional-communication` | Subfolder (`cli-tool/components/skills/enterprise-communication/professional-communication`) | https://github.com/davila7/claude-code-templates |
| `Writing/professional-proofreader` | Subfolder (`skills/professional-proofreader`) | https://github.com/diegosouzapw/awesome-omni-skills |
| `Data Analytic/Power BI/power-bi-*` (5 skills) | Subfolders (`skills/power-bi-*`, `skills/powerbi-modeling`) | https://github.com/github/awesome-copilot |
| `Engineering/matt-skills-main` | Full repo (39 skills) | https://github.com/mattpocock/skills |
| `Engineering/pstack-main` | Full repo (62 skills) | https://github.com/backnotprop/pstack |
| `Engineering/reverse-api-engineer-main` | Full repo (1 skill) | https://github.com/kalil0321/reverse-api-engineer |
| `Engineering/Development/code-review` | Full repo | https://github.com/NeoLabHQ/context-engineering-kit |
| `Engineering/Development/ponytail*` | Subfolders (6 skills) | https://github.com/DietrichGebert/ponytail |
| `Frontend/Emil-skills-main` | Full repo (20 skills) | https://github.com/emilkowalski/skills |
| `Frontend/impeccable-design-polish` | Full repo | https://github.com/pbakaus/impeccable |
| `Frontend/modern-web-guidance-main` | Full repo (2 skills) | https://github.com/GoogleChrome/modern-web-guidance-src |
| `Frontend/taste-skill-main` | Full repo | https://github.com/Leonxlnx/taste-skill |
| `One4All Skill Creator/skill-from-masters-main` | Full repo | https://github.com/GBSOSS/skill-from-masters |
| `Writing/humanizer` | Full repo | https://github.com/blader/humanizer |
| `Misc/aihot` | Subfolder (`aihot`) | https://github.com/KKKKhazix/khazix-skills |
| `Misc/storage-analyzer` | Subfolder (`storage-analyzer`) | https://github.com/KKKKhazix/khazix-skills |
| `Engineering/Development/architecture-copilot` | Full repo | https://github.com/study8677/architecture-copilot |
| `Charts/oh-my-mermaid` | Full repo | https://github.com/oh-my-mermaid/oh-my-mermaid |
| `Engineering/Development/codegraph` | Full repo | https://github.com/colbymchenry/codegraph |
| `Engineering/Development/readme-ai` | Full repo | https://github.com/eli64s/readme-ai |
| `Career/rendercv` | Full repo | https://github.com/rendercv/rendercv |
| `Data Analytic/Power BI/powerbi-modeling-mcp` | Full repo | https://github.com/microsoft/powerbi-modeling-mcp |
| `Frontend/design.md` | Full repo | https://github.com/google-labs-code/design.md |
| `Engineering/rea` | Full repo | https://github.com/morluto/rea |
| `Engineering/Agentic AI Development/prompt-engineering` | Subfolder (`cli-tool/components/skills/ai-research/prompt-engineering`) | https://github.com/davila7/claude-code-templates |
| `Engineering/Agentic AI Development/agent-evaluation` | Subfolder (`cli-tool/components/skills/ai-research/agent-evaluation`) | https://github.com/davila7/claude-code-templates |
| `Engineering/Agentic AI Development/autonomous-agent-patterns` | Subfolder (`cli-tool/components/skills/ai-research/autonomous-agent-patterns`) | https://github.com/davila7/claude-code-templates |
| `Engineering/Agentic AI Development/autonomous-agents` | Subfolder (`cli-tool/components/skills/ai-research/autonomous-agents`) | https://github.com/davila7/claude-code-templates |
| `Engineering/Agentic AI Development/context-window-management` | Subfolder (`cli-tool/components/skills/ai-research/context-window-management`) | https://github.com/davila7/claude-code-templates |
| `Engineering/Agentic AI Development/openrig-context-engineering` | Subfolder (`packages/daemon/specs/agents/shared/skills/process/context-engineering`) | https://github.com/mvschwarz/openrig |

</details>

### Unmapped or Local-Only
- **Needs upstream URL**: `Engineering/Agentic AI Development/AI-research-SKILLs-1.1.0` (`@orchestra-research/ai-research-skills`), `Data Analytic/Data Modeling/*`, `Data Analytic/Data Cleaning/*`, `Data Analytic/excel-analysis`, `Data Analytic/Business Analyst/strategy-advisor`.
- **Local-only**: `Tampermonkey Script/*`, `Career/*` (except `rendercv`), `Reports/*`, `Stakeholder Management/RACI Matrix`, `Engineering/Agentic AI Development/context-engineering` (kept separate from `openrig-context-engineering`), `llm-evaluation`, `thought-based-reasoning`.

---

## Quick Start

1. Clone the repo:
   ```powershell
   git clone https://github.com/Nzettodess/Awesome-Agent-Skills.git
   ```
2. Point your AI agent to any skill folder containing a `SKILL.md` file.
3. Preview or pull upstream updates:
   ```powershell
   .\sync-skills.ps1 -DryRun
   .\sync-skills.ps1
   .\sync-skills.ps1 -Filter "power-bi"
   ```

---

## Contributing

1. Fork the repository and create a branch (`git checkout -b feat/my-skill`).
2. Add a standalone folder under `Skills/<Category>/<skill-name>/` with a `SKILL.md` file.
3. Add an entry to [`sources.json`](sources.json) if the skill tracks an upstream repo.
4. Open a Pull Request.

---

## License

[MIT](LICENSE)

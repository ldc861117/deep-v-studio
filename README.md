# Deep V Studio

[🇨🇳 中文版](README_CN.md)

> **Multi-model video generation studio** — built on top of [LTX-2](https://github.com/Lightricks/LTX-2), extended with BYOK cloud provider support.

[![Upstream](https://img.shields.io/badge/upstream-Lightricks%2FLTX--2-blue?logo=github)](https://github.com/Lightricks/LTX-2)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Vision

Deep V Studio transforms LTX-2 from a single-model inference pipeline into a **unified video generation hub** that supports both local models and cloud APIs through a single interface.

**Core Goals:**

| Capability | Status | Description |
|---|---|---|
| 🏠 Local inference | ✅ Inherited | LTX-2/2.3 DiT models via existing `ltx-pipelines` |
| ☁️ BYOK Cloud Providers | 🚧 Phase 1 | Seedance 2.0, Veo 3.1, NanoBanana 2/Pro |
| 🔌 Provider Abstraction | ✅ Complete | Unified ABC interface + auto-config for all providers |
| 🖥️ Desktop App | 📋 Planned | Native UI for model selection, generation, and comparison |

### Why BYOK?

**Bring Your Own Key** — use your existing API subscriptions with any supported model. No vendor lock-in, no middleman markup. One prompt → choose your engine → generate.

## Architecture

```
packages/
├── ltx-core/                  # Core model components (upstream)
├── ltx-pipelines/             # Inference pipelines
│   └── src/ltx_pipelines/
│       ├── providers/         # ★ BYOK provider abstraction (NEW)
│       │   ├── base.py        # VideoGenerationProvider ABC
│       │   ├── config.py      # API key resolution (env → .env → TOML)
│       │   ├── registry.py    # Provider discovery & instantiation
│       │   ├── veo.py         # Google Veo 3.1
│       │   ├── seedance.py    # ByteDance Seedance 2.0
│       │   └── nanobanana.py  # NanoBanana 2 & Pro
│       └── *.py               # LTX-2 pipeline implementations
└── ltx-trainer/               # Training & fine-tuning tools
```

## Quick Start

```bash
# Clone
git clone https://github.com/ldc861117/deep-v-studio.git
cd deep-v-studio

# Set up environment
uv sync --frozen
source .venv/bin/activate

# Configure a cloud provider (example: Veo 3.1)
export VEO_API_KEY="your-api-key-here"
```

### API Key Configuration

Keys are resolved in priority order:

1. **Environment variable** — `export VEO_API_KEY=...`
2. **`.env` file** — in project root
3. **TOML config** — `~/.config/deep-v-studio/providers.toml`

```toml
# ~/.config/deep-v-studio/providers.toml
[providers.veo]
api_key = "your-key"

[providers.seedance]
api_key = "your-key"
```

## Upstream Relationship

This project is a **diverging fork** of [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2). We maintain an active connection to upstream for core model improvements while building an independent product layer on top.

### Fork Strategy

```
Lightricks/LTX-2 (upstream)          ldc861117/deep-v-studio (origin)
     │                                        │
     │  core model updates                    │  BYOK providers, desktop app,
     │  (ltx-core, pipelines)                 │  product features
     │                                        │
     └──── periodic sync ────────────────────►│
           (merge upstream/main)              │
```

**Sync policy:**
- `upstream` remote tracks `Lightricks/LTX-2`
- Core packages (`ltx-core`, `ltx-trainer`) sync regularly from upstream
- Our additions (`providers/`, `scripts/`, convention files) never conflict with upstream
- Sync command:
  ```bash
  git fetch upstream
  git merge upstream/main --no-edit
  # Resolve any conflicts in our added files, then push
  git push origin main
  ```

**What we DON'T change from upstream:**
- `ltx-core/` package internals
- Existing pipeline implementations in `ltx-pipelines/*.py`
- Model checkpoint formats and compatibility

**What we ADD on top:**
- `providers/` — BYOK cloud provider abstraction layer
- `AGENTS.md`, `GEMINI.md` — AI-assisted development conventions
- `scripts/` — Automation and task dispatch tools
- `docs/superpowers/` — Specs and plans
- Desktop application (future)

## Development

This project uses an **AI-assisted development paradigm** with [Superpowers](https://github.com/obra/superpowers) workflow and Jules CLI for parallel task execution.

| Role | Responsibility |
|---|---|
| **Architect** (Gemini) | Research, design, planning, code review, task dispatch |
| **Builder** (Jules) | TDD implementation within isolated file boundaries |
| **Decision-maker** (User) | Approval, prioritization, merge triggers |

See [`AGENTS.md`](AGENTS.md) for full conventions.

### Commands

```bash
# Lint & format
uv run ruff check .
uv run ruff format .

# Test
uv run pytest                              # All tests
uv run pytest -k "test_providers"          # Provider tests only

# Sync upstream
git fetch upstream && git merge upstream/main
```

## Available Pipelines (from LTX-2)

| Pipeline | Description |
|---|---|
| [TI2VidTwoStagesPipeline](packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages.py) | Production-quality text/image-to-video with 2x upsampling |
| [TI2VidTwoStagesHQPipeline](packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages_hq.py) | Second-order sampler (fewer steps, better quality) |
| [DistilledPipeline](packages/ltx-pipelines/src/ltx_pipelines/distilled.py) | Fastest inference with 8 predefined sigmas |
| [ICLoraPipeline](packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py) | Video-to-video and image-to-video with LoRA |
| [A2VidPipelineTwoStage](packages/ltx-pipelines/src/ltx_pipelines/a2vid_two_stage.py) | Audio-conditioned video generation |

For model downloads and detailed pipeline docs, see the [upstream README](https://github.com/Lightricks/LTX-2#readme).

## License

This project inherits the [Apache 2.0 License](LICENSE) from upstream LTX-2.

---

<sub>Forked from [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) • Core model by [Lightricks](https://ltx.io)</sub>

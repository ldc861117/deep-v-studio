# deep-v-studio — Gemini Project Context

@./AGENTS.md

## Superpowers Integration
This project uses the [Superpowers](https://github.com/obra/superpowers) agentic workflow framework.
All development follows: brainstorming → spec → plan → TDD → review → finish.

## Project Structure
```
deep-v-studio/                  # Python monorepo (uv-managed)
├── packages/
│   ├── ltx-core/               # Core model implementation (DiT, VAE, text encoder)
│   ├── ltx-pipelines/          # Inference pipelines + provider abstraction
│   │   └── src/ltx_pipelines/
│   │       ├── providers/      # BYOK multi-model providers (NEW)
│   │       ├── *.py            # LTX-2 pipeline implementations
│   │       └── utils/          # Shared pipeline utilities
│   └── ltx-trainer/            # Training & fine-tuning tools
├── docs/superpowers/
│   ├── specs/                  # Design documents
│   └── plans/                  # Implementation plans (Jules-dispatchable)
├── AGENTS.md                   # Shared conventions for all AI sessions
└── GEMINI.md                   # This file
```

## Quick Reference
- **Package manager**: `uv` (use `uv sync`, `uv run pytest`)
- **Python**: 3.11+
- **Linter/Formatter**: `ruff` (config in root `pyproject.toml`)
- **Tests**: `pytest` (run from package dirs or root)
- **Known first-party packages**: `ltx_core`, `ltx_pipelines`, `ltx_trainer`

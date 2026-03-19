# AGENTS.md — deep-v-studio Development Conventions

> **All AI coding sessions (Gemini, Jules, Claude, etc.) MUST follow these conventions.**
> This file is the shared protocol that ensures parallel sessions produce code that integrates cleanly.

## Project Vision

**deep-v-studio** is a multi-model video generation studio built on top of LTX-2. It supports:
- **Local inference**: LTX-2/2.3 DiT models (existing `ltx-pipelines` package)
- **Cloud BYOK providers**: Seedance 2.0, Veo 3.1, NanoBanana 2/Pro (via `providers/` module)

## Architecture

```
packages/ltx-pipelines/src/ltx_pipelines/
├── providers/                 # BYOK multi-model provider abstraction
│   ├── __init__.py            # Registry factory: get_provider(), list_providers()
│   ├── base.py                # ABC: VideoGenerationProvider, Request, Result, Capabilities
│   ├── config.py              # ProviderConfig: API key loading (env → .env → config)
│   ├── registry.py            # ModelRegistry: register/lookup/list providers
│   ├── seedance.py            # Seedance 2.0 provider (ByteDance API)
│   ├── veo.py                 # Veo 3.1 provider (Google Vertex AI / AI Studio)
│   └── nanobanana.py          # NanoBanana 2 & Pro provider
├── *.py                       # Existing LTX-2 pipeline implementations
└── utils/                     # Shared pipeline utilities
```

**Key dependency**: `ltx-core` provides all model components. `ltx-pipelines` builds on top.

## Code Standards

### Python
- **Version**: 3.11+ syntax (use `str | Path` not `Union[str, Path]`, `list[str]` not `List[str]`)
- **Type hints**: Required on all function arguments and return values
- **File operations**: Use `pathlib.Path`
- **Logging**: Use module-level `logger` (never `print()` in production code)
- **Async**: Provider implementations use `async/await` for API calls
- **Torch**: Use `@torch.inference_mode()` for inference (not `@torch.no_grad()`)

### Linting & Formatting
```bash
uv run ruff check .     # Lint
uv run ruff format .    # Format
```
All code MUST pass `ruff check` before commit. Config is in root `pyproject.toml`.

### Testing
- **Framework**: `pytest`
- **TDD mandatory**: Write failing test → implement → verify pass → commit
- **External APIs**: Always mock in tests (never call real APIs in CI)
- **Run tests**:
  ```bash
  uv run pytest                           # All tests
  uv run pytest packages/ltx-pipelines/   # Pipeline tests only
  uv run pytest -k "test_providers"       # Provider tests only
  ```

### Commit Messages
Use [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add Veo 3.1 provider with text-to-video support
fix: handle API timeout in Seedance provider
test: add mock tests for NanoBanana provider
docs: update AGENTS.md with new provider conventions
```

## Provider Implementation Contract

Every provider MUST:

1. **Inherit** from `VideoGenerationProvider` (in `providers/base.py`)
2. **Implement** all abstract methods:
   - `async generate_video(request) -> result`
   - `async check_status(task_id) -> status`
   - `validate_api_key() -> bool`
   - `capabilities` property
3. **Load API keys** via `ProviderConfig` (never hardcode)
4. **Include type hints** on every method
5. **Have tests** in `tests/test_providers/test_<name>.py` with mocked API calls
6. **Pass** `ruff check` and `ruff format`

## File Ownership (Parallel Safety)

When multiple Jules sessions run simultaneously, each session MUST only touch its assigned files.

| Session Task | Owned Files (create/modify) | Read-Only |
|---|---|---|
| Seedance provider | `providers/seedance.py`, `tests/test_providers/test_seedance.py` | `providers/base.py`, `providers/config.py` |
| Veo provider | `providers/veo.py`, `tests/test_providers/test_veo.py` | `providers/base.py`, `providers/config.py` |
| NanoBanana provider | `providers/nanobanana.py`, `tests/test_providers/test_nanobanana.py` | `providers/base.py`, `providers/config.py` |

**Shared files** (`base.py`, `config.py`, `registry.py`, `AGENTS.md`) are modified ONLY by the Architect, never by parallel builder sessions.

## Development Workflow

This project follows the [Superpowers](https://github.com/obra/superpowers) workflow:

1. **Brainstorm** → clarify requirements, explore alternatives, present design
2. **Write spec** → save to `docs/superpowers/specs/`
3. **Write plan** → save to `docs/superpowers/plans/`, bite-sized TDD tasks
4. **Execute** → one task at a time, TDD (RED → GREEN → REFACTOR), commit after each
5. **Review** → spec compliance + code quality review
6. **Finish** → verify all tests, merge or PR

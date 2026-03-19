#!/bin/bash
# deep-v-studio: Jules PoC Dispatch — Veo 3.1 Provider
# Run from project root: bash scripts/dispatch_veo_poc.sh

set -euo pipefail

TASK_PROMPT='Implement Veo 3.1 video generation provider for deep-v-studio.

## IMPORTANT: Read AGENTS.md first
Read the AGENTS.md file in the repo root. It defines all conventions you MUST follow.

## Goal
Create a Veo 3.1 provider that wraps the Google Vertex AI / AI Studio video generation API.

## Files to Create (you may ONLY touch these files)
- packages/ltx-pipelines/src/ltx_pipelines/providers/veo.py
- packages/ltx-pipelines/tests/test_providers/test_veo.py

## Files to Read (DO NOT modify)
- packages/ltx-pipelines/src/ltx_pipelines/providers/base.py (inherit VideoGenerationProvider)
- packages/ltx-pipelines/src/ltx_pipelines/providers/config.py (use get_provider_config("veo"))
- packages/ltx-pipelines/src/ltx_pipelines/providers/registry.py (register your provider)
- AGENTS.md (all conventions)

## Requirements
1. Class VeoProvider(VideoGenerationProvider) in providers/veo.py
2. Implement all abstract methods: generate_video, check_status, validate_api_key, capabilities property
3. Use async/await with httpx or aiohttp for Google Vertex AI API calls
4. Use ProviderConfig with api_key_env_var="VEO_API_KEY" for authentication
5. Support text_to_video mode at minimum
6. Handle API polling: submit job → poll for completion → return video URL

## TDD Process (mandatory)
1. Write test_veo.py FIRST with all test cases (mock all API calls, never call real APIs)
2. Run tests — they should FAIL (RED)
3. Implement veo.py to make tests pass (GREEN)
4. Refactor if needed
5. Run: ruff check and ruff format on both files
6. Commit with message: feat: add Veo 3.1 provider with text-to-video support

## Exit Criteria
- All tests pass
- ruff check produces 0 errors
- ruff format produces no changes
- Commit made with conventional commit message'

echo "🚀 Dispatching Jules PoC task: Veo 3.1 Provider"
echo "---"
echo "$TASK_PROMPT"
echo "---"

jules new "$TASK_PROMPT"

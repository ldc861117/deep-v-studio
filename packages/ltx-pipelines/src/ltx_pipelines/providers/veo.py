"""Veo 3.1 video generation provider (Google Gemini API / AI Studio).

API Reference: https://ai.google.dev/gemini-api/docs/video
"""

from __future__ import annotations

import logging

import httpx

from ltx_pipelines.providers.base import (
    GenerationMode,
    ProviderCapabilities,
    TaskStatus,
    VideoGenerationProvider,
    VideoGenerationRequest,
    VideoGenerationResult,
)
from ltx_pipelines.providers.config import get_provider_config
from ltx_pipelines.providers.registry import register_provider

logger = logging.getLogger(__name__)

# Gemini API base URL for Veo
_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Available model variants
VEO_MODEL_STANDARD = "veo-3.1-generate-preview"
VEO_MODEL_FAST = "veo-3.1-fast-generate-preview"


class VeoProvider(VideoGenerationProvider):
    """Provider for Google's Veo 3.1 video generation model.

    Uses the Gemini API (generativelanguage.googleapis.com) with
    API Key authentication.

    Supports:
        - Text-to-video generation
        - Configurable aspect ratio (16:9 or 9:16)
        - Configurable duration (4, 6, or 8 seconds)
        - Resolution control (720p, 1080p, 4k)
        - Standard and Fast model variants
    """

    def __init__(self, *, model: str = VEO_MODEL_STANDARD) -> None:
        self.config = get_provider_config("veo")
        self.base_url = self.config.base_url or _DEFAULT_BASE_URL
        self.model = model

    @property
    def name(self) -> str:
        return "Veo 3.1"

    @property
    def provider_id(self) -> str:
        return "veo"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modes=[GenerationMode.TEXT_TO_VIDEO],
            max_resolution=(3840, 2160),  # 4K support
            max_duration_seconds=8.0,
            supports_negative_prompt=False,
            supports_seed=True,  # Veo 3.x supports seed (partial determinism)
        )

    def _get_headers(self, api_key: str) -> dict[str, str]:
        """Build request headers with API key authentication."""
        return {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }

    async def validate_api_key(self) -> bool:
        """Check if the API key is valid by listing models."""
        api_key = self.config.resolve_api_key()
        if not api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(api_key),
                )
                return response.status_code == 200
        except httpx.RequestError:
            logger.exception("Failed to validate Veo API key")
            return False

    async def generate_video(
        self, request: VideoGenerationRequest
    ) -> VideoGenerationResult:
        """Submit a video generation job to Veo via predictLongRunning.

        Uses the Gemini API format:
            POST /models/{model}:predictLongRunning
            {"instances": [{"prompt": "..."}]}

        Returns:
            VideoGenerationResult with an LRO operation name as task_id.
        """
        api_key = self.config.resolve_api_key()
        if not api_key:
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message="API key not found. Set VEO_API_KEY env var.",
            )

        headers = self._get_headers(api_key)
        url = f"{self.base_url}/models/{self.model}:predictLongRunning"

        # Build the instance following the official API format
        instance: dict[str, object] = {"prompt": request.prompt}

        # Build generation config
        config: dict[str, object] = {}

        # Aspect ratio: "16:9" (default) or "9:16"
        aspect_ratio = self.config.extra.get("aspect_ratio", "16:9")
        config["aspectRatio"] = aspect_ratio

        # Duration: "4", "6", or "8" seconds
        if request.duration_seconds:
            duration = str(min(int(request.duration_seconds), 8))
            config["durationSeconds"] = duration

        # Resolution: "720p", "1080p", or "4k"
        resolution = self.config.extra.get("resolution", "720p")
        config["resolution"] = resolution

        # Person generation: "allow_all" or "allow_adult"
        person_gen = self.config.extra.get("person_generation")
        if person_gen:
            config["personGeneration"] = person_gen

        # Negative prompt
        if request.negative_prompt:
            config["negativePrompt"] = request.negative_prompt

        # Seed (partial determinism)
        if request.seed is not None:
            config["seed"] = request.seed

        payload: dict[str, object] = {"instances": [instance]}
        if config:
            payload["generationConfig"] = config

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # The API returns an LRO with a "name" field
                task_id = data.get("name")
                if not task_id:
                    return VideoGenerationResult(
                        task_id="",
                        status=TaskStatus.FAILED,
                        error_message=f"No operation name in response: {data}",
                    )

                logger.info("Veo generation started: %s", task_id)
                return VideoGenerationResult(
                    task_id=task_id,
                    status=TaskStatus.PENDING,
                )

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error("Veo API error: %s", error_text)
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message=f"API error ({e.response.status_code}): {error_text}",
            )
        except Exception as e:
            logger.exception("Unexpected error during Veo video generation")
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message=str(e),
            )

    async def check_status(self, task_id: str) -> VideoGenerationResult:
        """Poll the status of a Veo generation LRO.

        The API returns {"done": true/false, ...}. When done:
        - Success: .response.generateVideoResponse.generatedSamples[0].video.uri
        - Error: .error.message
        """
        api_key = self.config.resolve_api_key()
        if not api_key:
            return VideoGenerationResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="API key not found",
            )

        headers = self._get_headers(api_key)
        url = f"{self.base_url}/{task_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if not data.get("done", False):
                    return VideoGenerationResult(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                    )

                # Check for error
                if "error" in data:
                    return VideoGenerationResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error_message=data["error"].get("message", "Unknown error"),
                    )

                # Extract video URL from the official response format
                video_url = None
                resp = data.get("response", {})
                gen_resp = resp.get("generateVideoResponse", {})
                samples = gen_resp.get("generatedSamples", [])
                if samples:
                    video_url = samples[0].get("video", {}).get("uri")

                return VideoGenerationResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    video_url=video_url,
                )

        except Exception as e:
            logger.exception("Error checking Veo task status")
            return VideoGenerationResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
            )


# Register the provider
register_provider("veo", VeoProvider)

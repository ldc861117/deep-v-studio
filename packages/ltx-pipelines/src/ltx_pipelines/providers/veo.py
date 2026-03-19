"""Veo 3.1 video generation provider (Google Vertex AI / AI Studio)."""

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


class VeoProvider(VideoGenerationProvider):
    """Provider for Google's Veo 3.1 video generation model.

    This provider supports both Google AI Studio (using API Key) and
    Vertex AI (using OAuth2 tokens).
    """

    def __init__(self) -> None:
        self.config = get_provider_config("veo")
        # Default to AI Studio if no base_url is provided
        self.base_url = self.config.base_url or "https://generativelanguage.googleapis.com/v1beta"

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
            max_resolution=(1280, 720),
            max_duration_seconds=10.0,
            supports_negative_prompt=False,
            supports_seed=False,
        )

    def _get_headers(self, api_key: str) -> dict[str, str]:
        """Determine headers based on the API key format."""
        # AI Studio keys are typically just a string, Vertex AI uses Bearer tokens
        if api_key.startswith("ya29."):
            return {"Authorization": f"Bearer {api_key}"}
        return {"x-goog-api-key": api_key}

    async def validate_api_key(self) -> bool:
        """Check if the API key is valid."""
        api_key = self.config.resolve_api_key()
        if not api_key:
            return False

        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient() as client:
                # Use a lightweight endpoint to check the key
                response = await client.get(f"{self.base_url}/models", headers=headers)
                return response.status_code == 200
        except httpx.RequestError:
            logger.exception("Failed to validate Veo API key")
            return False

    async def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        """Submit a video generation job to Veo."""
        api_key = self.config.resolve_api_key()
        if not api_key:
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message="API key not found",
            )

        headers = self._get_headers(api_key)
        # Handle project/location for Vertex AI if provided in extra config
        project = self.config.extra.get("project")
        location = self.config.extra.get("location", "us-central1")

        if project:
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/veo-001:predict"
            payload = {
                "instances": [
                    {
                        "prompt": request.prompt,
                    }
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                },
            }
        else:
            # AI Studio / Generative Language API
            url = f"{self.base_url}/models/veo-001:generateVideo"
            payload = {
                "prompt": request.prompt,
                "videoConfig": {
                    "durationSeconds": request.duration_seconds,
                    "aspectRatio": "16:9",
                },
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # Google APIs often return an Operation name for LRO
                task_id = data.get("name")
                if not task_id and "metadata" in data:
                    # Sometimes it's in metadata for Vertex AI
                    task_id = data.get("metadata", {}).get("name")

                if not task_id:
                    # If it's a synchronous response (unlikely for video, but for completeness)
                    if "video" in data:
                        return VideoGenerationResult(
                            task_id="sync",
                            status=TaskStatus.COMPLETED,
                            video_url=data["video"].get("uri"),
                        )
                    return VideoGenerationResult(
                        task_id="",
                        status=TaskStatus.FAILED,
                        error_message="No task ID returned from API",
                    )

                return VideoGenerationResult(
                    task_id=task_id,
                    status=TaskStatus.PENDING,
                )
        except httpx.HTTPStatusError as e:
            logger.error("Veo API error: %s", e.response.text)
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message=f"API error: {e.response.text}",
            )
        except Exception as e:
            logger.exception("Unexpected error during Veo video generation")
            return VideoGenerationResult(
                task_id="",
                status=TaskStatus.FAILED,
                error_message=str(e),
            )

    async def check_status(self, task_id: str) -> VideoGenerationResult:
        """Poll the status of a Veo generation task."""
        if task_id == "sync":
            return VideoGenerationResult(task_id=task_id, status=TaskStatus.COMPLETED)

        api_key = self.config.resolve_api_key()
        if not api_key:
            return VideoGenerationResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="API key not found",
            )

        headers = self._get_headers(api_key)
        # Determine if task_id is a full resource name or just an ID
        if task_id.startswith(("projects/", "operations/")):
            # It's likely a full Vertex AI / LRO resource name
            if task_id.startswith("projects/"):
                location = task_id.split("/")[3]
                url = f"https://{location}-aiplatform.googleapis.com/v1/{task_id}"
            else:
                url = f"{self.base_url}/{task_id}"
        else:
            url = f"{self.base_url}/operations/{task_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if not data.get("done", False):
                    return VideoGenerationResult(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                    )

                if "error" in data:
                    return VideoGenerationResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error_message=data["error"].get("message", "Unknown error"),
                    )

                # Extract video URL
                video_url = None
                resp_payload = data.get("response", {})
                if "video" in resp_payload:
                    video_url = resp_payload["video"].get("uri")
                elif "outputs" in resp_payload:
                    # Vertex AI format
                    outputs = resp_payload.get("outputs", [])
                    if outputs and "uri" in outputs[0]:
                        video_url = outputs[0]["uri"]

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

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ltx_pipelines.providers.base import (
    GenerationMode,
    TaskStatus,
    VideoGenerationRequest,
)
from ltx_pipelines.providers.veo import VEO_MODEL_STANDARD, VeoProvider

if TYPE_CHECKING:
    from ltx_pipelines.providers.base import ProviderCapabilities


class TestVeoProvider:
    @pytest.fixture
    def provider(self) -> VeoProvider:
        return VeoProvider()

    def test_capabilities(self, provider: VeoProvider) -> None:
        caps: ProviderCapabilities = provider.capabilities
        assert GenerationMode.TEXT_TO_VIDEO in caps.supported_modes
        assert caps.max_resolution == (3840, 2160)  # 4K
        assert caps.max_duration_seconds == 8.0
        assert caps.supports_seed is True

    def test_model_default(self, provider: VeoProvider) -> None:
        assert provider.model == VEO_MODEL_STANDARD
        assert provider.model == "veo-3.1-generate-preview"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_validate_api_key_success(
        self, mock_get: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            assert await provider.validate_api_key() is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_validate_api_key_failure(
        self, mock_get: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with patch.object(
            provider.config, "resolve_api_key", return_value="wrong-key"
        ):
            assert await provider.validate_api_key() is False

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_video_success(
        self, mock_post: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "operations/generate-video-abc123"
        }
        mock_post.return_value = mock_response

        request = VideoGenerationRequest(prompt="A beautiful sunset")
        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.generate_video(request)

        assert result.task_id == "operations/generate-video-abc123"
        assert result.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_generate_video_no_api_key(self, provider: VeoProvider) -> None:
        request = VideoGenerationRequest(prompt="test")
        with patch.object(provider.config, "resolve_api_key", return_value=None):
            result = await provider.generate_video(request)

        assert result.status == TaskStatus.FAILED
        assert "API key not found" in (result.error_message or "")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_processing(
        self, mock_get: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "operations/op-123",
            "done": False,
        }
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("operations/op-123")

        assert result.status == TaskStatus.PROCESSING

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_completed(
        self, mock_get: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Official response format from Google API docs
        mock_response.json.return_value = {
            "name": "operations/op-123",
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [
                        {"video": {"uri": "https://storage.example.com/video.mp4"}}
                    ]
                }
            },
        }
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("operations/op-123")

        assert result.status == TaskStatus.COMPLETED
        assert result.video_url == "https://storage.example.com/video.mp4"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_failed(
        self, mock_get: MagicMock, provider: VeoProvider
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "operations/op-123",
            "done": True,
            "error": {"message": "Content policy violation"},
        }
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("operations/op-123")

        assert result.status == TaskStatus.FAILED
        assert result.error_message is not None
        assert "Content policy violation" in result.error_message

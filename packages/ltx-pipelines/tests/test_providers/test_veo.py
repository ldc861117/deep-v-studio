from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ltx_pipelines.providers.base import (
    GenerationMode,
    TaskStatus,
    VideoGenerationRequest,
)
from ltx_pipelines.providers.veo import VeoProvider

if TYPE_CHECKING:
    from ltx_pipelines.providers.base import ProviderCapabilities


class TestVeoProvider:
    @pytest.fixture
    def provider(self) -> VeoProvider:
        return VeoProvider()

    def test_capabilities(self, provider: VeoProvider) -> None:
        caps: ProviderCapabilities = provider.capabilities
        assert GenerationMode.TEXT_TO_VIDEO in caps.supported_modes
        assert caps.max_resolution == (1280, 720)
        assert caps.max_duration_seconds == 10.0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_validate_api_key_success(self, mock_get: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Mock resolve_api_key to return a key
        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            assert await provider.validate_api_key() is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_validate_api_key_failure(self, mock_get: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="wrong-key"):
            assert await provider.validate_api_key() is False

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_video_success(self, mock_post: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "projects/p/locations/l/operations/op-123"}
        mock_post.return_value = mock_response

        request = VideoGenerationRequest(prompt="A beautiful sunset")
        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.generate_video(request)

        assert result.task_id == "projects/p/locations/l/operations/op-123"
        assert result.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_processing(self, mock_get: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "op-123",
            "done": False,
        }
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("op-123")

        assert result.status == TaskStatus.PROCESSING

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_completed(self, mock_get: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "op-123",
            "done": True,
            "response": {"video": {"uri": "https://example.com/video.mp4"}},
        }
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("op-123")

        assert result.status == TaskStatus.COMPLETED
        assert result.video_url == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_check_status_failed(self, mock_get: MagicMock, provider: VeoProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "op-123", "done": True, "error": {"message": "Something went wrong"}}
        mock_get.return_value = mock_response

        with patch.object(provider.config, "resolve_api_key", return_value="fake-key"):
            result = await provider.check_status("op-123")

        assert result.status == TaskStatus.FAILED
        assert result.error_message is not None
        assert "Something went wrong" in result.error_message

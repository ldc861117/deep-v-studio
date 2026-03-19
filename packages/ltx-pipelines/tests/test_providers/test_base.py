"""Tests for providers/base.py — ABC, dataclasses, and validation."""

from pathlib import Path

import pytest

from ltx_pipelines.providers.base import (
    GenerationMode,
    ProviderCapabilities,
    TaskStatus,
    VideoGenerationProvider,
    VideoGenerationRequest,
    VideoGenerationResult,
)


# ---------------------------------------------------------------------------
# Concrete stub for testing the ABC
# ---------------------------------------------------------------------------
class StubProvider(VideoGenerationProvider):
    """Minimal concrete provider for testing base class behavior."""

    @property
    def name(self) -> str:
        return "Stub Provider"

    @property
    def provider_id(self) -> str:
        return "stub"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modes=[GenerationMode.TEXT_TO_VIDEO],
            max_resolution=(1920, 1080),
            max_duration_seconds=10.0,
            supports_negative_prompt=False,
            supports_seed=True,
        )

    async def validate_api_key(self) -> bool:
        return True

    async def generate_video(self, _request: VideoGenerationRequest) -> VideoGenerationResult:
        return VideoGenerationResult(
            task_id="test-123",
            status=TaskStatus.COMPLETED,
            video_path=Path("/tmp/test.mp4"),
        )

    async def check_status(self, task_id: str) -> VideoGenerationResult:
        return VideoGenerationResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
        )


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------
class TestTaskStatus:
    def test_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_all_statuses_exist(self) -> None:
        expected = {"pending", "processing", "completed", "failed", "cancelled"}
        assert {s.value for s in TaskStatus} == expected


class TestGenerationMode:
    def test_values(self) -> None:
        assert GenerationMode.TEXT_TO_VIDEO.value == "text_to_video"
        assert GenerationMode.IMAGE_TO_VIDEO.value == "image_to_video"
        assert GenerationMode.VIDEO_TO_VIDEO.value == "video_to_video"


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------
class TestVideoGenerationRequest:
    def test_defaults(self) -> None:
        req = VideoGenerationRequest(prompt="a cat")
        assert req.prompt == "a cat"
        assert req.mode == GenerationMode.TEXT_TO_VIDEO
        assert req.width == 1280
        assert req.height == 720
        assert req.negative_prompt is None
        assert req.seed is None

    def test_all_fields(self) -> None:
        req = VideoGenerationRequest(
            prompt="sunset over ocean",
            mode=GenerationMode.IMAGE_TO_VIDEO,
            negative_prompt="blurry",
            width=1920,
            height=1080,
            duration_seconds=8.0,
            seed=42,
            input_image_path=Path("/tmp/img.png"),
            extra_params={"style": "cinematic"},
        )
        assert req.seed == 42
        assert req.extra_params["style"] == "cinematic"


class TestVideoGenerationResult:
    def test_success_result(self) -> None:
        result = VideoGenerationResult(
            task_id="abc-123",
            status=TaskStatus.COMPLETED,
            video_path=Path("/output/video.mp4"),
            duration_seconds=5.0,
        )
        assert result.error_message is None
        assert result.video_path is not None

    def test_error_result(self) -> None:
        result = VideoGenerationResult(
            task_id="abc-456",
            status=TaskStatus.FAILED,
            error_message="Rate limit exceeded",
        )
        assert result.status == TaskStatus.FAILED
        assert result.video_path is None


class TestProviderCapabilities:
    def test_defaults(self) -> None:
        caps = ProviderCapabilities()
        assert caps.max_resolution == (1280, 720)
        assert caps.max_duration_seconds == 10.0
        assert caps.supported_modes == []


# ---------------------------------------------------------------------------
# ABC + validation tests
# ---------------------------------------------------------------------------
class TestVideoGenerationProvider:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            VideoGenerationProvider()  # type: ignore[abstract]

    def test_stub_provider_properties(self) -> None:
        provider = StubProvider()
        assert provider.name == "Stub Provider"
        assert provider.provider_id == "stub"
        assert GenerationMode.TEXT_TO_VIDEO in provider.capabilities.supported_modes

    @pytest.mark.asyncio
    async def test_generate_video(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test")
        result = await provider.generate_video(request)
        assert result.status == TaskStatus.COMPLETED
        assert result.task_id == "test-123"

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        provider = StubProvider()
        result = await provider.check_status("task-abc")
        assert result.task_id == "task-abc"

    def test_validate_request_valid(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", width=1920, height=1080, duration_seconds=5.0)
        errors = provider.validate_request(request)
        assert errors == []

    def test_validate_request_unsupported_mode(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", mode=GenerationMode.VIDEO_TO_VIDEO)
        errors = provider.validate_request(request)
        assert len(errors) == 1
        assert "not supported" in errors[0]

    def test_validate_request_exceeds_resolution(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", width=4096, height=2160)
        errors = provider.validate_request(request)
        assert len(errors) == 2  # both width and height exceed

    def test_validate_request_exceeds_duration(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", duration_seconds=60.0)
        errors = provider.validate_request(request)
        assert any("Duration" in e for e in errors)

    def test_validate_request_unsupported_negative_prompt(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", negative_prompt="blurry")
        errors = provider.validate_request(request)
        assert any("negative prompt" in e.lower() for e in errors)

    def test_validate_request_seed_supported(self) -> None:
        provider = StubProvider()
        request = VideoGenerationRequest(prompt="test", seed=42)
        errors = provider.validate_request(request)
        assert errors == []  # StubProvider supports seed

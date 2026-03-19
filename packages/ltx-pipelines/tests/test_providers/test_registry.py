"""Tests for providers/registry.py — register, get, list, clear."""

import pytest

from ltx_pipelines.providers.base import (
    GenerationMode,
    ProviderCapabilities,
    TaskStatus,
    VideoGenerationProvider,
    VideoGenerationRequest,
    VideoGenerationResult,
)
from ltx_pipelines.providers.registry import (
    clear_registry,
    get_provider,
    list_providers,
    register_provider,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------
class FakeProvider(VideoGenerationProvider):
    """A fake provider for registry tests."""

    @property
    def name(self) -> str:
        return "Fake"

    @property
    def provider_id(self) -> str:
        return "fake"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supported_modes=[GenerationMode.TEXT_TO_VIDEO])

    async def validate_api_key(self) -> bool:
        return True

    async def generate_video(self, _request: VideoGenerationRequest) -> VideoGenerationResult:
        return VideoGenerationResult(task_id="fake-1", status=TaskStatus.COMPLETED)

    async def check_status(self, task_id: str) -> VideoGenerationResult:
        return VideoGenerationResult(task_id=task_id, status=TaskStatus.COMPLETED)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Ensure registry is clean before and after each test."""
    clear_registry()
    yield  # type: ignore[misc]
    clear_registry()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestRegisterProvider:
    def test_register_instance(self) -> None:
        provider = FakeProvider()
        register_provider("fake", provider)
        assert "fake" in list_providers()

    def test_register_class(self) -> None:
        register_provider("fake", FakeProvider)
        assert "fake" in list_providers()


class TestGetProvider:
    def test_get_registered_instance(self) -> None:
        provider = FakeProvider()
        register_provider("fake", provider)
        result = get_provider("fake")
        assert result is provider

    def test_get_registered_class_instantiates(self) -> None:
        register_provider("fake", FakeProvider)
        result = get_provider("fake")
        assert isinstance(result, FakeProvider)

    def test_get_class_caches_instance(self) -> None:
        register_provider("fake", FakeProvider)
        first = get_provider("fake")
        second = get_provider("fake")
        assert first is second  # same instance

    def test_get_unregistered_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_provider("nonexistent")

    def test_error_message_shows_available(self) -> None:
        register_provider("alpha", FakeProvider)
        register_provider("beta", FakeProvider)
        with pytest.raises(KeyError, match="alpha") as exc_info:
            get_provider("missing")
        assert "beta" in str(exc_info.value)


class TestListProviders:
    def test_empty(self) -> None:
        assert list_providers() == []

    def test_sorted(self) -> None:
        register_provider("zebra", FakeProvider)
        register_provider("alpha", FakeProvider)
        assert list_providers() == ["alpha", "zebra"]


class TestClearRegistry:
    def test_clear(self) -> None:
        register_provider("fake", FakeProvider)
        assert len(list_providers()) == 1
        clear_registry()
        assert list_providers() == []

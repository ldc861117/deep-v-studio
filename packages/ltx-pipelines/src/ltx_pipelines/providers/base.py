"""BYOK provider abstraction for multi-model video generation.

This module defines the base interfaces that all cloud video generation
providers (Seedance, Veo, NanoBanana, etc.) must implement.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStatus(enum.Enum):
    """Status of an asynchronous video generation task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationMode(enum.Enum):
    """Supported video generation modes."""

    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"


@dataclass
class ProviderCapabilities:
    """Declares what a provider can do.

    Used by the registry and UI to show available features per model.
    """

    supported_modes: list[GenerationMode] = field(default_factory=list)
    max_resolution: tuple[int, int] = (1280, 720)
    max_duration_seconds: float = 10.0
    supports_negative_prompt: bool = False
    supports_seed: bool = False
    supported_aspect_ratios: list[str] = field(default_factory=lambda: ["16:9"])
    extra: dict[str, object] = field(default_factory=dict)


@dataclass
class VideoGenerationRequest:
    """Unified input for all providers.

    Each provider maps this to its native API format.
    """

    prompt: str
    mode: GenerationMode = GenerationMode.TEXT_TO_VIDEO
    negative_prompt: str | None = None
    width: int = 1280
    height: int = 720
    duration_seconds: float = 5.0
    seed: int | None = None
    input_image_path: Path | None = None
    input_video_path: Path | None = None
    extra_params: dict[str, object] = field(default_factory=dict)


@dataclass
class VideoGenerationResult:
    """Unified output from all providers.

    Providers populate this after successful generation.
    """

    task_id: str
    status: TaskStatus
    video_path: Path | None = None
    video_url: str | None = None
    duration_seconds: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    error_message: str | None = None


class VideoGenerationProvider(ABC):
    """Abstract base for all video generation providers.

    Every cloud provider (Seedance, Veo, NanoBanana) and the local
    LTX wrapper must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g., 'Veo 3.1')."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Machine identifier (e.g., 'veo', 'seedance')."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """What this provider supports."""

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """Check if the configured API key is valid.

        Returns:
            True if the key is valid and the provider is reachable.
        """

    @abstractmethod
    async def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        """Submit a video generation request.

        For async providers, this returns immediately with a task_id
        and status=PENDING. Use check_status() to poll.

        For sync providers, this blocks and returns status=COMPLETED.

        Args:
            request: The generation parameters.

        Returns:
            Result with task_id, status, and (optionally) video path/URL.
        """

    @abstractmethod
    async def check_status(self, task_id: str) -> VideoGenerationResult:
        """Poll the status of an async generation task.

        Args:
            task_id: The task identifier from generate_video().

        Returns:
            Updated result with current status and video if complete.
        """

    def validate_request(self, request: VideoGenerationRequest) -> list[str]:
        """Validate a request against this provider's capabilities.

        Returns a list of error messages (empty = valid).
        """
        errors: list[str] = []
        caps = self.capabilities

        if request.mode not in caps.supported_modes:
            errors.append(
                f"Mode {request.mode.value} not supported by {self.name}. "
                f"Supported: {[m.value for m in caps.supported_modes]}"
            )

        if request.width > caps.max_resolution[0]:
            errors.append(f"Width {request.width} exceeds max {caps.max_resolution[0]}")

        if request.height > caps.max_resolution[1]:
            errors.append(f"Height {request.height} exceeds max {caps.max_resolution[1]}")

        if request.duration_seconds > caps.max_duration_seconds:
            errors.append(f"Duration {request.duration_seconds}s exceeds max {caps.max_duration_seconds}s")

        if request.negative_prompt and not caps.supports_negative_prompt:
            errors.append(f"{self.name} does not support negative prompts")

        if request.seed is not None and not caps.supports_seed:
            errors.append(f"{self.name} does not support seed parameter")

        return errors

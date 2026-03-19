#!/usr/bin/env python3
"""End-to-end demo: generate a video with Veo 3.1.

This script exercises the full VeoProvider flow as a real user would:
    1. Load API key from config
    2. Validate the key
    3. Submit a video generation request
    4. Poll until completion
    5. Download the generated video

Usage:
    # Set your API key
    export VEO_API_KEY="your-gemini-api-key"

    # Run the demo (from repo root)
    cd packages/ltx-pipelines
    PYTHONPATH=src python scripts/demo_veo.py

    # Or with a custom prompt
    PYTHONPATH=src python scripts/demo_veo.py --prompt "A cat playing piano"

    # Use the fast model
    PYTHONPATH=src python scripts/demo_veo.py --fast

    # Specify output path
    PYTHONPATH=src python scripts/demo_veo.py -o my_video.mp4
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

import httpx

# --- Bootstrap: avoid triggering torch-heavy ltx_pipelines/__init__.py ---
import types

_stub = types.ModuleType("ltx_pipelines")
_stub.__path__ = [str(Path(__file__).resolve().parents[1] / "src" / "ltx_pipelines")]  # type: ignore[attr-defined]
_stub.__package__ = "ltx_pipelines"
sys.modules.setdefault("ltx_pipelines", _stub)
# --- End bootstrap ---

from ltx_pipelines.providers.base import (  # noqa: E402
    TaskStatus,
    VideoGenerationRequest,
)
from ltx_pipelines.providers.veo import VEO_MODEL_FAST, VEO_MODEL_STANDARD, VeoProvider  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_demo(
    prompt: str,
    output_path: Path,
    *,
    fast: bool = False,
    duration: int = 4,
    aspect_ratio: str = "16:9",
    poll_interval: int = 10,
    max_wait: int = 300,
) -> bool:
    """Run the full Veo E2E flow.

    Returns True on success, False on failure.
    """
    model = VEO_MODEL_FAST if fast else VEO_MODEL_STANDARD
    print(f"\n{'='*60}")
    print(f"  Deep V Studio — Veo 3.1 E2E Demo")
    print(f"{'='*60}")
    print(f"  Model    : {model}")
    print(f"  Prompt   : {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Duration : {duration}s")
    print(f"  Aspect   : {aspect_ratio}")
    print(f"  Output   : {output_path}")
    print(f"{'='*60}\n")

    # --- Step 1: Initialize provider ---
    print("▶ Step 1: Initializing VeoProvider...")
    provider = VeoProvider(model=model)
    provider.config.extra["aspect_ratio"] = aspect_ratio
    print(f"  ✓ Provider initialized (base_url: {provider.base_url})")
    print(f"  ✓ Capabilities: {provider.capabilities}")

    # --- Step 2: Validate API key ---
    print("\n▶ Step 2: Validating API key...")
    is_valid = await provider.validate_api_key()
    if not is_valid:
        print("  ✗ API key validation FAILED.")
        print("    → Set VEO_API_KEY environment variable")
        print("    → Or add to ~/.config/deep-v-studio/providers.toml")
        return False
    print("  ✓ API key is valid.")

    # --- Step 3: Submit generation request ---
    print("\n▶ Step 3: Submitting video generation request...")
    request = VideoGenerationRequest(
        prompt=prompt,
        duration_seconds=float(duration),
    )
    result = await provider.generate_video(request)

    if result.status == TaskStatus.FAILED:
        print(f"  ✗ Generation request FAILED: {result.error_message}")
        return False

    print(f"  ✓ Request accepted. Operation: {result.task_id}")

    # --- Step 4: Poll for completion ---
    print(f"\n▶ Step 4: Polling for completion (every {poll_interval}s, max {max_wait}s)...")
    start_time = time.time()
    elapsed = 0.0

    while elapsed < max_wait:
        result = await provider.check_status(result.task_id)

        if result.status == TaskStatus.COMPLETED:
            elapsed = time.time() - start_time
            print(f"\n  ✓ Video generation COMPLETED in {elapsed:.0f}s!")
            break
        elif result.status == TaskStatus.FAILED:
            print(f"\n  ✗ Generation FAILED: {result.error_message}")
            return False
        else:
            elapsed = time.time() - start_time
            bar_len = int(min(elapsed / max_wait, 1.0) * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            print(f"  ⏳ [{bar}] {elapsed:.0f}s — status: {result.status.value}", end="\r")
            await asyncio.sleep(poll_interval)
    else:
        print(f"\n  ✗ Timed out after {max_wait}s")
        return False

    # --- Step 5: Download the video ---
    if result.video_url:
        print(f"\n▶ Step 5: Downloading video...")
        print(f"  URL: {result.video_url}")

        api_key = provider.config.resolve_api_key()
        headers = {"x-goog-api-key": api_key} if api_key else {}

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
                resp = await client.get(result.video_url, headers=headers)
                resp.raise_for_status()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(resp.content)

                size_mb = len(resp.content) / (1024 * 1024)
                print(f"  ✓ Saved to {output_path} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ✗ Download failed: {e}")
            print(f"  → You can manually download from: {result.video_url}")
            return False
    else:
        print("\n  ⚠ No video URL in response — generation may have completed without output.")
        return False

    print(f"\n{'='*60}")
    print(f"  ✅ E2E test PASSED — video saved to {output_path}")
    print(f"{'='*60}\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep V Studio — Veo 3.1 E2E Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--prompt",
        default="A serene mountain lake at sunrise, with mist rising from the water surface. A deer drinks at the water's edge. Cinematic, 4K quality.",
        help="Text prompt for video generation",
    )
    parser.add_argument(
        "-o", "--output",
        default="output/veo_demo.mp4",
        help="Output file path (default: output/veo_demo.mp4)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Use the fast model variant (lower quality, faster)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=4,
        choices=[4, 6, 8],
        help="Video duration in seconds (default: 4)",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["16:9", "9:16"],
        help="Video aspect ratio (default: 16:9)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between status polls (default: 10)",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=300,
        help="Maximum seconds to wait (default: 300)",
    )

    args = parser.parse_args()

    success = asyncio.run(
        run_demo(
            prompt=args.prompt,
            output_path=Path(args.output),
            fast=args.fast,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait,
        )
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

"""Provider configuration and API key management.

Loads API keys and provider settings with priority:
    1. Environment variable (e.g., VEO_API_KEY)
    2. .env file in project root
    3. Config file (~/.config/deep-v-studio/providers.toml)
"""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = Path.home() / ".config" / "deep-v-studio"
_DEFAULT_CONFIG_FILE = _DEFAULT_CONFIG_DIR / "providers.toml"


@dataclass
class ProviderConfig:
    """Configuration for a single provider.

    Handles API key resolution from multiple sources with clear priority.
    """

    provider_id: str
    api_key_env_var: str
    api_key: str | None = None
    base_url: str | None = None
    extra: dict[str, object] = field(default_factory=dict)

    def resolve_api_key(
        self,
        *,
        dotenv_path: Path | None = None,
        config_path: Path | None = None,
    ) -> str | None:
        """Resolve API key with priority: env → .env → config file.

        Args:
            dotenv_path: Path to .env file. Defaults to cwd/.env.
            config_path: Path to TOML config. Defaults to
                ~/.config/deep-v-studio/providers.toml.

        Returns:
            The resolved API key, or None if not found.
        """
        # 1. Already set explicitly
        if self.api_key:
            logger.debug("Using explicitly set API key for %s", self.provider_id)
            return self.api_key

        # 2. Environment variable
        env_val = os.environ.get(self.api_key_env_var)
        if env_val:
            logger.debug(
                "Resolved API key for %s from env var %s",
                self.provider_id,
                self.api_key_env_var,
            )
            self.api_key = env_val
            return env_val

        # 3. .env file
        resolved = self._load_from_dotenv(dotenv_path or Path.cwd() / ".env")
        if resolved:
            logger.debug("Resolved API key for %s from .env file", self.provider_id)
            self.api_key = resolved
            return resolved

        # 4. TOML config file
        resolved = self._load_from_toml(config_path or _DEFAULT_CONFIG_FILE)
        if resolved:
            logger.debug("Resolved API key for %s from config file", self.provider_id)
            self.api_key = resolved
            return resolved

        logger.warning(
            "No API key found for %s. Set %s or add to config.",
            self.provider_id,
            self.api_key_env_var,
        )
        return None

    def _load_from_dotenv(self, path: Path) -> str | None:
        """Parse a .env file for the API key variable."""
        if not path.is_file():
            return None

        try:
            for raw_line in path.read_text().splitlines():
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key == self.api_key_env_var:
                    return value
        except OSError:
            logger.debug("Could not read .env file at %s", path)
        return None

    def _load_from_toml(self, path: Path) -> str | None:
        """Load API key from TOML config under [providers.<id>]."""
        if not path.is_file():
            return None

        try:
            data = tomllib.loads(path.read_text())
            providers = data.get("providers", {})
            provider_section = providers.get(self.provider_id, {})
            return provider_section.get("api_key")
        except (OSError, Exception) as e:
            logger.debug("Could not read TOML config at %s: %s", path, e)
        return None


# Pre-configured configs for known providers
KNOWN_PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "veo": ProviderConfig(
        provider_id="veo",
        api_key_env_var="VEO_API_KEY",
    ),
    "seedance": ProviderConfig(
        provider_id="seedance",
        api_key_env_var="SEEDANCE_API_KEY",
    ),
    "nanobanana": ProviderConfig(
        provider_id="nanobanana",
        api_key_env_var="NANOBANANA_API_KEY",
    ),
    "nanobanana_pro": ProviderConfig(
        provider_id="nanobanana_pro",
        api_key_env_var="NANOBANANA_PRO_API_KEY",
    ),
}


def get_provider_config(provider_id: str) -> ProviderConfig:
    """Get or create a config for a provider.

    Args:
        provider_id: The provider identifier.

    Returns:
        A ProviderConfig instance (pre-configured for known providers,
        or with sensible defaults for unknown ones).
    """
    if provider_id in KNOWN_PROVIDER_CONFIGS:
        return KNOWN_PROVIDER_CONFIGS[provider_id]

    # Generate a sensible env var name for unknown providers
    env_var = f"{provider_id.upper()}_API_KEY"
    return ProviderConfig(provider_id=provider_id, api_key_env_var=env_var)

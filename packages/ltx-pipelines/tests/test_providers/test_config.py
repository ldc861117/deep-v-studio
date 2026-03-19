"""Tests for providers/config.py — API key resolution chain."""

from pathlib import Path

import pytest

from ltx_pipelines.providers.config import (
    KNOWN_PROVIDER_CONFIGS,
    ProviderConfig,
    get_provider_config,
)


class TestProviderConfig:
    def test_explicit_api_key(self) -> None:
        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="TEST_API_KEY",
            api_key="my-secret-key",
        )
        resolved = config.resolve_api_key()
        assert resolved == "my-secret-key"

    def test_env_var_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "env-key-value")
        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="TEST_API_KEY",
        )
        resolved = config.resolve_api_key()
        assert resolved == "env-key-value"

    def test_dotenv_resolution(self, tmp_path: Path) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text('MY_PROVIDER_KEY="dotenv-secret"\n')

        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="MY_PROVIDER_KEY",
        )
        resolved = config.resolve_api_key(dotenv_path=dotenv)
        assert resolved == "dotenv-secret"

    def test_dotenv_without_quotes(self, tmp_path: Path) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("MY_KEY=bare-value\n")

        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="MY_KEY",
        )
        resolved = config.resolve_api_key(dotenv_path=dotenv)
        assert resolved == "bare-value"

    def test_dotenv_skips_comments(self, tmp_path: Path) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("# comment\nMY_KEY=value\n")

        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="MY_KEY",
        )
        resolved = config.resolve_api_key(dotenv_path=dotenv)
        assert resolved == "value"

    def test_toml_resolution(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.toml"
        config_file.write_text('[providers.mycloud]\napi_key = "toml-secret"\n')

        config = ProviderConfig(
            provider_id="mycloud",
            api_key_env_var="MYCLOUD_API_KEY",
        )
        resolved = config.resolve_api_key(
            dotenv_path=tmp_path / "nonexistent.env",
            config_path=config_file,
        )
        assert resolved == "toml-secret"

    def test_priority_env_over_dotenv(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("PRIO_KEY", "from-env")
        dotenv = tmp_path / ".env"
        dotenv.write_text("PRIO_KEY=from-dotenv\n")

        config = ProviderConfig(
            provider_id="test",
            api_key_env_var="PRIO_KEY",
        )
        resolved = config.resolve_api_key(dotenv_path=dotenv)
        assert resolved == "from-env"  # env takes priority

    def test_no_key_found(self, tmp_path: Path) -> None:
        # Ensure env is clean
        config = ProviderConfig(
            provider_id="ghost",
            api_key_env_var="GHOST_NONEXISTENT_KEY_12345",
        )
        resolved = config.resolve_api_key(
            dotenv_path=tmp_path / "no.env",
            config_path=tmp_path / "no.toml",
        )
        assert resolved is None


class TestKnownProviderConfigs:
    def test_veo_config_exists(self) -> None:
        assert "veo" in KNOWN_PROVIDER_CONFIGS
        assert KNOWN_PROVIDER_CONFIGS["veo"].api_key_env_var == "VEO_API_KEY"

    def test_seedance_config_exists(self) -> None:
        assert "seedance" in KNOWN_PROVIDER_CONFIGS
        assert KNOWN_PROVIDER_CONFIGS["seedance"].api_key_env_var == "SEEDANCE_API_KEY"

    def test_nanobanana_configs_exist(self) -> None:
        assert "nanobanana" in KNOWN_PROVIDER_CONFIGS
        assert "nanobanana_pro" in KNOWN_PROVIDER_CONFIGS


class TestGetProviderConfig:
    def test_known_provider(self) -> None:
        config = get_provider_config("veo")
        assert config.provider_id == "veo"

    def test_unknown_provider_generates_env_var(self) -> None:
        config = get_provider_config("newmodel")
        assert config.provider_id == "newmodel"
        assert config.api_key_env_var == "NEWMODEL_API_KEY"

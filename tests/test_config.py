"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest
import yaml
from config import config, load_config

PORT = 6002
TRANSPORT = "sse"


class TestLoadConfig:
    """Test cases for load_config function."""

    def test_load_config_valid_file(self, temp_config_file: Path) -> None:
        """Test loading valid config file."""
        result = load_config(temp_config_file)

        assert result.server.port == PORT
        assert result.server.transport == TRANSPORT
        assert result.path_to_metadata.name == "test_metadata.yaml"
        assert result.path_to_ee_auth.name == "test_auth.json"

    def test_load_config_nonexistent_file(self) -> None:
        """Test loading nonexistent config file raises FileNotFoundError."""
        nonexistent_path = Path("/nonexistent/config.yaml")
        with pytest.raises(FileNotFoundError):
            load_config(nonexistent_path)

    def test_load_config_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises yaml.YAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                load_config(temp_path)
        finally:
            temp_path.unlink()

    def test_load_config_missing_required_fields(self) -> None:
        """Test loading config with missing required fields."""
        incomplete_config = {
            "server": {
                "port": 8080
                # Missing transport
            }
            # Missing path_to_metadata and path_to_ee_auth
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(incomplete_config, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises((KeyError, TypeError)):
                load_config(temp_path)
        finally:
            temp_path.unlink()

    def test_load_config_with_relative_paths(self) -> None:
        """Test loading config with relative paths."""
        config_data = {
            "server": {"port": 8080, "transport": "stdio"},
            "path_to_metadata": "relative/metadata.yaml",
            "path_to_ee_auth": "relative/auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert result.path_to_metadata.name == "metadata.yaml"
            assert result.path_to_ee_auth.name == "auth.json"
        finally:
            temp_path.unlink()

    def test_load_config_with_absolute_paths(self) -> None:
        """Test loading config with absolute paths."""
        config_data = {
            "server": {"port": 8080, "transport": "sse"},
            "path_to_metadata": "/absolute/path/to/metadata.yaml",
            "path_to_ee_auth": "/absolute/path/to/auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert str(result.path_to_metadata) == "/absolute/path/to/metadata.yaml"
            assert str(result.path_to_ee_auth) == "/absolute/path/to/auth.json"
        finally:
            temp_path.unlink()

    def test_load_config_empty_file(self) -> None:
        """Test loading empty config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            with pytest.raises((TypeError, AttributeError)):
                load_config(temp_path)
        finally:
            temp_path.unlink()

    def test_load_config_with_extra_fields(self) -> None:
        """Test loading config with extra fields (should be ignored)."""
        config_data = {
            "server": {"port": 8080, "transport": "stdio", "extra_field": "ignored"},
            "path_to_metadata": "metadata.yaml",
            "path_to_ee_auth": "auth.json",
            "extra_top_level": "also_ignored",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert result.server.port == 8080  # noqa: PLR2004
            assert result.server.transport == "stdio"
        finally:
            temp_path.unlink()


class TestConfigModule:
    """Test cases for the config module."""

    def test_config_object_exists(self) -> None:
        """Test that config object exists and has expected attributes."""
        assert hasattr(config, "server")
        assert hasattr(config, "path_to_metadata")
        assert hasattr(config, "path_to_ee_auth")

    def test_config_server_attributes(self) -> None:
        """Test that config.server has expected attributes."""
        assert hasattr(config.server, "port")
        assert hasattr(config.server, "transport")
        assert isinstance(config.server.port, int)
        assert isinstance(config.server.transport, str)

    def test_config_path_attributes(self) -> None:
        """Test that config paths are Path objects."""
        assert isinstance(config.path_to_metadata, Path)
        assert isinstance(config.path_to_ee_auth, Path)


class TestConfigEdgeCases:
    """Test edge cases for configuration."""

    def test_load_config_with_unicode_paths(self) -> None:
        """Test loading config with unicode characters in paths."""
        config_data = {
            "server": {"port": 8080, "transport": "stdio"},
            "path_to_metadata": "metadata_ñ_€_中文.yaml",
            "path_to_ee_auth": "auth_ñ_€_中文.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert "ñ" in result.path_to_metadata.name
            assert "€" in result.path_to_metadata.name
            assert "中文" in result.path_to_metadata.name
        finally:
            temp_path.unlink()

    def test_load_config_with_very_long_paths(self) -> None:
        """Test loading config with very long file paths."""
        long_name = "a" * 200
        config_data = {
            "server": {"port": 8080, "transport": "sse"},
            "path_to_metadata": f"{long_name}.yaml",
            "path_to_ee_auth": f"{long_name}.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert len(result.path_to_metadata.name) == 205  # 200 + ".yaml"  # noqa: PLR2004
            assert len(result.path_to_ee_auth.name) == 205  # 200 + ".json"  # noqa: PLR2004
        finally:
            temp_path.unlink()

    def test_load_config_with_minimum_port(self) -> None:
        """Test loading config with minimum valid port number."""
        config_data = {
            "server": {"port": 1, "transport": "stdio"},
            "path_to_metadata": "metadata.yaml",
            "path_to_ee_auth": "auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert result.server.port == 1  # noqa: PLR2004
        finally:
            temp_path.unlink()

    def test_load_config_with_maximum_port(self) -> None:
        """Test loading config with maximum valid port number."""
        config_data = {
            "server": {"port": 65535, "transport": "sse"},
            "path_to_metadata": "metadata.yaml",
            "path_to_ee_auth": "auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert result.server.port == 65535  # noqa: PLR2004
        finally:
            temp_path.unlink()

    def test_load_config_with_nested_directory_paths(self) -> None:
        """Test loading config with deeply nested directory paths."""
        config_data = {
            "server": {"port": 8080, "transport": "streamable-http"},
            "path_to_metadata": "deep/nested/directory/structure/metadata.yaml",
            "path_to_ee_auth": "another/deep/nested/path/auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            result = load_config(temp_path)
            assert "deep/nested" in str(result.path_to_metadata)
            assert "another/deep" in str(result.path_to_ee_auth)
        finally:
            temp_path.unlink()


class TestConfigValidation:
    """Test cases for config validation."""

    def test_load_config_invalid_transport(self) -> None:
        """Test loading config with invalid transport value."""
        config_data = {
            "server": {"port": 8080, "transport": "invalid_transport"},
            "path_to_metadata": "metadata.yaml",
            "path_to_ee_auth": "auth.json",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            # This should raise a validation error due to invalid transport
            with pytest.raises((ValueError, TypeError)):
                load_config(temp_path)
        finally:
            temp_path.unlink()

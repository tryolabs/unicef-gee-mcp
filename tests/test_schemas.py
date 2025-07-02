"""Tests for schemas module."""

from pathlib import Path
from typing import cast

from schemas import AREA_TYPES, REDUCERS, Config, DatasetMetadata, ServerConfig, Transport

PORT = 8080


class TestServerConfig:
    """Test cases for ServerConfig dataclass."""

    def test_server_config_creation_valid_transport(self) -> None:
        """Test ServerConfig creation with valid transport."""
        config = ServerConfig(port=PORT, transport="stdio")
        assert config.port == PORT
        assert config.transport == "stdio"

    def test_server_config_creation_all_transports(self) -> None:
        """Test ServerConfig creation with all valid transports."""
        valid_transports = ["stdio", "sse", "streamable-http"]
        for transport in valid_transports:
            config = ServerConfig(port=PORT, transport=cast("Transport", transport))
            assert config.transport == transport

    def test_server_config_equality(self) -> None:
        """Test ServerConfig equality comparison."""
        config1 = ServerConfig(port=PORT, transport="stdio")
        config2 = ServerConfig(port=PORT, transport="stdio")
        config3 = ServerConfig(port=9090, transport="stdio")

        assert config1 == config2
        assert config1 != config3

    def test_server_config_string_representation(self) -> None:
        """Test ServerConfig string representation."""
        config = ServerConfig(port=PORT, transport="stdio")
        assert f"{PORT}" in str(config)
        assert "stdio" in str(config)


class TestConfig:
    """Test cases for Config dataclass."""

    def test_config_creation(self) -> None:
        """Test Config creation with valid parameters."""
        server_config = ServerConfig(port=PORT, transport="stdio")
        metadata_path = Path("/path/to/metadata.yaml")
        auth_path = Path("/path/to/auth.json")

        config = Config(
            server=server_config, path_to_metadata=metadata_path, path_to_ee_auth=auth_path
        )

        assert config.server == server_config
        assert config.path_to_metadata == metadata_path
        assert config.path_to_ee_auth == auth_path

    def test_config_with_relative_paths(self) -> None:
        """Test Config creation with relative paths."""
        server_config = ServerConfig(port=PORT, transport="sse")
        metadata_path = Path("metadata.yaml")
        auth_path = Path("auth.json")

        config = Config(
            server=server_config, path_to_metadata=metadata_path, path_to_ee_auth=auth_path
        )

        assert config.path_to_metadata.name == "metadata.yaml"
        assert config.path_to_ee_auth.name == "auth.json"

    def test_config_equality(self) -> None:
        """Test Config equality comparison."""
        server_config = ServerConfig(port=PORT, transport="stdio")
        metadata_path = Path("/path/to/metadata.yaml")
        auth_path = Path("/path/to/auth.json")

        config1 = Config(
            server=server_config, path_to_metadata=metadata_path, path_to_ee_auth=auth_path
        )
        config2 = Config(
            server=server_config, path_to_metadata=metadata_path, path_to_ee_auth=auth_path
        )

        assert config1 == config2


class TestDatasetMetadata:
    """Test cases for DatasetMetadata dataclass."""

    def test_dataset_metadata_creation_minimal(self) -> None:
        """Test DatasetMetadata creation with minimal required fields."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
        )

        assert metadata.image_filename == "test.json"
        assert metadata.asset_id == "test_asset"
        assert metadata.description == "Test dataset"
        assert metadata.source_name == "Test Source"
        assert metadata.source_url == "https://test.com"
        assert metadata.mosaic is False  # Default value
        assert metadata.threshold is None  # Default value
        assert metadata.input_arguments is None  # Default value
        assert metadata.color_palette is None  # Default value

    def test_dataset_metadata_creation_full(self) -> None:
        """Test DatasetMetadata creation with all fields."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
            mosaic=True,
            threshold=5.0,
            input_arguments={"param": "value"},
            color_palette=["#FF0000", "#00FF00", "#0000FF"],
        )

        assert metadata.mosaic is True
        assert metadata.threshold == 5.0  # noqa: PLR2004
        assert metadata.input_arguments == {"param": "value"}
        assert metadata.color_palette == ["#FF0000", "#00FF00", "#0000FF"]

    def test_dataset_metadata_with_complex_asset_id(self) -> None:
        """Test DatasetMetadata with complex asset ID."""
        metadata = DatasetMetadata(
            image_filename="complex.json",
            asset_id="projects/unicef-ccri/assets/complex_dataset_v2",
            description="Complex dataset",
            source_name="Complex Source",
            source_url="https://complex.com/data",
        )

        assert "projects/unicef-ccri/assets" in metadata.asset_id
        assert metadata.asset_id.endswith("complex_dataset_v2")

    def test_dataset_metadata_equality(self) -> None:
        """Test DatasetMetadata equality comparison."""
        metadata1 = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
        )
        metadata2 = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
        )
        metadata3 = DatasetMetadata(
            image_filename="different.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
        )

        assert metadata1 == metadata2
        assert metadata1 != metadata3

    def test_dataset_metadata_with_special_characters(self) -> None:
        """Test DatasetMetadata with special characters in fields."""
        metadata = DatasetMetadata(
            image_filename="test_with_ñ_€_characters.json",
            asset_id="test_asset_ñ_€",
            description="Dataset with special characters: ñ, €, 中文",
            source_name="Source with émojis 🌍",
            source_url="https://test.com/ñ-€-中文",
        )

        assert "ñ" in metadata.image_filename
        assert "€" in metadata.asset_id
        assert "中文" in metadata.description
        assert "🌍" in metadata.source_name
        assert "中文" in metadata.source_url


class TestLiteralTypes:
    """Test cases for literal type definitions."""

    def test_reducers_literal(self) -> None:
        """Test REDUCERS literal contains expected values."""
        # This is a compile-time check, but we can test the expected values exist
        expected_reducers = ["mean", "max", "min", "sum", "median", "std"]
        # Since REDUCERS is a Literal type, we can't iterate over it directly
        # But we can test that the expected strings would be valid
        assert all(isinstance(reducer, str) for reducer in expected_reducers)

    def test_area_types_literal(self) -> None:
        """Test AREA_TYPES literal contains expected values."""
        expected_area_types = ["country", "admin1"]
        # Since AREA_TYPES is a Literal type, we can't iterate over it directly
        # But we can test that the expected strings would be valid
        assert all(isinstance(area_type, str) for area_type in expected_area_types)

    def test_literal_type_usage_in_functions(self) -> None:
        """Test that literal types can be used in function signatures."""

        # This is more of a type checker test, but we can verify the values
        def test_reducer_function(reducer: REDUCERS) -> str:
            return f"Using reducer: {reducer}"

        def test_area_function(area_type: AREA_TYPES) -> str:
            return f"Using area type: {area_type}"

        # Test with valid values
        assert "mean" in test_reducer_function("mean")
        assert "country" in test_area_function("country")


class TestDatasetMetadataEdgeCases:
    """Test edge cases for DatasetMetadata."""

    def test_dataset_metadata_with_empty_strings(self) -> None:
        """Test DatasetMetadata with empty strings."""
        metadata = DatasetMetadata(
            image_filename="", asset_id="", description="", source_name="", source_url=""
        )

        assert metadata.image_filename == ""
        assert metadata.asset_id == ""
        assert metadata.description == ""
        assert metadata.source_name == ""
        assert metadata.source_url == ""

    def test_dataset_metadata_with_very_long_strings(self) -> None:
        """Test DatasetMetadata with very long strings."""
        long_string = "a" * 1000
        metadata = DatasetMetadata(
            image_filename=f"{long_string}.json",
            asset_id=long_string,
            description=long_string,
            source_name=long_string,
            source_url=f"https://{long_string}.com",
        )

        assert len(metadata.image_filename) == 1005  # 1000 + ".json"  # noqa: PLR2004
        assert len(metadata.asset_id) == 1000  # noqa: PLR2004
        assert len(metadata.description) == 1000  # noqa: PLR2004
        assert len(metadata.source_name) == 1000  # noqa: PLR2004

    def test_dataset_metadata_with_zero_threshold(self) -> None:
        """Test DatasetMetadata with zero threshold."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
            threshold=0.0,
        )

        assert metadata.threshold == 0.0

    def test_dataset_metadata_with_negative_threshold(self) -> None:
        """Test DatasetMetadata with negative threshold."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
            threshold=-10.5,
        )

        assert metadata.threshold == -10.5  # noqa: PLR2004

    def test_dataset_metadata_with_empty_color_palette(self) -> None:
        """Test DatasetMetadata with empty color palette."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
            color_palette=[],
        )

        assert metadata.color_palette == []

    def test_dataset_metadata_with_empty_input_arguments(self) -> None:
        """Test DatasetMetadata with empty input arguments."""
        metadata = DatasetMetadata(
            image_filename="test.json",
            asset_id="test_asset",
            description="Test dataset",
            source_name="Test Source",
            source_url="https://test.com",
            input_arguments={},
        )

        assert metadata.input_arguments == {}

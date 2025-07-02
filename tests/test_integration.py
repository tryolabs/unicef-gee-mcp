"""Integration tests for the MCP server."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestMCPServerIntegration:
    """Integration tests for the MCP server tools."""

    @patch("initialize.ee")
    def test_get_all_datasets_and_metadata_tool(
        self, mock_ee: MagicMock, temp_metadata_file: Path
    ) -> None:
        """Test the get_all_datasets_and_metadata MCP tool."""
        with patch("config.config") as mock_config:
            mock_config.path_to_metadata = temp_metadata_file

            # Call the MCP tool function directly
            from server import get_all_datasets_and_metadata

            result = get_all_datasets_and_metadata()

            assert "datasets" in result
            assert isinstance(result["datasets"], dict)
            assert "test_dataset" in result["datasets"]

    @patch("initialize.ee")
    @patch("server.ee")
    def test_get_dataset_image_tool(
        self,
        mock_server_ee: MagicMock,
        mock_init_ee: MagicMock,
        temp_metadata_file: Path,
        mock_image: MagicMock,
    ) -> None:
        """Test the get_dataset_image_and_metadata MCP tool."""
        mock_server_ee.Image.return_value = mock_image

        with patch("config.config") as mock_config:
            mock_config.path_to_metadata = temp_metadata_file

            from server import get_dataset_image

            result = get_dataset_image("test_dataset")

            assert "image_json" in result
            assert result["image_json"] == mock_image.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_mask_image_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test the mask_image MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_image

        from server import mask_image

        image_json = '{"type": "Image", "asset_id": "test"}'
        mask_json = '{"type": "Image", "asset_id": "mask"}'

        result = mask_image(image_json, mask_json)

        assert "image_json" in result
        assert result["image_json"] == mock_image.updateMask.return_value.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_filter_image_by_threshold_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test the filter_image_by_threshold MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_image

        from server import filter_image_by_threshold

        image_json = '{"type": "Image", "asset_id": "test"}'
        threshold = 5.0

        result = filter_image_by_threshold(image_json, threshold)

        assert "image_json" in result
        assert result["image_json"] == mock_image.gt.return_value.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_union_binary_images_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test the union_binary_images MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_image

        from server import union_binary_images

        binary_images = [
            '{"type": "Image", "asset_id": "binary1"}',
            '{"type": "Image", "asset_id": "binary2"}',
        ]

        result = union_binary_images(binary_images)

        assert "image_json" in result
        assert result["image_json"] == mock_image.Or.return_value.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_intersect_binary_images_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test the intersect_binary_images MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_image

        from server import intersect_binary_images

        binary_images = [
            '{"type": "Image", "asset_id": "binary1"}',
            '{"type": "Image", "asset_id": "binary2"}',
        ]

        result = intersect_binary_images(binary_images)

        assert "image_json" in result
        assert result["image_json"] == mock_image.And.return_value.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_intersect_feature_collections_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_feature_collection: MagicMock
    ) -> None:
        """Test the intersect_feature_collections MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_feature_collection

        from server import intersect_feature_collections

        feature_collections = [
            '{"type": "FeatureCollection", "features": []}',
            '{"type": "FeatureCollection", "features": []}',
        ]

        result = intersect_feature_collections(feature_collections)

        assert "feature_collection_json" in result
        assert result["feature_collection_json"] == mock_feature_collection.serialize.return_value

    @patch("initialize.ee")
    @patch("server.ee")
    def test_merge_feature_collections_tool(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_feature_collection: MagicMock
    ) -> None:
        """Test the merge_feature_collections MCP tool."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_feature_collection

        from server import merge_feature_collections

        feature_collections = [
            '{"type": "FeatureCollection", "features": []}',
            '{"type": "FeatureCollection", "features": []}',
        ]

        result = merge_feature_collections(feature_collections)

        assert "feature_collection_json" in result
        assert (
            result["feature_collection_json"]
            == mock_feature_collection.merge.return_value.serialize.return_value
        )

    @patch("initialize.ee")
    @patch("server.ee")
    def test_reduce_image_tool(
        self,
        mock_server_ee: MagicMock,
        mock_init_ee: MagicMock,
        mock_image: MagicMock,
        mock_feature_collection: MagicMock,
    ) -> None:
        """Test the reduce_image MCP tool."""
        mock_server_ee.deserializer.fromJSON.side_effect = [mock_image, mock_feature_collection]
        mock_server_ee.Reducer.mean.return_value = MagicMock()

        from server import reduce_image

        image_json = '{"type": "Image", "asset_id": "test"}'
        fc_json = '{"type": "FeatureCollection", "features": []}'

        result = reduce_image(image_json, fc_json, "mean", 100.0)

        assert "aggregation_result" in result
        assert result["aggregation_result"] == 10.5  # noqa: PLR2004

    @patch("initialize.ee")
    @patch("server.ee")
    @patch("server.pycountry")
    def test_get_zone_of_area_tool(
        self,
        mock_pycountry: MagicMock,
        mock_server_ee: MagicMock,
        mock_init_ee: MagicMock,
        mock_feature_collection: MagicMock,
    ) -> None:
        """Test the get_zone_of_area MCP tool."""
        # Mock pycountry
        country_mock = MagicMock()
        country_mock.name = "France"
        mock_pycountry.countries.get.return_value = country_mock

        mock_server_ee.FeatureCollection.return_value = mock_feature_collection

        with patch("server.geemap") as mock_geemap:
            mock_geemap.ee_to_geojson.return_value = {"type": "FeatureCollection"}

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value = MagicMock()

                from server import get_zone_of_area

                result = get_zone_of_area("FRA", "country")

                assert "zone_path" in result
                assert result["zone_path"].endswith(".geojson")


class TestMCPServerErrorHandling:
    """Test error handling in MCP server tools."""

    @patch("initialize.ee")
    def test_get_dataset_image_invalid_dataset(
        self, mock_ee: MagicMock, temp_metadata_file: Path
    ) -> None:
        """Test error handling for invalid dataset in get_dataset_image."""
        with patch("config.config") as mock_config:
            mock_config.path_to_metadata = temp_metadata_file

            from server import get_dataset_image

            with pytest.raises(ValueError, match="Invalid dataset"):
                get_dataset_image("nonexistent_dataset")

    @patch("initialize.ee")
    @patch("server.ee")
    def test_mask_image_invalid_json(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock
    ) -> None:
        """Test error handling for invalid JSON in mask_image."""
        mock_server_ee.deserializer.fromJSON.side_effect = ValueError("Invalid JSON")

        from server import mask_image

        with pytest.raises(ValueError, match="Invalid JSON"):
            mask_image("invalid_json", '{"type": "Image", "asset_id": "mask"}')

    @patch("initialize.ee")
    @patch("server.pycountry")
    def test_get_zone_of_area_invalid_country(
        self, mock_pycountry: MagicMock, mock_init_ee: MagicMock
    ) -> None:
        """Test error handling for invalid country in get_zone_of_area."""
        mock_pycountry.countries.get.return_value = None

        from server import get_zone_of_area

        with pytest.raises(ValueError, match="Country with alpha-3 code"):
            get_zone_of_area("INVALID", "country")


class TestMCPServerEdgeCases:
    """Test edge cases for MCP server tools."""

    @patch("initialize.ee")
    @patch("server.ee")
    def test_filter_image_with_extreme_thresholds(
        self, mock_server_ee: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test filtering with extreme threshold values."""
        mock_server_ee.deserializer.fromJSON.return_value = mock_image

        from server import filter_image_by_threshold

        image_json = '{"type": "Image", "asset_id": "test"}'

        # Test with very large threshold
        result_large = filter_image_by_threshold(image_json, 1e10)
        assert "image_json" in result_large

        # Test with very small threshold
        result_small = filter_image_by_threshold(image_json, -1e10)
        assert "image_json" in result_small

    @patch("initialize.ee")
    @patch("handlers.fromJSON")
    def test_union_with_many_images(
        self, mock_from_json: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test union with many binary images."""
        mock_from_json.return_value = mock_image

        from server import union_binary_images

        # Create many binary images
        binary_images = [f'{{"type": "Image", "asset_id": "binary{i}"}}' for i in range(10)]

        result = union_binary_images(binary_images)

        assert "image_json" in result
        assert mock_from_json.call_count == 10  # noqa: PLR2004

    @patch("initialize.ee")
    @patch("handlers.fromJSON")
    @patch("handlers.Reducer")
    def test_reduce_image_with_different_reducers(
        self,
        mock_reducer: MagicMock,
        mock_from_json: MagicMock,
        mock_init_ee: MagicMock,
        mock_image: MagicMock,
        mock_feature_collection: MagicMock,
    ) -> None:
        """Test reduce_image with different reducer types."""
        mock_from_json.side_effect = [mock_image, mock_feature_collection] * 6

        # Mock all reducers
        mock_reducer.mean.return_value = MagicMock()
        mock_reducer.max.return_value = MagicMock()
        mock_reducer.min.return_value = MagicMock()
        mock_reducer.sum.return_value = MagicMock()
        mock_reducer.median.return_value = MagicMock()
        mock_reducer.stdDev.return_value = MagicMock()

        from server import reduce_image

        image_json = '{"type": "Image", "asset_id": "test"}'
        fc_json = '{"type": "FeatureCollection", "features": []}'

        reducers = ["mean", "max", "min", "sum", "median", "std"]

        for reducer in reducers:
            result = reduce_image(image_json, fc_json, reducer, 100.0)  # type: ignore[arg-type]
            assert "aggregation_result" in result
            assert isinstance(result["aggregation_result"], float)

    @patch("initialize.ee")
    @patch("handlers.fromJSON")
    def test_tools_with_unicode_data(
        self, mock_from_json: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test tools with unicode characters in JSON data."""
        mock_from_json.return_value = mock_image

        from server import filter_image_by_threshold

        # JSON with unicode characters
        unicode_json = (
            '{"type": "Image", "asset_id": "test_ñ_€_中文", "description": "Unicode test 🌍"}'
        )

        result = filter_image_by_threshold(unicode_json, 5.0)

        assert "image_json" in result
        assert result["image_json"] == mock_image.gt.return_value.serialize.return_value


class TestMCPServerPerformance:
    """Test performance-related aspects of MCP server tools."""

    @patch("initialize.ee")
    @patch("handlers.fromJSON")
    def test_tools_with_large_json_data(
        self, mock_from_json: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test tools with large JSON data structures."""
        mock_from_json.return_value = mock_image

        from server import filter_image_by_threshold

        # Create large JSON with many properties
        large_properties = {f"prop_{i}": f"value_{i}" for i in range(1000)}
        large_json_dict = {"type": "Image", "asset_id": "test", "properties": large_properties}
        large_json = json.dumps(large_json_dict)

        result = filter_image_by_threshold(large_json, 5.0)

        assert "image_json" in result
        # Verify the large JSON was processed correctly
        mock_from_json.assert_called_once()

    @patch("initialize.ee")
    @patch("handlers.fromJSON")
    def test_concurrent_tool_calls_simulation(
        self, mock_from_json: MagicMock, mock_init_ee: MagicMock, mock_image: MagicMock
    ) -> None:
        """Simulate concurrent calls to tools (sequential execution for testing)."""
        mock_from_json.return_value = mock_image

        from server import filter_image_by_threshold

        image_json = '{"type": "Image", "asset_id": "test"}'

        results: list[dict[str, Any]] = [
            filter_image_by_threshold(image_json, float(i)) for i in range(5)
        ]
        # All calls should succeed
        assert len(results) == 5  # noqa: PLR2004
        for result in results:
            assert "image_json" in result

        # Verify all calls were made
        assert mock_from_json.call_count == 5  # noqa: PLR2004

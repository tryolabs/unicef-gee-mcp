"""Tests for handlers module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import handlers
import pytest
from constants import BASE_ASSETS_PATH
from initialize import initialize_ee

initialize_ee(Path("ee_auth.json"))


class TestHandleGetAllDatasetsAndMetadata:
    """Test cases for handle_get_all_datasets_and_metadata function."""

    def test_handle_get_all_datasets_and_metadata_success(self, temp_metadata_file: Path) -> None:
        """Test successful retrieval of all datasets and metadata."""
        result = handlers.handle_get_all_datasets_and_metadata(temp_metadata_file)

        assert isinstance(result, dict)
        assert "test_dataset" in result
        assert "mosaic_dataset" in result
        assert result["test_dataset"].asset_id == f"{BASE_ASSETS_PATH}/test_asset"
        assert result["mosaic_dataset"].mosaic is True

    def test_handle_get_all_datasets_and_metadata_nonexistent_file(self) -> None:
        """Test handling of nonexistent metadata file."""
        nonexistent_path = Path("/nonexistent/metadata.yaml")
        with pytest.raises(FileNotFoundError):
            handlers.handle_get_all_datasets_and_metadata(nonexistent_path)

    def test_handle_get_all_datasets_and_metadata_empty_file(self) -> None:
        """Test handling of empty metadata file."""
        import tempfile

        import yaml

        empty_metadata = {}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(empty_metadata, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises((KeyError, TypeError)):
                handlers.handle_get_all_datasets_and_metadata(temp_path)
        finally:
            temp_path.unlink()


class TestHandleGetDatasetImage:
    """Test cases for handle_get_dataset_image function."""

    @patch("handlers.ee")
    def test_handle_get_dataset_image_success_non_mosaic(
        self, mock_ee: MagicMock, temp_metadata_file: Path, mock_image: MagicMock
    ) -> None:
        """Test successful retrieval of non-mosaic dataset image."""
        mock_ee.Image.return_value = mock_image

        result = handlers.handle_get_dataset_image("test_dataset", temp_metadata_file)
        assert result == mock_image.serialize.return_value

    @patch("handlers.ee")
    def test_handle_get_dataset_image_success_mosaic(
        self, mock_ee: MagicMock, temp_metadata_file: Path, mock_image_collection: MagicMock
    ) -> None:
        """Test successful retrieval of mosaic dataset image."""
        mock_ee.ImageCollection.return_value = mock_image_collection

        result = handlers.handle_get_dataset_image("mosaic_dataset", temp_metadata_file)

        assert result == mock_image_collection.mosaic.return_value.serialize.return_value

    def test_handle_get_dataset_image_invalid_dataset(self, temp_metadata_file: Path) -> None:
        """Test handling of invalid dataset name."""
        with pytest.raises(KeyError):
            handlers.handle_get_dataset_image("nonexistent_dataset", temp_metadata_file)

    def test_handle_get_dataset_image_nonexistent_metadata_file(self) -> None:
        """Test handling of nonexistent metadata file."""
        nonexistent_path = Path("/nonexistent/metadata.yaml")
        with pytest.raises(FileNotFoundError):
            handlers.handle_get_dataset_image("test_dataset", nonexistent_path)


class TestHandleMaskImage:
    """Test cases for handle_mask_image function."""

    @patch("handlers.ee")
    def test_handle_mask_image_success(self, mock_ee: MagicMock, mock_image: MagicMock) -> None:
        """Test successful image masking."""
        image_json = mock_image.serialize.return_value
        mask_json = mock_image.serialize.return_value

        result = handlers.handle_mask_image(image_json, mask_json)

        assert isinstance(result, str)


class TestHandleFilterImageByThreshold:
    """Test cases for handle_filter_image_by_threshold function."""

    @patch("handlers.ee")
    def test_handle_filter_image_by_threshold_success(
        self, mock_ee: MagicMock, mock_image_gt: MagicMock
    ) -> None:
        """Test successful image filtering by threshold."""
        image_json = (
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Image.load", "arguments": '
            '{"id": {"constantValue": "projects/unicef-ccri/assets/test_asset"}}}}}}'
        )
        threshold = 5.0

        result = handlers.handle_filter_image_by_threshold(image_json, threshold)

        assert result == mock_image_gt.gt.return_value

    @patch("handlers.ee")
    def test_handle_filter_image_by_threshold_invalid_image(self, mock_ee: MagicMock) -> None:
        """Test handling of invalid image JSON."""
        mock_ee.deserializer.fromJSON.side_effect = ValueError("Invalid image")

        image_json = '{"invalid": "json"}'
        threshold = 5.0

        with pytest.raises(KeyError):
            handlers.handle_filter_image_by_threshold(image_json, threshold)


class TestHandleUnionBinaryImages:
    """Test cases for handle_union_binary_images function."""

    @patch("handlers.ee")
    def test_handle_union_binary_images_success(
        self, mock_ee: MagicMock, mock_image_or: MagicMock
    ) -> None:
        """Test successful union of binary images."""
        binary_images = [
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Image.load", "arguments": '
            '{"id": {"constantValue": "projects/unicef-ccri/assets/binary1"}}}}}}',
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Image.load", "arguments": '
            '{"id": {"constantValue": "projects/unicef-ccri/assets/binary2"}}}}}}',
        ]

        result = handlers.handle_union_binary_images(binary_images)

        assert result == mock_image_or.Or.return_value

    def test_handle_union_binary_images_empty_list(self) -> None:
        """Test union with empty list."""
        binary_images: list[str] = []

        with pytest.raises((IndexError, ValueError)):
            handlers.handle_union_binary_images(binary_images)


class TestHandleIntersectBinaryImages:
    """Test cases for handle_intersect_binary_images function."""

    @patch("handlers.ee")
    def test_handle_intersect_binary_images_success(
        self, mock_ee: MagicMock, mock_image_and: MagicMock
    ) -> None:
        """Test successful intersection of binary images."""
        binary_images = [
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Image.load", "arguments": '
            '{"id": {"constantValue": "projects/unicef-ccri/assets/binary1"}}}}}}',
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Image.load", "arguments": '
            '{"id": {"constantValue": "projects/unicef-ccri/assets/binary2"}}}}}}',
        ]

        result = handlers.handle_intersect_binary_images(binary_images)

        assert result == mock_image_and.And.return_value


class TestHandleIntersectFeatureCollections:
    """Test cases for handle_intersect_feature_collections function."""

    @patch("handlers.ee")
    def test_handle_intersect_feature_collections_success(
        self, mock_ee: MagicMock, mock_feature_collection_intersect: MagicMock
    ) -> None:
        """Test successful intersection of feature collections."""
        mock_ee.deserializer.fromJSON.return_value = mock_feature_collection_intersect

        feature_collections: list[str] = [
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Collection.loadTable", "arguments": '
            '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm0_wfp"}}}}}}',
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Collection.loadTable", "arguments": '
            '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm1_wfp"}}}}}}',
        ]

        result = handlers.handle_intersect_feature_collections(feature_collections)

        assert result == mock_feature_collection_intersect.serialize.return_value


class TestHandleMergeFeatureCollections:
    """Test cases for handle_merge_feature_collections function."""

    @patch("handlers.ee")
    def test_handle_merge_feature_collections_success(
        self, mock_ee: MagicMock, mock_feature_collection_merge: MagicMock
    ) -> None:
        """Test successful merging of feature collections."""
        mock_ee.deserializer.fromJSON.return_value = mock_feature_collection_merge

        feature_collections: list[str] = [
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Collection.loadTable", "arguments": '
            '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm0_wfp"}}}}}}',
            '{"result": "0", "values": {"0": {"functionInvocationValue": '
            '{"functionName": "Collection.loadTable", "arguments": '
            '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm0_wfp"}}}}}}',
        ]

        result = handlers.handle_merge_feature_collections(feature_collections)

        assert result == mock_feature_collection_merge.serialize.return_value


class TestHandleGetZoneOfArea:
    """Test cases for handle_get_zone_of_area function."""

    @patch("handlers.ee")
    @patch("handlers.FeatureCollection")
    @patch("handlers.get_country_code")
    def test_handle_get_zone_of_area_country_success(
        self,
        mock_get_country_code: MagicMock,
        mock_feature_collection: MagicMock,
        mock_ee: MagicMock,
        mock_boundry_json: MagicMock,
    ) -> None:
        """Test successful retrieval of country zone."""
        mock_get_country_code.return_value = "URY"
        mock_feature_collection.return_value = mock_boundry_json

        result = handlers.handle_get_zone_of_area("URY", "country")

        assert result == mock_boundry_json.serialize.return_value

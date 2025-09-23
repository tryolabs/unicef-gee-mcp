"""Integration tests for the MCP server endpoints."""

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from ee.feature import Feature
from ee.featurecollection import FeatureCollection
from ee.geometry import Geometry
from ee.image import Image

from ee_mcp.server import (
    filter_image_by_threshold,
    get_all_datasets_and_metadata,
    get_dataset_image,
    get_zone_of_area,
    intersect_binary_images,
    intersect_feature_collections,
    mask_image,
    merge_feature_collections,
    reduce_image,
    union_binary_images,
)
from ee_mcp.utils import load_ee_object, save_ee_object


@pytest.fixture(name="test_metadata_file")
def test_metadata_file() -> Path:
    """Create a temporary metadata file with real test data."""
    test_metadata = {
        "datasets": {
            "river_flood": {
                "asset_id": "users/unicef-ccri/Flood_hazard_th_2023_CEMS_GLOFAS_GL_rp_100",
                "description": "Test flood hazard dataset",
                "source_name": "GLOFAS",
                "source_url": "https://cds.climate.copernicus.eu/cdsapp#!/dataset/cems-glofas-reforecast",
                "mosaic": False,
                "threshold": 0.5,
                "color_palette": ["#0000FF", "#FF0000"],
            },
            "agricultural_drought": {
                "asset_id": "users/unicef-ccri/agricultural_drought",
                "description": "Test drought dataset",
                "source_name": "ERA5",
                "source_url": "https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
                "mosaic": False,
                "threshold": 75.0,
                "color_palette": ["#00FF00", "#FF0000"],
            },
            "children_population": {
                "asset_id": "users/unicef-ccri/population_children_under_5_2020_100_m",
                "description": "Test population dataset",
                "source_name": "WorldPop",
                "source_url": "https://www.worldpop.org/",
                "mosaic": False,
                "threshold": 1.0,
                "color_palette": ["#FFFFFF", "#000000"],
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(test_metadata, f)
        return Path(f.name)


@pytest.fixture(name="rectangle_test_data")
def rectangle_test_data() -> dict[str, str]:
    """Create two overlapping rectangles and save them to tests/data directory."""
    # Create two overlapping rectangles
    rectangle_1_geometry: Geometry = Geometry.Rectangle([-103, 39, -102, 38])  # type: ignore[arg-type]
    rectangle_2_geometry: Geometry = Geometry.Rectangle([-103, 38.5, -102, 37.5])  # type: ignore[arg-type]
    rectangle_1 = FeatureCollection([Feature(rectangle_1_geometry)])
    rectangle_2 = FeatureCollection([Feature(rectangle_2_geometry)])

    return {
        "rectangle_1": rectangle_1.serialize(),
        "rectangle_2": rectangle_2.serialize(),
    }


@pytest.fixture(name="binary_image_test_data")
def binary_image_test_data() -> dict[str, str | int]:
    scale = 47000
    horizontal_rectangle_geometry: Geometry = Geometry.Rectangle([-103, 39, -102, 38.5])  # type: ignore[arg-type]
    vertical_rectangle_geometry: Geometry = Geometry.Rectangle([-103, 39, -102.5, 38])  # type: ignore[arg-type]
    horizontal_rectangle = FeatureCollection([Feature(horizontal_rectangle_geometry)])
    vertical_rectangle = FeatureCollection([Feature(vertical_rectangle_geometry)])

    # Create binary image that is 0 everywhere except 1 in small rectangle
    binary_image_horizontal = (
        Image(0).paint(horizontal_rectangle, 1).reproject(crs="EPSG:4326", scale=scale)
    )
    binary_image_vertical = (
        Image(0).paint(vertical_rectangle, 1).reproject(crs="EPSG:4326", scale=scale)
    )

    return {
        "horizontal_rectangle": horizontal_rectangle.serialize(),
        "vertical_rectangle": vertical_rectangle.serialize(),
        "binary_image_horizontal": binary_image_horizontal.serialize(),
        "binary_image_vertical": binary_image_vertical.serialize(),
        "scale": scale,
    }


def check_coordinates_match(
    actual_feature_collection: str,
    expected_coords: list[list[float]],
    tolerance: float = 1e-6,
) -> tuple[bool, list[list[float]]]:
    """Check if actual coordinates match expected coordinates with a tolerance.

    Args:
        actual_feature_collection: JSON string of the actual feature collection
        expected_coords: List of expected coordinate pairs [[x1, y1], [x2, y2], ...]
        tolerance: Numerical tolerance for coordinate comparison

    Returns:
        bool: True if coordinates match within tolerance
    """
    actual_feature_collection_info: Any = load_ee_object(actual_feature_collection).getInfo()

    coords: Any = actual_feature_collection_info["features"][0]["geometry"]["coordinates"][0]

    # Extract the min/max coordinates
    x_coords: list[float] = [coord[0] for coord in coords]
    y_coords: list[float] = [coord[1] for coord in coords]
    min_x: float = min(x_coords)
    max_x: float = max(x_coords)
    min_y: float = min(y_coords)
    max_y: float = max(y_coords)

    # Create actual coords in clockwise order starting from northwest
    actual_coords = [
        [min_x, max_y],  # Northwest
        [max_x, max_y],  # Northeast
        [max_x, min_y],  # Southeast
        [min_x, min_y],  # Southwest
    ]

    # Check if coordinates match within tolerance
    coords_match: bool = all(
        np.allclose(np.array(actual), np.array(expected), rtol=tolerance)
        for actual, expected in zip(actual_coords, expected_coords, strict=True)
    )

    return coords_match, actual_coords


@pytest.fixture(name="test_config_file")
def test_config_file(test_metadata_file: Path) -> Path:
    """Create a temporary config file for testing."""
    config_data = {
        "server": {"port": 6002, "transport": "stdio"},
        "path_to_metadata": str(test_metadata_file),
        "path_to_ee_auth": "service-account.json",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        return Path(f.name)


class TestMCPServerIntegration:
    """Integration tests for the MCP server endpoints."""

    def test_get_all_datasets_and_metadata_endpoint(self) -> None:
        """Test the get_all_datasets_and_metadata endpoint."""
        result = get_all_datasets_and_metadata()

        assert "datasets" in result
        assert isinstance(result["datasets"], dict)
        assert len(result["datasets"]) > 0

        for dataset_name, dataset_info in result["datasets"].items():
            assert dataset_info.asset_id
            assert dataset_info.asset_id != ""
            assert dataset_info.description
            assert dataset_info.description != ""
            assert dataset_info.source_name
            assert dataset_info.source_name != ""
            assert isinstance(dataset_info.mosaic, bool)
            assert dataset_name
            assert dataset_name != ""

    def test_get_dataset_image_endpoint(self) -> None:
        """Test the get_dataset_image endpoint with real data."""
        result = get_dataset_image("children_population", trace_id="123")

        assert "image_path" in result
        assert isinstance(result["image_path"], str)
        assert len(result["image_path"]) > 0

    def test_get_dataset_image_invalid_dataset(self) -> None:
        """Test error handling for invalid dataset."""
        with pytest.raises(ValueError, match="Invalid dataset"):
            get_dataset_image("nonexistent_dataset", trace_id="123")

    def test_filter_image_by_threshold_endpoint(self) -> None:
        """Test the filter_image_by_threshold endpoint."""
        image_result = get_dataset_image("river_flood", trace_id="123")
        image_path = image_result["image_path"]

        result = filter_image_by_threshold(image_path, 0.5, "test_filtered_image")

        assert "result_name" in result
        assert isinstance(result["result_name"], str)
        assert len(result["result_name"]) > 0

    def test_mask_image_endpoint(self) -> None:
        """Test the mask_image endpoint."""
        image_result = get_dataset_image("river_flood", trace_id="123")
        mask_result = get_dataset_image("agricultural_drought", trace_id="123")

        result = mask_image(
            image_result["image_path"], mask_result["image_path"], "test_masked_image"
        )

        assert "result_name" in result
        assert isinstance(result["result_name"], str)
        assert len(result["result_name"]) > 0

    def test_union_binary_images_endpoint(self) -> None:
        """Test the union_binary_images endpoint."""
        image1_result = get_dataset_image("river_flood", trace_id="123")
        image2_result = get_dataset_image("agricultural_drought", trace_id="123")

        binary1_result = filter_image_by_threshold(image1_result["image_path"], 0.5, "binary1_test")
        binary2_result = filter_image_by_threshold(
            image2_result["image_path"], 75.0, "binary2_test"
        )

        result = union_binary_images(
            [
                f"data/123/{binary1_result['result_name']}.json",
                f"data/123/{binary2_result['result_name']}.json",
            ],
            "test_union_result",
        )

        assert "result_name" in result
        assert isinstance(result["result_name"], str)
        assert len(result["result_name"]) > 0

    def test_intersect_binary_images_endpoint(self) -> None:
        """Test the intersect_binary_images endpoint."""
        image1_result = get_dataset_image("river_flood", trace_id="123")
        image2_result = get_dataset_image("agricultural_drought", trace_id="123")

        binary1_result = filter_image_by_threshold(
            image1_result["image_path"], 0.5, "binary1_intersect"
        )
        binary2_result = filter_image_by_threshold(
            image2_result["image_path"], 75.0, "binary2_intersect"
        )

        result = intersect_binary_images(
            [
                f"data/123/{binary1_result['result_name']}.json",
                f"data/123/{binary2_result['result_name']}.json",
            ],
            "test_intersect_result",
        )

        assert "result_name" in result
        assert isinstance(result["result_name"], str)
        assert len(result["result_name"]) > 0

    def test_reduce_image_endpoint(self) -> None:
        """Test the reduce_image endpoint."""
        image_result = get_dataset_image("children_population", trace_id="123")

        zone_result = get_zone_of_area("THA", "country", trace_id="123")

        result = reduce_image(image_result["image_path"], zone_result["zone_path"], "mean")

        assert "aggregation_result" in result
        assert isinstance(result["aggregation_result"], int | float)


class TestMCPServerErrorHandling:
    """Test error handling in MCP server endpoints."""

    def test_invalid_area_type(self) -> None:
        """Test error handling for invalid area type."""
        with pytest.raises((ValueError, TypeError)):
            get_zone_of_area("THA", "invalid_type", trace_id="123")

    def test_invalid_reducer_type(self) -> None:
        """Test error handling for invalid reducer type."""
        image_result = get_dataset_image("children_population", trace_id="123")
        zone_result = get_zone_of_area("THA", "country", trace_id="123")

        with pytest.raises((ValueError, TypeError)):
            reduce_image(image_result["image_path"], zone_result["zone_path"], "invalid_reducer")

    def test_invalid_json_input(self) -> None:
        """Test error handling for invalid JSON input."""
        with pytest.raises((ValueError, TypeError, json.JSONDecodeError)):
            filter_image_by_threshold("invalid_json", 0.5, "test_invalid")


class TestMCPServerEdgeCases:
    """Test edge cases for MCP server endpoints."""

    def test_extreme_threshold_values(self) -> None:
        """Test filtering with extreme threshold values."""
        image_result = get_dataset_image("river_flood", trace_id="123")

        result_large = filter_image_by_threshold(
            image_result["image_path"], 1e10, "test_large_threshold"
        )
        assert "result_name" in result_large
        assert isinstance(result_large["result_name"], str)

        result_small = filter_image_by_threshold(
            image_result["image_path"], -1e10, "test_small_threshold"
        )
        assert "result_name" in result_small
        assert isinstance(result_small["result_name"], str)

    def test_multiple_binary_images_union(self) -> None:
        """Test union with multiple binary images."""
        images: list[str] = []
        for dataset in ["river_flood", "agricultural_drought", "children_population"]:
            image_result = get_dataset_image(dataset, trace_id="123")
            binary_result = filter_image_by_threshold(
                image_result["image_path"], 0.5, f"binary_{dataset}"
            )
            images.append(f"data/123/{binary_result['result_name']}.json")

        result = union_binary_images(images, "test_multiple_union")

        assert "result_name" in result
        assert isinstance(result["result_name"], str)
        assert len(result["result_name"]) > 0

    def test_different_reducer_types(self) -> None:
        """Test reduce_image with different reducer types."""
        image_result = get_dataset_image("children_population", trace_id="123")
        zone_result = get_zone_of_area("THA", "country", trace_id="123")

        reducers = ["mean", "max", "min", "sum"]

        for reducer in reducers:
            result = reduce_image(image_result["image_path"], zone_result["zone_path"], reducer)
            assert "aggregation_result" in result
            assert isinstance(result["aggregation_result"], int | float)


class TestMCPServerPerformance:
    """Test performance aspects of MCP server endpoints."""

    def test_concurrent_calls_simulation(self) -> None:
        """Test multiple sequential calls to simulate concurrent usage."""
        image_result = get_dataset_image("river_flood", trace_id="123")

        results: list[dict[str, Any]] = []
        for i in range(3):
            result = filter_image_by_threshold(
                image_result["image_path"], float(i + 1), f"concurrent_test_{i}"
            )
            results.append(result)

        assert len(results) == 3  # noqa: PLR2004
        for result in results:
            assert "result_name" in result
            assert isinstance(result["result_name"], str)

    def test_large_feature_collection_operations(self) -> None:
        """Test operations with larger feature collections."""
        zones: list[str] = []
        for country in ["THA", "IDN", "PHL"]:
            try:
                zone_result = get_zone_of_area(country, "country", trace_id="123")
                zones.append(zone_result["zone_path"])
            except ValueError:
                continue

        result = merge_feature_collections(zones, "test_large_merge")
        assert "feature_collection_path" in result
        assert isinstance(result["feature_collection_path"], str)
        assert len(result["feature_collection_path"]) > 0


class TestMCPServerOutputs:
    def test_intersect_feature_collection_result(self, rectangle_test_data: dict[str, str]) -> None:
        """Test that intersecting two rectangles produces the expected coordinates."""
        save_ee_object("data/123/rectangle_1.json", rectangle_test_data["rectangle_1"])
        save_ee_object("data/123/rectangle_2.json", rectangle_test_data["rectangle_2"])
        intersection_feature_data = intersect_feature_collections(
            [
                "data/123/rectangle_1.json",
                "data/123/rectangle_2.json",
            ],
            "test_intersection_result",
        )

        expected_coords: list[list[float]] = [[-103, 38.5], [-102, 38.5], [-102, 38], [-103, 38]]
        coords_match, actual_coords = check_coordinates_match(
            intersection_feature_data["feature_collection_path"], expected_coords
        )

        assert coords_match, (
            f"Intersection coordinates {actual_coords} do not match expected {expected_coords}"
        )

    def test_intersect_feature_collection_result_not_matching(
        self, rectangle_test_data: dict[str, str]
    ) -> None:
        """Test that intersecting two rectangles fails with incorrect expected coordinates."""
        save_ee_object("data/123/rectangle_1.json", rectangle_test_data["rectangle_1"])
        save_ee_object("data/123/rectangle_2.json", rectangle_test_data["rectangle_2"])
        intersection_feature_data = intersect_feature_collections(
            [
                "data/123/rectangle_1.json",
                "data/123/rectangle_2.json",
            ],
            "test_intersection_not_matching",
        )

        incorrect_coords: list[list[float]] = [[-104, 39.5], [-103, 39.5], [-103, 39], [-104, 39]]
        coords_match, actual_coords = check_coordinates_match(
            intersection_feature_data["feature_collection_path"], incorrect_coords
        )

        assert not coords_match, (
            f"Intersection coordinates {actual_coords} should not match incorrect expected "
            f"coordinates {incorrect_coords}"
        )

    def test_merge_feature_collection_result(self, rectangle_test_data: dict[str, str]) -> None:
        """Test that merging two rectangles produces the expected coordinates."""
        save_ee_object("data/123/rectangle_1.json", rectangle_test_data["rectangle_1"])
        save_ee_object("data/123/rectangle_2.json", rectangle_test_data["rectangle_2"])
        merge_feature_data = merge_feature_collections(
            [
                "data/123/rectangle_1.json",
                "data/123/rectangle_2.json",
            ],
            "test_merge_result",
        )
        expected_coords: list[list[float]] = [[-103, 39], [-102, 39], [-102, 37.5], [-103, 37.5]]
        coords_match, actual_coords = check_coordinates_match(
            merge_feature_data["feature_collection_path"], expected_coords
        )

        assert coords_match, (
            f"Intersection coordinates {actual_coords} do not match expected {expected_coords}"
        )

    def test_merge_feature_collection_result_not_matching(
        self, rectangle_test_data: dict[str, str]
    ) -> None:
        """Test that merging two rectangles fails with incorrect expected coordinates."""
        save_ee_object("data/123/rectangle_1.json", rectangle_test_data["rectangle_1"])
        save_ee_object("data/123/rectangle_2.json", rectangle_test_data["rectangle_2"])
        merge_feature_data = merge_feature_collections(
            [
                "data/123/rectangle_1.json",
                "data/123/rectangle_2.json",
            ],
            "test_merge_not_matching",
        )
        incorrect_coords: list[list[float]] = [[-103, 39], [-102, 39], [-102, 38], [-103, 38]]
        coords_match, actual_coords = check_coordinates_match(
            merge_feature_data["feature_collection_path"], incorrect_coords
        )

        assert not coords_match, (
            f"Intersection coordinates {actual_coords} should not match incorrect expected "
            f"coordinates {incorrect_coords}"
        )

    def test_reduce_image_result(self, binary_image_test_data: dict[str, str]) -> None:
        save_ee_object(
            "data/123/binary_image_horizontal.json",
            binary_image_test_data["binary_image_horizontal"],
        )
        save_ee_object(
            "data/123/horizontal_rectangle.json",
            binary_image_test_data["horizontal_rectangle"],
        )
        result = reduce_image(
            "data/123/binary_image_horizontal.json",
            "data/123/horizontal_rectangle.json",
            "sum",
            scale=binary_image_test_data["scale"],
        )

        assert abs(result["aggregation_result"] - 2) < 0.5  # noqa: PLR2004

        result = reduce_image(
            "data/123/binary_image_horizontal.json",
            "data/123/vertical_rectangle.json",
            "sum",
            scale=binary_image_test_data["scale"],
        )

        assert abs(result["aggregation_result"] - 1) < 0.5  # noqa: PLR2004

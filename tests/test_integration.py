"""Integration tests for the MCP server endpoints."""

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from ee.deserializer import fromJSON
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


@pytest.fixture(name="test_metadata_file")
def test_metadata_file() -> Path:
    """Create a temporary metadata file with real test data."""
    test_metadata = {
        "datasets": {
            "river_flood": {
                "asset_id": "users/unicef-ccri/Flood_hazard_th_2023_CEMS_GLOFAS_GL_rp_100",
                "image_filename": "river_flood.json",
                "description": "Test flood hazard dataset",
                "source_name": "GLOFAS",
                "source_url": "https://cds.climate.copernicus.eu/cdsapp#!/dataset/cems-glofas-reforecast",
                "mosaic": False,
                "threshold": 0.5,
                "color_palette": ["#0000FF", "#FF0000"],
            },
            "agricultural_drought": {
                "asset_id": "users/unicef-ccri/agricultural_drought",
                "image_filename": "agricultural_drought.json",
                "description": "Test drought dataset",
                "source_name": "ERA5",
                "source_url": "https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
                "mosaic": False,
                "threshold": 75.0,
                "color_palette": ["#00FF00", "#FF0000"],
            },
            "children_population": {
                "asset_id": "users/unicef-ccri/population_children_under_5_2020_100_m",
                "image_filename": "children_population.json",
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
    actual_feature_collection_info: Any = fromJSON(actual_feature_collection).getInfo()

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
        result = get_dataset_image("children_population")

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_get_dataset_image_invalid_dataset(self) -> None:
        """Test error handling for invalid dataset."""
        with pytest.raises(ValueError, match="Invalid dataset"):
            get_dataset_image("nonexistent_dataset")

    def test_filter_image_by_threshold_endpoint(self) -> None:
        """Test the filter_image_by_threshold endpoint."""
        image_result = get_dataset_image("river_flood")
        image_json = image_result["image_json"]

        result = filter_image_by_threshold(image_json, 0.5)

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_mask_image_endpoint(self) -> None:
        """Test the mask_image endpoint."""
        image_result = get_dataset_image("river_flood")
        mask_result = get_dataset_image("agricultural_drought")

        result = mask_image(image_result["image_json"], mask_result["image_json"])

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_union_binary_images_endpoint(self) -> None:
        """Test the union_binary_images endpoint."""
        image1_result = get_dataset_image("river_flood")
        image2_result = get_dataset_image("agricultural_drought")

        binary1_result = filter_image_by_threshold(image1_result["image_json"], 0.5)
        binary2_result = filter_image_by_threshold(image2_result["image_json"], 75.0)

        result = union_binary_images([binary1_result["image_json"], binary2_result["image_json"]])

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_intersect_binary_images_endpoint(self) -> None:
        """Test the intersect_binary_images endpoint."""
        image1_result = get_dataset_image("river_flood")
        image2_result = get_dataset_image("agricultural_drought")

        binary1_result = filter_image_by_threshold(image1_result["image_json"], 0.5)
        binary2_result = filter_image_by_threshold(image2_result["image_json"], 75.0)

        result = intersect_binary_images(
            [binary1_result["image_json"], binary2_result["image_json"]]
        )

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_reduce_image_endpoint(self) -> None:
        """Test the reduce_image endpoint."""
        image_result = get_dataset_image("children_population")

        zone_result = get_zone_of_area("THA", "country")

        result = reduce_image(image_result["image_json"], zone_result["zone_json"], "mean", 100.0)

        assert "aggregation_result" in result
        assert isinstance(result["aggregation_result"], int | float)


class TestMCPServerErrorHandling:
    """Test error handling in MCP server endpoints."""

    def test_invalid_area_type(self) -> None:
        """Test error handling for invalid area type."""
        with pytest.raises((ValueError, TypeError)):
            get_zone_of_area("THA", "invalid_type")

    def test_invalid_reducer_type(self) -> None:
        """Test error handling for invalid reducer type."""
        image_result = get_dataset_image("children_population")
        zone_result = get_zone_of_area("THA", "country")

        with pytest.raises((ValueError, TypeError)):
            reduce_image(
                image_result["image_json"], zone_result["zone_json"], "invalid_reducer", 100.0
            )

    def test_invalid_json_input(self) -> None:
        """Test error handling for invalid JSON input."""
        with pytest.raises((ValueError, TypeError, json.JSONDecodeError)):
            filter_image_by_threshold("invalid_json", 0.5)


class TestMCPServerEdgeCases:
    """Test edge cases for MCP server endpoints."""

    def test_extreme_threshold_values(self) -> None:
        """Test filtering with extreme threshold values."""
        image_result = get_dataset_image("river_flood")

        result_large = filter_image_by_threshold(image_result["image_json"], 1e10)
        assert "image_json" in result_large
        assert isinstance(result_large["image_json"], str)

        result_small = filter_image_by_threshold(image_result["image_json"], -1e10)
        assert "image_json" in result_small
        assert isinstance(result_small["image_json"], str)

    def test_multiple_binary_images_union(self) -> None:
        """Test union with multiple binary images."""
        images: list[str] = []
        for dataset in ["river_flood", "agricultural_drought", "children_population"]:
            image_result = get_dataset_image(dataset)
            binary_result = filter_image_by_threshold(image_result["image_json"], 0.5)
            images.append(binary_result["image_json"])

        result = union_binary_images(images)

        assert "image_json" in result
        assert isinstance(result["image_json"], str)
        assert len(result["image_json"]) > 0

    def test_different_reducer_types(self) -> None:
        """Test reduce_image with different reducer types."""
        image_result = get_dataset_image("children_population")
        zone_result = get_zone_of_area("THA", "country")

        reducers = ["mean", "max", "min", "sum"]

        for reducer in reducers:
            result = reduce_image(
                image_result["image_json"], zone_result["zone_json"], reducer, 100.0
            )
            assert "aggregation_result" in result
            assert isinstance(result["aggregation_result"], int | float)


class TestMCPServerPerformance:
    """Test performance aspects of MCP server endpoints."""

    def test_concurrent_calls_simulation(self) -> None:
        """Test multiple sequential calls to simulate concurrent usage."""
        image_result = get_dataset_image("river_flood")

        results: list[dict[str, Any]] = []
        for i in range(3):
            result = filter_image_by_threshold(image_result["image_json"], float(i + 1))
            results.append(result)

        assert len(results) == 3  # noqa: PLR2004
        for result in results:
            assert "image_json" in result
            assert isinstance(result["image_json"], str)

    def test_large_feature_collection_operations(self) -> None:
        """Test operations with larger feature collections."""
        zones: list[str] = []
        for country in ["THA", "IDN", "PHL"]:
            try:
                zone_result = get_zone_of_area(country, "country")
                zones.append(zone_result["zone_json"])
            except ValueError:
                continue

        result = merge_feature_collections(zones)
        assert "feature_collection_json" in result
        assert isinstance(result["feature_collection_json"], str)
        assert len(result["feature_collection_json"]) > 0


class TestMCPServerOutputs:
    def test_intersect_feature_collection_result(
        self, rectangle_test_data: dict[str, FeatureCollection]
    ) -> None:
        """Test that intersecting two rectangles produces the expected coordinates."""
        intersection_feature_data = intersect_feature_collections(
            [
                rectangle_test_data["rectangle_1"],
                rectangle_test_data["rectangle_2"],
            ],
        )

        expected_coords: list[list[float]] = [[-103, 38.5], [-102, 38.5], [-102, 38], [-103, 38]]
        coords_match, actual_coords = check_coordinates_match(
            intersection_feature_data["feature_collection_json"], expected_coords
        )

        assert (
            coords_match
        ), f"Intersection coordinates {actual_coords} do not match expected {expected_coords}"

    def test_intersect_feature_collection_result_not_matching(
        self, rectangle_test_data: dict[str, FeatureCollection]
    ) -> None:
        """Test that intersecting two rectangles fails with incorrect expected coordinates."""
        intersection_feature_data = intersect_feature_collections(
            [
                rectangle_test_data["rectangle_1"],
                rectangle_test_data["rectangle_2"],
            ],
        )

        incorrect_coords: list[list[float]] = [[-104, 39.5], [-103, 39.5], [-103, 39], [-104, 39]]
        coords_match, actual_coords = check_coordinates_match(
            intersection_feature_data["feature_collection_json"], incorrect_coords
        )

        assert not coords_match, (
            f"Intersection coordinates {actual_coords} should not match incorrect expected "
            f"coordinates {incorrect_coords}"
        )

    def test_merge_feature_collection_result(self, rectangle_test_data: dict[str, str]) -> None:
        """Test that merging two rectangles produces the expected coordinates."""
        merge_feature_data = merge_feature_collections(
            [
                rectangle_test_data["rectangle_1"],
                rectangle_test_data["rectangle_2"],
            ],
        )
        expected_coords: list[list[float]] = [[-103, 39], [-102, 39], [-102, 37.5], [-103, 37.5]]
        coords_match, actual_coords = check_coordinates_match(
            merge_feature_data["feature_collection_json"], expected_coords
        )

        assert (
            coords_match
        ), f"Intersection coordinates {actual_coords} do not match expected {expected_coords}"

    def test_merge_feature_collection_result_not_matching(
        self, rectangle_test_data: dict[str, str]
    ) -> None:
        """Test that merging two rectangles fails with incorrect expected coordinates."""
        merge_feature_data = merge_feature_collections(
            [
                rectangle_test_data["rectangle_1"],
                rectangle_test_data["rectangle_2"],
            ],
        )
        incorrect_coords: list[list[float]] = [[-103, 39], [-102, 39], [-102, 38], [-103, 38]]
        coords_match, actual_coords = check_coordinates_match(
            merge_feature_data["feature_collection_json"], incorrect_coords
        )

        assert not coords_match, (
            f"Intersection coordinates {actual_coords} should not match incorrect expected "
            f"coordinates {incorrect_coords}"
        )

    def test_reduce_image_result(self, binary_image_test_data: dict[str, str | int]) -> None:
        result = reduce_image(
            binary_image_test_data["binary_image_horizontal"],
            binary_image_test_data["horizontal_rectangle"],
            "sum",
            scale=binary_image_test_data["scale"],
        )

        assert abs(result["aggregation_result"] - 2) < 0.5  # noqa: PLR2004

        result = reduce_image(
            binary_image_test_data["binary_image_horizontal"],
            binary_image_test_data["vertical_rectangle"],
            "sum",
            scale=binary_image_test_data["scale"],
        )

        assert abs(result["aggregation_result"] - 1) < 0.5  # noqa: PLR2004

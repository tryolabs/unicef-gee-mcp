"""Test configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml


@pytest.fixture()
def mock_ee_module() -> Generator[MagicMock, None, None]:
    """Mock the entire ee module."""
    with pytest.MonkeyPatch().context() as m:
        # Mock Earth Engine classes
        mock_ee = MagicMock()
        mock_ee.Image = MagicMock()
        mock_ee.ImageCollection = MagicMock()
        mock_ee.FeatureCollection = MagicMock()
        mock_ee.Feature = MagicMock()
        mock_ee.Filter = MagicMock()
        mock_ee.Reducer = MagicMock()
        mock_ee.Number = MagicMock()
        mock_ee.Algorithms = MagicMock()
        mock_ee.ServiceAccountCredentials = MagicMock()
        mock_ee.Initialize = MagicMock()

        # Mock serialization/deserialization
        mock_ee.deserializer = MagicMock()
        mock_ee.deserializer.fromJSON = MagicMock()

        m.setattr("ee", mock_ee)
        yield mock_ee


@pytest.fixture()
def sample_config_data() -> dict[str, Any]:
    """Sample configuration data."""
    return {
        "server": {"port": 6002, "transport": "sse"},
        "path_to_metadata": "test_metadata.yaml",
        "path_to_ee_auth": "test_auth.json",
    }


@pytest.fixture()
def sample_metadata() -> dict[str, Any]:
    """Sample dataset metadata."""
    return {
        "datasets": {
            "test_dataset": {
                "asset_id": "test_asset",
                "image_filename": "test.json",
                "description": "Test dataset",
                "source_name": "Test Source",
                "source_url": "https://test.com",
                "mosaic": False,
                "threshold": 1.0,
                "color_palette": ["#FF0000", "#00FF00"],
            },
            "mosaic_dataset": {
                "asset_id": "mosaic_asset",
                "image_filename": "mosaic.json",
                "description": "Mosaic dataset",
                "source_name": "Mosaic Source",
                "source_url": "https://mosaic.com",
                "mosaic": True,
            },
        }
    }


@pytest.fixture()
def temp_config_file(sample_config_data: dict[str, Any]) -> Generator[Path, None, None]:
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_config_data, f)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


@pytest.fixture()
def temp_metadata_file(sample_metadata: dict[str, Any]) -> Generator[Path, None, None]:
    """Create a temporary metadata file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_metadata, f)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


@pytest.fixture()
def mock_image() -> MagicMock:
    """Mock Earth Engine Image."""
    mock = MagicMock()
    mock.serialize.return_value = (
        '{"result": "0", "values": {"0": {"functionInvocationValue": '
        '{"functionName": "Image.load", "arguments": '
        '{"id": {"constantValue": "projects/unicef-ccri/assets/test_asset"}}}}}}'
    )
    mock.updateMask.return_value = mock

    mock.lt.return_value = mock
    mock.lte.return_value = mock

    mock.unmask.return_value = mock
    mock.reduceRegions.return_value = mock
    mock.getInfo.return_value = {
        "features": [{"properties": {"mean": 10.5, "sum": 100, "max": 20}}]
    }
    return mock


@pytest.fixture()
def mock_image_gt() -> MagicMock:
    """Mock Earth Engine Image.gt."""
    mock = MagicMock()
    mock.gt.return_value = (
        '{"result": "0", "values": {"0": {"functionInvocationValue": '
        '{"functionName": "Image.gt", "arguments": '
        '{"image1": {"functionInvocationValue": {"functionName": "Image.load", "arguments": '
        '{"id": {"constantValue": "projects/unicef-ccri/assets/test_asset"}}}}, '
        '"image2": {"functionInvocationValue": {"functionName": "Image.constant", "arguments": '
        '{"value": {"constantValue": 5.0}}}}}}}}}'
    )
    return mock


@pytest.fixture()
def mock_image_collection() -> MagicMock:
    """Mock Earth Engine ImageCollection."""
    mock = MagicMock()
    mock.mosaic.return_value = MagicMock()
    mock.mosaic.return_value.serialize.return_value = (
        '{"result": "0", "values": {"0": {"functionInvocationValue": '
        '{"functionName": "ImageCollection.mosaic", "arguments": '
        '{"collection": {"functionInvocationValue": '
        '{"functionName": "ImageCollection.load", "arguments": '
        '{"id": {"constantValue": "projects/unicef-ccri/assets/mosaic_asset"}}}}}}}}}'
    )
    return mock


@pytest.fixture()
def mock_image_or() -> MagicMock:
    """Mock Earth Engine Image.Or."""
    mock = MagicMock()
    mock.Or.return_value = (
        '{"result": "0", "values": {"1": {"functionInvocationValue": '
        '{"functionName": "Image.constant", "arguments": {"value": {"constantValue": 0}}}}, '
        '"0": {"functionInvocationValue": {"functionName": "Image.or", "arguments": {"image1": '
        '{"functionInvocationValue": {"functionName": "Image.unmask", "arguments": {"input": '
        '{"functionInvocationValue": {"functionName": "Image.load", "arguments": {"id": '
        '{"constantValue": "projects/unicef-ccri/assets/binary1"}}}}, "value": {"valueReference": '
        '"1"}}}}, "image2": {"functionInvocationValue": {"functionName": "Image.unmask", '
        '"arguments": {"input": {"functionInvocationValue": {"functionName": "Image.load", '
        '"arguments": {"id": {"constantValue": "projects/unicef-ccri/assets/binary2"}}}}, '
        '"value": {"valueReference": "1"}}}}}}}}}'
    )
    return mock


@pytest.fixture()
def mock_image_and() -> MagicMock:
    """Mock Earth Engine Image.And."""
    mock = MagicMock()
    mock.And.return_value = (
        '{"result": "0", "values": {"0": {"functionInvocationValue": '
        '{"functionName": "Image.and", "arguments": {"image1": '
        '{"functionInvocationValue": {"functionName": "Image.load", "arguments": '
        '{"id": {"constantValue": "projects/unicef-ccri/assets/binary1"}}}}, '
        '"image2": {"functionInvocationValue": {"functionName": "Image.load", '
        '"arguments": {"id": {"constantValue": "projects/unicef-ccri/assets/binary2"}}}}}}}}}'
    )
    return mock


@pytest.fixture()
def mock_feature_collection_intersect() -> MagicMock:
    """Mock Earth Engine FeatureCollection."""
    mock = MagicMock()
    mock.serialize.return_value = (
        '{"result": "0", "values": {"1": {"functionInvocationValue": '
        '{"functionName": "Element.copyProperties", "arguments": {"destination": '
        '{"functionInvocationValue": {"functionName": "Feature", "arguments": '
        '{"geometry": {"functionInvocationValue": {"functionName": "Geometry.intersection", '
        '"arguments": {"left": {"functionInvocationValue": {"functionName": "Feature.geometry", '
        '"arguments": {"feature": {"argumentReference": "_MAPPING_VAR_0_0"}}}}, '
        '"maxError": {"functionInvocationValue": {"functionName": "ErrorMargin", '
        '"arguments": {"value": {"constantValue": 100}}}}, "right": '
        '{"functionInvocationValue": {"functionName": "Collection.geometry", '
        '"arguments": {"collection": {"functionInvocationValue": '
        '{"functionName": "Collection.loadTable", "arguments": '
        '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm1_wfp"}}}}}}}}}}}}}, '
        '"source": {"argumentReference": "_MAPPING_VAR_0_0"}}}}, "0": '
        '{"functionInvocationValue": {"functionName": "Collection.map", "arguments": '
        '{"baseAlgorithm": {"functionDefinitionValue": {"argumentNames": ["_MAPPING_VAR_0_0"], '
        '"body": "1"}}, "collection": {"functionInvocationValue": '
        '{"functionName": "Collection.loadTable", "arguments": '
        '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm0_wfp"}}}}}}}}}'
    )

    return mock


@pytest.fixture()
def mock_feature_collection_merge() -> MagicMock:
    """Mock Earth Engine FeatureCollection."""
    mock = MagicMock()
    mock.serialize.return_value = (
        '{"result": "0", "values": {"1": {"functionInvocationValue": '
        '{"functionName": "Collection.loadTable", "arguments": '
        '{"tableId": {"constantValue": "projects/unicef-ccri/assets/adm0_wfp"}}}}, '
        '"0": {"functionInvocationValue": {"functionName": "Collection.union", '
        '"arguments": {"collection": {"functionInvocationValue": {"functionName": '
        '"Collection.merge", "arguments": {"collection1": {"valueReference": "1"}, '
        '"collection2": {"valueReference": "1"}}}}}}}}}'
    )
    return mock


@pytest.fixture()
def mock_boundry_json() -> MagicMock:
    """Mock Earth Engine FeatureCollection.mean."""
    mock = MagicMock()
    mock.serialize.return_value = '{"result": "0", "values": {"1": {"functionInvocationValue": '
    '{"functionName": "Collection.filter", "arguments": {"collection": {"functionInvocationValue": '
    '{"functionName": "Collection.loadTable", "arguments": {"tableId": {"constantValue": '
    '"projects/unicef-ccri/assets/adm0_wfp"}}}}, "filter": {"functionInvocationValue": '
    '{"functionName": "Filter.equals", "arguments": {"leftField": {"constantValue": "iso3"}, '
    '"rightValue": {"constantValue": "URY"}}}}}}}, "0": {"functionInvocationValue": '
    '{"functionName": "Collection", "arguments": {"features": {"arrayValue": {"values": '
    '[{"functionInvocationValue": {"functionName": "Feature", "arguments": {"geometry": '
    '{"functionInvocationValue": {"functionName": "Geometry.simplify", "arguments": {"geometry": '
    '{"functionInvocationValue": {"functionName": "Collection.geometry", "arguments": '
    '{"collection": {"valueReference": "1"}}}}, "maxError": {"functionInvocationValue": '
    '{"functionName": "ErrorMargin", "arguments": {"value": {"functionInvocationValue": '
    '{"functionName": "If", "arguments": {"condition": {"functionInvocationValue": '
    '{"functionInvocationValue": {"functionName": "Number.gt", "arguments": {"left": '
    '{"functionInvocationValue": {"functionName": "Element.getNumber", "arguments": {"object": '
    '{"functionInvocationValue": {"functionName": "Collection.first", "arguments": {"collection": '
    '{"valueReference": "1"}}}}, "property": {"constantValue": "Shape_Area"}}}}, "right": '
    '{"constantValue": 33}}}}, "falseCase": {"constantValue": 100}, "trueCase": '
    '{"constantValue": 10000}}}}}}}}}}}}}]}}}}}}}'
    return mock


@pytest.fixture()
def sample_json_data() -> dict[str, Any]:
    """Sample JSON data for testing."""
    return {
        "valid_json": '{"type": "Image", "asset_id": "test"}',
        "invalid_json": '{"invalid": json}',
        "empty_json": "",
        "malformed_json": '{"incomplete":',
    }


@pytest.fixture()
def mock_pycountry() -> MagicMock:
    """Mock pycountry module."""
    mock = MagicMock()
    mock.countries = MagicMock()

    # Mock country object
    country_mock = MagicMock()
    country_mock.name = "France"
    country_mock.alpha_2 = "FR"
    country_mock.alpha_3 = "FRA"

    mock.countries.get.return_value = country_mock
    return mock


@pytest.fixture()
def integration_test_data() -> dict[str, Any]:
    """Data for integration tests."""
    return {
        "image_json": '{"type": "Image", "asset_id": "projects/test/image"}',
        "feature_collection_json": '{"type": "FeatureCollection", "features": []}',
        "binary_image_jsons": [
            '{"type": "Image", "asset_id": "projects/test/binary1"}',
            '{"type": "Image", "asset_id": "projects/test/binary2"}',
        ],
    }

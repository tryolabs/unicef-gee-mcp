from typing import Any, get_args

from config import config
from dotenv import load_dotenv
from handlers import (
    handle_filter_image_by_threshold,
    handle_get_all_datasets_and_metadata,
    handle_get_dataset_image,
    handle_get_zone_of_area,
    handle_intersect_binary_images,
    handle_intersect_feature_collections,
    handle_mask_image,
    handle_merge_feature_collections,
    handle_reduce_image,
    handle_union_binary_images,
)
from initialize import initialize_ee, load_all_datasets
from logging_config import get_logger
from mcp.server.fastmcp import FastMCP
from schemas import AREA_TYPES, REDUCERS, DatasetMetadata
from utils import safe_json_loads

load_dotenv(override=True)

mcp = FastMCP("GEE MCP", port=config.server.port)
initialize_ee(config.path_to_ee_auth)


logger = get_logger(__name__)


@mcp.tool(name="get_all_datasets_and_metadata")
def get_all_datasets_and_metadata() -> dict[str, dict[str, DatasetMetadata]]:
    """Get all available datasets names and metadata.

    Returns:
        A dictionary containing the metadata for all available datasets
    """
    res = handle_get_all_datasets_and_metadata(config.path_to_metadata)
    return {"datasets": res}


@mcp.tool(name="get_dataset_image_and_metadata")
def get_dataset_image(
    dataset: str,
) -> dict[str, DatasetMetadata | str | dict[str, str]]:
    """Get an image from Earth Engine and return its JSON representation and metadata.

    Args:
        dataset: The dataset to get the image and metadata for

    Returns:
        A dictionary containing the metadata and JSON representation of the image
        and the input arguments

    Use case:
        Retrieve a global agricultural drought dataset to analyze drought conditions:
        get_dataset_image("agricultural_drought")
    """
    dataset = dataset.lower()
    if dataset not in load_all_datasets(config.path_to_metadata):
        available_datasets = load_all_datasets(config.path_to_metadata)
        msg = f"Invalid dataset '{dataset}'. Available datasets: {available_datasets}"
        raise ValueError(msg)

    res = handle_get_dataset_image(dataset, config.path_to_metadata)
    return {"image_json": res}


@mcp.tool(name="mask_image")
def mask_image(
    image_json: str | dict[str, Any],
    mask_image_json: str | dict[str, Any],
) -> dict[str, str | dict[str, str]]:
    """Mask an Earth Engine image based on a mask.

    Masking an image means applying a binary filter to it, where pixels are retained only
    where the mask has non-zero values. This effectively "cuts out" or preserves only the
    areas of interest defined by the mask, while setting all other areas to no-data values.

    This is the operation used to intersect two images.

    The mask should be a binary image where:
    - Values of 1 (or non-zero) indicate areas to keep in the original image
    - Values of 0 indicate areas to mask out (set to no-data)

    This operation can only be used with images.

    Args:
        image_json: JSON string of the Earth Engine image
        mask_image_json: JSON string of the Earth Engine binary image mask.

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the masked Earth Engine image
            - input_arguments: The original input arguments used for the operation

    Use case:
        Get the zone of exposed children to a hazard.
        mask_image(
            child_population_data_json,
            hazard_data_json,
        )
    """
    image_json = safe_json_loads(str(image_json))
    mask_image_json = safe_json_loads(str(mask_image_json))
    res = handle_mask_image(image_json, mask_image_json)
    return {"image_json": res}


@mcp.tool(name="filter_image_by_threshold")
def filter_image_by_threshold(
    image_json: str | dict[str, Any],
    threshold: float,
) -> dict[str, str | dict[str, str]]:
    """Filter an Earth Engine image based on a threshold value.

    This function applies a threshold filter to an image.
    The result is a binary image where the values are either 0 or 1.

    Args:
        image_json: JSON string of the Earth Engine image
        threshold: Numeric value to use as the threshold for filtering

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the filtered Earth Engine image
            - input_arguments: The original input arguments used for the operation

    Raises:
        TypeError: If the loaded data is not an Earth Engine Image object

    Use case:
        Identify hazard areas with values above a threshold.
        filter_image_by_threshold(temperature_data_json, 35.0)
    """
    image_json = safe_json_loads(str(image_json))
    res = handle_filter_image_by_threshold(image_json, threshold)
    return {"image_json": res}


@mcp.tool(name="union_binary_images")
def union_binary_images(
    binary_images_jsons: list[str],
) -> dict[str, str | dict[str, str]]:
    """Union multiple binary images.

    This function loads binary images from the provided paths and performs
    a union operation, returning a new binary image where any of the input images
    have values of 1.

    Args:
        binary_images_jsons: List of JSON strings of the binary images to union.
            Each JSON should point to a valid Earth Engine Image.

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the union result
            - input_arguments: The original input arguments used for the operation

    Use case:
        Union two binary images to find areas that are either hazard zones.
        union_binary_images([flood_zones_json, drought_zones_json])
    """
    for i, image_json in enumerate(binary_images_jsons):
        binary_images_jsons[i] = safe_json_loads(image_json)

    res = handle_union_binary_images(binary_images_jsons)
    return {"image_json": res}


@mcp.tool(name="intersect_binary_images")
def intersect_binary_images(
    binary_images_jsons: list[str],
) -> dict[str, str | dict[str, str]]:
    """Intersect multiple binary images.

    This function loads binary images from the provided paths and performs
    an intersection operation, returning a new binary image where all the input images
    have values of 1.

    Args:
        binary_images_jsons: List of JSON strings of the binary images to intersect.
            Each JSON should point to a valid Earth Engine Image.

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the intersection result
            - input_arguments: The original input arguments used for the operation

    Use case:
        Intersect two binary images to find areas that are both hazard zones.
        intersect_binary_images([flood_zones_json, drought_zones_json])
    """
    for i, image_json in enumerate(binary_images_jsons):
        binary_images_jsons[i] = safe_json_loads(image_json)

    res = handle_intersect_binary_images(binary_images_jsons)
    return {"image_json": res}


@mcp.tool(name="intersect_feature_collections")
def intersect_feature_collections(
    feature_collections_jsons: list[str],
) -> dict[str, str | dict[str, str]]:
    """Perform a geometric intersection of multiple feature collections.

    This function loads feature collections from the provided paths and performs
    a geometric intersection operation, returning features that exist in all collections.

    Note: This operation only works with vector data (feature collections).
    Images cannot be intersected using this method.

    Args:
        feature_collections_jsons: List of JSON strings of the feature collections to intersect.
            Each JSON should point to a valid Earth Engine FeatureCollection.
            All inputs must be vector data (feature collections), not images.

    Returns:
        dict: A dictionary containing:
            - feature_collection_json: JSON string of the intersection result
            - input_arguments: The original input arguments used for the operation

    Raises:
        TypeError: If any input is an Image

    Use case:
        Find areas that are both flood-prone and densely populated by intersecting flood
        hazard zones with population density data:
        intersect_feature_collections([flood_zones_json, high_population_areas_json])
    """
    for i, feature_collection_json in enumerate(feature_collections_jsons):
        feature_collections_jsons[i] = safe_json_loads(feature_collection_json)

    res = handle_intersect_feature_collections(feature_collections_jsons)
    return {"feature_collection_json": res}


@mcp.tool(name="merge_feature_collections")
def merge_feature_collections(
    feature_collections_jsons: list[str],
) -> dict[str, str | dict[str, str]]:
    """Merge multiple feature collections into a single combined collection.

    This function loads feature collections from the provided paths and merges them
    into a single feature collection containing all features from the input collections.

    Note: This operation only works with vector data (feature collections).
    Images cannot be merged using this method.

    Args:
        feature_collections_jsons: List of JSON strings of the feature collections to merge.
            Each JSON should point to a valid Earth Engine FeatureCollection.

    Returns:
        dict: A dictionary containing:
            - feature_collection_json: JSON string of the merged result
            - input_arguments: The original input arguments used for the operation

    Raises:
        TypeError: If any input is an Image

    Use case:
        Combine different country areas into a single feature collection.
        merge_feature_collections([uruguay_json, argentina_json])
    """
    for i, feature_collection_json in enumerate(feature_collections_jsons):
        feature_collections_jsons[i] = safe_json_loads(feature_collection_json)

    res = handle_merge_feature_collections(feature_collections_jsons)
    return {"feature_collection_json": res}


@mcp.tool(name="reduce_image")
def reduce_image(
    image_json: str | dict[str, Any],
    feature_collection_json: str | dict[str, Any],
    reducer: REDUCERS,
    scale: float = 92.76624195666344,  # scale of child population data,
) -> dict[str, float | dict[str, float]]:
    """Reduce an image by applying a reducer to its pixels within specified regions.

    Args:
        image_json: The JSON string of the image to reduce
        feature_collection_json: The JSON string of the geometry to reduce the image to
        reducer: The reducer to apply
        scale: The scale of the image. It should be 100 unless otherwise specified.

    Returns:
        float: The reduced value

    Use case:
        Calculate the average rainfall within specific administrative boundaries:
        reduce_image("rainfall_data.json", "admin_boundaries.json", REDUCERS.MEAN)

    Note:
        Do not provide a value for temp_dir, it will be handled automatically.
    """
    if reducer not in get_args(REDUCERS):
        available_reducers = get_args(REDUCERS)
        msg = f"Invalid reducer: {reducer}. Available reducers: {available_reducers}"
        raise ValueError(msg)

    image_json = safe_json_loads(str(image_json))
    feature_collection_json = safe_json_loads(str(feature_collection_json))
    res = handle_reduce_image(image_json, feature_collection_json, reducer, scale)
    return {"aggregation_result": res}


@mcp.tool(name="get_zone_of_area")
def get_zone_of_area(
    area_name: str,
    area_type: AREA_TYPES,
) -> dict[str, str | dict[str, str]]:
    """Get the zone boundary for a specified area and return it as a JSON string.

    Retrieves the boundary geometry for either a country or admin level 1 area from
    Earth Engine and returns it as a JSON string.

    Args:
        area_name: Name of the area to get boundary for.
                If it is a country, it should be the ISO 3166-1 alpha-3 code.
        area_type: Type of area - either 'country' or 'admin1'. Determines which
            dataset to query.

    Returns:
        dict[str, str]: A dictionary containing:
            - zone_json: JSON string of the vector file

    Example:
        To get boundary data for France:
        >>> zone_json = get_zone_of_area("France", "country")

        To get boundary data for California:
        >>> zone_json = get_zone_of_area("California", "admin1")
    """
    if area_type not in get_args(AREA_TYPES):
        available_area_types = get_args(AREA_TYPES)
        msg = f"Invalid area type: {area_type}. Available types: {available_area_types}"
        raise ValueError(msg)

    res = handle_get_zone_of_area(area_name, area_type)

    return {"zone_json": res}


if __name__ == "__main__":
    mcp.run(config.server.transport)

from typing import Any, get_args

from config import config
from dotenv import load_dotenv
from handlers import (
    handle_build_map,
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
from mcp.server.fastmcp import FastMCP
from schemas import AREA_TYPES, REDUCERS, DatasetMetadata
from utils import safe_json_loads

load_dotenv(override=True)

mcp = FastMCP("GEE MCP", host=config.server.host, port=config.server.port)

# needs to be imported after mcp is initialized
# https://github.com/modelcontextprotocol/python-sdk/issues/420
from logging_config import get_logger  # noqa: E402

initialize_ee(config.path_to_ee_auth)


logger = get_logger(__name__)


@mcp.tool(name="get_all_datasets_and_metadata")
def get_all_datasets_and_metadata() -> dict[str, dict[str, DatasetMetadata]]:
    """Get all available datasets names and metadata.

    Returns:
        A dictionary containing the metadata for all available datasets
    """
    logger.info("Called get_all_datasets_and_metadata")
    res = handle_get_all_datasets_and_metadata(config.path_to_metadata)
    logger.info("Returning %d datasets", len(res))
    return {"datasets": res, "input_arguments": {}}


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
    logger.info("Called get_dataset_image with dataset=%s", dataset)
    dataset = dataset.lower()
    if dataset not in load_all_datasets(config.path_to_metadata):
        available_datasets = load_all_datasets(config.path_to_metadata)
        msg = f"Invalid dataset '{dataset}'. Available datasets: {available_datasets}"
        logger.exception(msg)
        raise ValueError(msg)

    res = handle_get_dataset_image(dataset, config.path_to_metadata)
    logger.info("Successfully retrieved dataset image for %s", dataset)
    return {"image_json": res, "input_arguments": {"dataset": dataset}}


@mcp.tool(name="mask_image")
def mask_image(
    image_json: str | dict[str, Any],
    mask_image_json: str | dict[str, Any],
) -> dict[str, Any]:
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
    logger.info("Called mask_image")
    image_json = safe_json_loads(str(image_json))
    mask_image_json = safe_json_loads(str(mask_image_json))
    res = handle_mask_image(image_json, mask_image_json)
    logger.info("Successfully masked image")
    return {"image_json": res}


@mcp.tool(name="filter_image_by_threshold")
def filter_image_by_threshold(
    image_json: str | dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
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
    logger.info("Called filter_image_by_threshold with threshold=%s", threshold)
    image_json = safe_json_loads(str(image_json))
    res = handle_filter_image_by_threshold(image_json, threshold)
    logger.info("Successfully filtered image by threshold %s", threshold)
    return {"image_json": res, "input_arguments": {"threshold": threshold}}


@mcp.tool(name="union_binary_images")
def union_binary_images(
    binary_images_jsons: list[str],
) -> dict[str, Any]:
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
    logger.info("Called union_binary_images with %d images", len(binary_images_jsons))
    for i, image_json in enumerate(binary_images_jsons):
        binary_images_jsons[i] = safe_json_loads(image_json)

    res = handle_union_binary_images(binary_images_jsons)
    logger.info("Successfully performed union on %d binary images", len(binary_images_jsons))
    return {"image_json": res}


@mcp.tool(name="intersect_binary_images")
def intersect_binary_images(
    binary_images_jsons: list[str],
) -> dict[str, Any]:
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
    logger.info("Called intersect_binary_images with %d images", len(binary_images_jsons))
    for i, image_json in enumerate(binary_images_jsons):
        binary_images_jsons[i] = safe_json_loads(image_json)

    res = handle_intersect_binary_images(binary_images_jsons)
    logger.info("Successfully performed intersection on %d binary images", len(binary_images_jsons))
    return {"image_json": res}


@mcp.tool(name="intersect_feature_collections")
def intersect_feature_collections(
    feature_collections_jsons: list[str],
) -> dict[str, Any]:
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
    logger.info(
        "Called intersect_feature_collections with %d feature collections",
        len(feature_collections_jsons),
    )
    for i, feature_collection_json in enumerate(feature_collections_jsons):
        feature_collections_jsons[i] = safe_json_loads(feature_collection_json)

    res = handle_intersect_feature_collections(feature_collections_jsons)
    logger.info(
        "Successfully performed intersection on %d feature collections",
        len(feature_collections_jsons),
    )
    return {"feature_collection_json": res}


@mcp.tool(name="merge_feature_collections")
def merge_feature_collections(
    feature_collections_jsons: list[str],
) -> dict[str, Any]:
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
    logger.info(
        "Called merge_feature_collections with %d feature collections",
        len(feature_collections_jsons),
    )
    for i, feature_collection_json in enumerate(feature_collections_jsons):
        feature_collections_jsons[i] = safe_json_loads(feature_collection_json)

    res = handle_merge_feature_collections(feature_collections_jsons)
    logger.info("Successfully merged %d feature collections", len(feature_collections_jsons))
    return {"feature_collection_json": res}


@mcp.tool(name="reduce_image")
def reduce_image(
    image_json: str | dict[str, Any],
    feature_collection_json: str | dict[str, Any],
    reducer: REDUCERS,
) -> dict[str, Any]:
    """Reduce an image by applying a reducer to its pixels within specified regions.

    Args:
        image_json: The JSON string of the image to reduce
        feature_collection_json: The JSON string of the geometry to reduce the image to
        reducer: The reducer to apply (lower case)

    Returns:
        float: The reduced value

    Use case:
        Calculate the average rainfall within specific administrative boundaries:
        reduce_image("rainfall_data.json", "admin_boundaries.json", REDUCERS.MEAN)

    Note:
        Do not provide a value for temp_dir, it will be handled automatically.
    """
    reducer = reducer.lower()  # type: ignore[assignment]
    logger.info("Called reduce_image with reducer=%s", reducer)
    if reducer not in get_args(REDUCERS):
        available_reducers = get_args(REDUCERS)
        msg = f"Invalid reducer: {reducer}. Available reducers: {available_reducers}"
        logger.exception(msg)
        raise ValueError(msg)
    image_json = safe_json_loads(str(image_json))
    feature_collection_json = safe_json_loads(str(feature_collection_json))
    res = handle_reduce_image(image_json, feature_collection_json, reducer)
    logger.info("Successfully reduced image with reducer %s, result: %s", reducer, res)
    return {"aggregation_result": res, "input_arguments": {"reducer": reducer}}


@mcp.tool(name="get_zone_of_area")
def get_zone_of_area(
    area_name: str,
    area_type: AREA_TYPES,
) -> dict[str, Any]:
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
    logger.info("Called get_zone_of_area with area_name=%s and area_type=%s", area_name, area_type)
    if area_type not in get_args(AREA_TYPES):
        available_area_types = get_args(AREA_TYPES)
        msg = f"Invalid area type: {area_type}. Available types: {available_area_types}"
        logger.exception(msg)
        raise ValueError(msg)

    res = handle_get_zone_of_area(area_name, area_type)
    logger.info("Successfully retrieved zone for area %s of type %s", area_name, area_type)

    return {"zone_json": res, "input_arguments": {"area_name": area_name, "area_type": area_type}}


@mcp.tool(name="build_map")
def build_map(
    images_json: list[str | dict[str, Any]],
    feature_collection_json: str | dict[str, Any],
    color_palettes: list[list[str]],
    names: list[str],
) -> dict[str, Any]:
    """Build a map from images and vector data and save it to an HTML file.

    Creates an interactive map by overlaying Earth Engine images on top of vector data
    (e.g. administrative boundaries). The map is saved as an HTML file that can be viewed
    in a web browser.

    Each image will be a different layer in the map, with its own color palette and name.

    Args:
        images_json: List of JSON strings of the Earth Engine images to display on the map
        feature_collection_json: JSON string of the vector data (e.g. GeoJSON) defining the
            boundaries to overlay the images on
        color_palettes: List of color palettes to use for each image layer. Each palette should
            be a list of color strings (e.g. ["#ff0000", "#00ff00"])
        names:  List of names for each image layer. Must match length of images_json.

    Returns:
        dict: A dictionary containing the HTML content of the map under the key 'html_content'

    Use case:
        Create an interactive map showing fire severity and population density in a region:
        build_map(["fire_image.json", "population_density_image.json"], "country_boundaries.json",
                 [["#ff0000", "#00ff00"], ["#0000ff", "#ffff00"]],
                ["Fire Severity", "Population Density"])
    """
    logger.info("Called build_map with %d images", len(images_json))
    if len(images_json) != len(color_palettes):
        msg = "The number of color palettes must match the number of images"
        logger.exception(msg)
        raise ValueError(msg)
    if len(images_json) != len(names):
        msg = "The number of names must match the number of images"
        logger.exception(msg)
        raise ValueError(msg)

    images_json = [safe_json_loads(str(image_json)) for image_json in images_json]

    feature_collection_json = safe_json_loads(str(feature_collection_json))

    res = handle_build_map(images_json, feature_collection_json, color_palettes, names)  # type: ignore[arg-type]
    logger.info("Successfully built map")
    return {
        "html_content": res,
        "input_arguments": {"color_palettes": color_palettes, "names": names},
    }


if __name__ == "__main__":
    mcp.run(config.server.transport)  # type: ignore[call-arg]

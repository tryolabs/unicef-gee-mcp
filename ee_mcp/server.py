import shutil
from pathlib import Path
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
from utils import save_ee_object

load_dotenv(override=True)

mcp = FastMCP("GEE MCP", host=config.server.host, port=config.server.port)

# needs to be imported after mcp is initialized
# https://github.com/modelcontextprotocol/python-sdk/issues/420
from logging_config import get_logger  # noqa: E402

initialize_ee(config.path_to_ee_auth)

logger = get_logger(__name__)


@mcp.tool(name="create_temp_dir")
def create_temp_dir(trace_id: str) -> dict[str, Any]:
    """Create a temporary directory for storing intermediate processing files.

    This function creates a unique temporary directory using the provided trace_id
    to organize and isolate files generated during a specific processing session.
    The directory is created under the 'data' folder with the trace_id as the subdirectory name.

    Args:
        trace_id (str): Unique identifier used to create a specific temporary directory path.

    Returns:
        dict[str, Any]: Dictionary containing:
            - input_arguments (dict): Contains 'temp_dir' key with the absolute path as string.

    Example:
        >>> create_temp_dir("session_123")
        {"input_arguments": {"temp_dir": "/path/to/data/session_123"}}
    """
    logger.info("Called create_temp_dir with trace_id=%s", trace_id)
    temp_dir = Path(f"data/{trace_id}").resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Created temporary directory %s", temp_dir)
    return {"result": "success", "input_arguments": {"temp_dir": str(temp_dir)}}


@mcp.tool(name="get_all_datasets_and_metadata")
def get_all_datasets_and_metadata() -> dict[str, dict[str, DatasetMetadata]]:
    """Retrieve all available datasets and their associated metadata.

    This function loads and returns all datasets that are available in the system
    along with their metadata information. The metadata includes details such as
    dataset descriptions, data sources, temporal coverage, and other relevant attributes.

    Args:
        None

    Returns:
        dict[str, dict[str, DatasetMetadata]]: Dictionary containing:
            - datasets (dict): Nested dictionary where:
              - keys are dataset names
              - values are DatasetMetadata objects
            - input_arguments (dict): Empty dictionary for consistency with other functions.

    Example:
        >>> get_all_datasets_and_metadata()
        {
            "datasets": {
                "flood_data": {"name": "Flood Dataset", "description": "Global flood data", ...},
                "drought_data": {"name": "Drought Dataset", "description": "Drought indices", ...}
            },
            "input_arguments": {}
        }
    """
    logger.info("Called get_all_datasets_and_metadata")
    res = handle_get_all_datasets_and_metadata(config.path_to_metadata)
    logger.info("Returning %d datasets", len(res))
    return {"datasets": res, "input_arguments": {}}


@mcp.tool(name="get_dataset_image_and_metadata")
def get_dataset_image(
    dataset: str,
    trace_id: str,
) -> dict[str, DatasetMetadata | str | dict[str, str]]:
    """Retrieve a specific dataset image and save it to a temporary location.

    This function loads a specific dataset image from Google Earth Engine and saves
    it as a JSON file in the temporary directory associated with the trace_id.
    The dataset name is case-insensitive and must exist in the available datasets.

    Args:
        dataset (str): Name of the dataset to retrieve (case-insensitive).
        trace_id (str): Unique identifier for the processing session to determine save location.

    Returns:
        dict[str, DatasetMetadata | str | dict[str, str]]: Dictionary containing:
            - image_path (str): Path to the saved JSON file containing the dataset image.
            - input_arguments (dict): Contains the dataset name used.

    Raises:
        ValueError: If the specified dataset is not found in available datasets.

    Example:
        >>> get_dataset_image("FLOOD_DATA", "session_123")
        {
            "image_path": "data/session_123/image_flood_data.json",
            "input_arguments": {"dataset": "flood_data"}
        }
    """
    logger.info("Called get_dataset_image with dataset=%s", dataset)
    dataset = dataset.lower()
    available_datasets = load_all_datasets(config.path_to_metadata)
    if dataset not in available_datasets:
        msg = f"Invalid dataset '{dataset}'. Available datasets: {available_datasets}"
        logger.exception(msg)
        raise ValueError(msg)
    res = handle_get_dataset_image(dataset, config.path_to_metadata)
    image_path = f"data/{trace_id}/image_{dataset}.json"
    save_ee_object(image_path, res)
    logger.info("Successfully retrieved dataset image for %s", dataset)
    return {"image_path": image_path, "input_arguments": {"dataset": dataset}}


@mcp.tool(name="mask_image")
def mask_image(
    image_path: str,
    mask_image_path: str,
    result_name: str,
) -> dict[str, Any]:
    """Apply a mask to an image using another image as the mask.

    This function takes an input image and applies a mask image to it, effectively
    filtering the input image to only show areas where the mask has valid values.
    The result is saved as a new JSON file in the same directory as the input image.

    Args:
        image_path (str): Path to the input image JSON file to be masked.
        mask_image_path (str): Path to the mask image JSON file used for masking.
        result_name (str): Name for the output masked image file (without extension).

    Returns:
        dict[str, Any]: Dictionary containing:
            - result_name (str): Name of the output masked image file.
            - input_arguments (dict): Contains all input parameters used.

    Example:
        >>> mask_image("data/session_123/children_population.json",
        ...     "data/session_123/flood_zones.json",
        ...     "children_population_flood_zones",
        ... )
        {
            "result_name": "children_population_flood_zones",
            "input_arguments": {
                "image_path": "data/session_123/children_population.json",
                "mask_image_path": "data/session_123/flood_zones.json",
                "result_name": "children_population_flood_zones"
            }
        }
    """
    logger.info(
        "Called mask_image with image_path=%s, mask_image_path=%s, result_name=%s",
        image_path,
        mask_image_path,
        result_name,
    )
    res = handle_mask_image(image_path, mask_image_path)
    result_path = f"{'/'.join(image_path.split('/')[:-1])}/{result_name}.json"
    save_ee_object(result_path, res)
    logger.info("Successfully masked image")
    return {
        "result_name": result_name,
        "input_arguments": {
            "image": image_path.split("/")[-1],
            "mask_image": mask_image_path.split("/")[-1],
            "result_name": result_name,
        },
    }


@mcp.tool(name="filter_image_by_threshold")
def filter_image_by_threshold(
    image_path: str,
    threshold: float | str,
    result_name: str,
) -> dict[str, Any]:
    """Filter an image by applying a threshold to create a binary mask.

    This function applies a threshold filter to an image, creating a binary image
    where pixels above the threshold are preserved and pixels below are masked out.
    The filtered result is saved as a new JSON file in the same directory.

    Args:
        image_path (str): Path to the input image JSON file to be filtered.
        threshold (float|str): Threshold value used for filtering. Pixels above this value are kept.
        If "mean", the threshold is calculated using the mean of the image.
        result_name (str): Name for the output filtered image file (without extension).

    Returns:
        dict[str, Any]: Dictionary containing the filtered image path and input arguments.
            - image_path (str): Path to the saved filtered image JSON file.
            - input_arguments (dict): Contains the threshold value used.

    Example:
        >>> filter_image_by_threshold(
        ...     "data/session_123/precipitation.json",
        ...     50.0,
        ...     "filtered_precipitation",
        ... )
        {
            "image_path": "data/session_123/filtered_precipitation.json",
            "input_arguments": {"threshold": 50.0, "result_name": "filtered_precipitation"}
        }
    """
    try:
        logger.info(
            "Called filter_image_by_threshold with image_path=%s, threshold=%s",
            image_path,
            threshold,
        )
        res = handle_filter_image_by_threshold(image_path, threshold)
        result_path = f"{'/'.join(image_path.split('/')[:-1])}/{result_name}.json"
        save_ee_object(result_path, res)
        logger.info("Successfully filtered image by threshold %s", threshold)
    except Exception as e:
        msg = f"Error filtering image by threshold {threshold}: {e}"
        logger.exception(msg)
        raise ValueError(msg) from e
    return {
        "result_name": result_name,
        "input_arguments": {
            "image": image_path.split("/")[-1],
            "threshold": threshold,
            "result_name": result_name,
        },
    }


@mcp.tool(name="union_binary_images")
def union_binary_images(
    binary_images_paths: list[str],
    result_name: str,
) -> dict[str, Any]:
    """Perform a union operation on multiple binary images.

    This function takes multiple binary images and performs a logical OR operation,
    creating a combined image where a pixel is 1 if it's 1 in any of the input images.
    The operation is useful for combining multiple hazard or risk areas.

    Args:
        binary_images_paths (list[str]): List of paths to binary image JSON files to union.
        result_name (str): Name for the output union image file (without extension).

    Returns:
        dict[str, Any]: Dictionary containing the union result image path.
            - result_name (str): Name of the output union image file.

    Example:
        >>> union_binary_images([
        ...     "data/session_123/flood_mask.json",
        ...     "data/session_123/drought_mask.json",
        ... ],
        ...     "union_result",
        ... )
        {
            "result_name": "union_result",
            "input_arguments": {"result_name": "union_result"}
        }
    """
    logger.info("Called union_binary_images with %d images", len(binary_images_paths))
    res = handle_union_binary_images(binary_images_paths)
    logger.info("Successfully performed union on %d binary images", len(binary_images_paths))
    result_path = f"{'/'.join(binary_images_paths[0].split('/')[:-1])}/{result_name}.json"
    save_ee_object(result_path, res)
    return {
        "result_name": result_name,
        "input_arguments": {
            "result_name": result_name,
            "binary_images": [
                binary_images_paths.split("/")[-1] for binary_images_paths in binary_images_paths
            ],
        },
    }


@mcp.tool(name="intersect_binary_images")
def intersect_binary_images(
    binary_images_paths: list[str],
    result_name: str,
) -> dict[str, Any]:
    """Perform an intersection operation on multiple binary images.

    This function takes multiple binary images and performs a logical AND operation,
    creating a combined image where a pixel is 1 only if it's 1 in all input images.
    This is useful for finding areas that satisfy multiple conditions simultaneously.

    Args:
        binary_images_paths (list[str]): List of paths to binary image JSON files to intersect.
        result_name (str): Name for the output intersection image file (without extension).

    Returns:
        dict[str, Any]: Dictionary containing the intersection result image path.
            - result_name (str): Name of the output intersection image file.

    Example:
        >>> intersect_binary_images([
        ...     "data/session_123/flood_areas.json",
        ...     "data/session_123/fire_areas.json",
        ... ],
        ...     "flood_and_fire_areas",
        ... )
        {
            "result_name": "flood_and_fire_areas",
            "input_arguments": {"result_name": "flood_and_fire_areas"}
        }
    """
    logger.info("Called intersect_binary_images with %d images", len(binary_images_paths))
    res = handle_intersect_binary_images(binary_images_paths)
    logger.info("Successfully performed intersection on %d binary images", len(binary_images_paths))
    result_path = f"{'/'.join(binary_images_paths[0].split('/')[:-1])}/{result_name}.json"
    save_ee_object(result_path, res)
    return {
        "result_name": result_name,
        "input_arguments": {
            "result_name": result_name,
            "binary_images": [
                binary_images_paths.split("/")[-1] for binary_images_paths in binary_images_paths
            ],
        },
    }


@mcp.tool(name="intersect_feature_collections")
def intersect_feature_collections(
    feature_collections_paths: list[str],
    result_name: str,
) -> dict[str, Any]:
    """Perform spatial intersection on multiple feature collections.

    This function takes multiple vector feature collections and computes their
    spatial intersection, returning only the areas where all input collections overlap.
    This is useful for finding common geographic areas across multiple datasets.

    Args:
        feature_collections_paths (list[str]): List of paths to feature collection JSON files
                                             to intersect.
        result_name (str): Name for the output intersection feature collection file
                        (without extension).

    Returns:
        dict[str, Any]: Dictionary containing:
            - feature_collection_path (str): Path to the saved intersection feature collection
                                            JSON file.

    Example:
        >>> intersect_feature_collections([
        ...     "data/session_456/country-zone.json",
        ...     "data/session_456/city-zone.json",
        ... ],
        ...     "intersection",
        ... )
        {
            "feature_collection_path": "data/session_456/intersection.json",
            "input_arguments": {"result_name": "intersection"}
        }
    """
    logger.info(
        "Called intersect_feature_collections with %d feature collections",
        len(feature_collections_paths),
    )
    res = handle_intersect_feature_collections(feature_collections_paths)
    logger.info(
        "Successfully performed intersection on %d feature collections",
        len(feature_collections_paths),
    )
    result_path = f"{'/'.join(feature_collections_paths[0].split('/')[:-1])}/{result_name}.json"
    save_ee_object(result_path, res)
    return {
        "feature_collection_path": result_path,
        "input_arguments": {
            "result_name": result_name,
            "feature_collections": [
                feature_collections_paths.split("/")[-1]
                for feature_collections_paths in feature_collections_paths
            ],
        },
    }


@mcp.tool(name="merge_feature_collections")
def merge_feature_collections(
    feature_collections_paths: list[str],
    result_name: str,
) -> dict[str, Any]:
    """Merge multiple feature collections into a single collection.

    This function combines multiple vector feature collections into one unified
    collection containing all features from all input collections. This is useful
    for consolidating geographic data from multiple sources or processing steps.

    Args:
        feature_collections_paths (list[str]): List of paths to feature collection JSON files
                                                to merge.
        result_name (str): Name for the output merged feature collection file (without extension).

    Returns:
        dict[str, Any]: Dictionary containing:
            - feature_collection_path (str): Path to the saved merged feature collection JSON file.

    Example:
        >>> merge_feature_collections([
        ...     "data/session_123/uruguay-zone.json",
        ...     "data/session_123/argentina-zone.json",
        ... ],
        ...     "uruguay_and_argentina-zone",
        ... )
        {
            "feature_collection_path": "data/session_123/uruguay_and_argentina-zone.json",
            "input_arguments": {"result_name": "uruguay_and_argentina-zone"}
        }
    """
    logger.info(
        "Called merge_feature_collections with %d feature collections",
        len(feature_collections_paths),
    )
    res = handle_merge_feature_collections(feature_collections_paths)
    logger.info("Successfully merged %d feature collections", len(feature_collections_paths))
    result_path = f"{'/'.join(feature_collections_paths[0].split('/')[:-1])}/{result_name}.json"
    save_ee_object(result_path, res)
    return {
        "feature_collection_path": result_path,
        "input_arguments": {
            "result_name": result_name,
            "feature_collections": [
                feature_collections_paths.split("/")[-1]
                for feature_collections_paths in feature_collections_paths
            ],
        },
    }


@mcp.tool(name="reduce_image")
def reduce_image(
    image_path: str,
    feature_collection_path: str,
    reducer: REDUCERS,
    scale: float = 92.76624195666344,
) -> dict[str, Any]:
    """Perform statistical reduction of image data within feature collection boundaries.

    This function applies a statistical reducer (e.g., mean, sum, max) to image data
    within the boundaries defined by a feature collection. This is commonly used
    to calculate statistics like average rainfall per administrative region or
    total population within specific areas.

    Args:
        image_path (str): Path to the input image JSON file to reduce.
        feature_collection_path (str): Path to feature collection JSON file defining the reduction
                                       boundaries.
        reducer (REDUCERS): Type of statistical reduction to perform.
        scale (float): Scale of the image. Do not use this parameter unless otherwise specified.

    Returns:
        dict[str, Any]: Dictionary containing the aggregation result and input arguments.
            - aggregation_result: The computed statistical values for each feature.
            - input_arguments (dict): Contains the reducer type used.

    Raises:
        ValueError: If the specified reducer is not supported.

    Example:
        >>> reduce_image("data/session_123/precipitation.json",
        ...     "data/session_123/countries.json",
        ...     "mean",
        ... )
        {
            "aggregation_result": {"country1": 45.2, "country2": 38.7},
            "input_arguments": {"reducer": "mean"}
        }
    """
    reducer = reducer.lower()  # type: ignore[assignment]
    logger.info("Called reduce_image with reducer=%s", reducer)
    if reducer not in get_args(REDUCERS):
        available_reducers = get_args(REDUCERS)
        msg = f"Invalid reducer: {reducer}. Available reducers: {available_reducers}"
        logger.exception(msg)
        raise ValueError(msg)

    res = handle_reduce_image(image_path, feature_collection_path, reducer, scale)
    logger.info("Successfully reduced image with reducer %s, result: %s", reducer, res)

    return {
        "aggregation_result": res,
        "input_arguments": {
            "reducer": reducer,
            "feature_collection": feature_collection_path.split("/")[-1],
            "image": image_path.split("/")[-1],
            "scale": scale,
        },
    }


@mcp.tool(name="get_zone_of_area")
def get_zone_of_area(
    area_name: str,
    area_type: AREA_TYPES,
    trace_id: str,
) -> dict[str, Any]:
    """Retrieve the geometric boundary of a specified geographic area.

    This function fetches the geographic boundary (zone) for a named area of a specific type
    (e.g., country, state, city). The zone is returned as a feature collection and saved
    to the temporary directory for further processing.

    Args:
        area_name (str): Name of the geographic area to retrieve.
        area_type (AREA_TYPES): Type of area ('country' or 'admin1').
        trace_id (str): Unique identifier for the processing session.

    Returns:
        dict[str, Any]: Dictionary containing:
            - zone_path (str): Path to the saved zone feature collection JSON file.
            - input_arguments (dict): Contains the area name and type used.

    Raises:
        ValueError: If the specified area type is not supported.

    Example:
        >>> get_zone_of_area("Kenya", "country", "session_123")
        {
            "zone_path": "data/session_123/zone_Kenya.json",
            "input_arguments": {"area_name": "Kenya", "area_type": "country"}
        }
    """
    logger.info("Called get_zone_of_area with area_name=%s and area_type=%s", area_name, area_type)
    if area_type not in get_args(AREA_TYPES):
        available_area_types = get_args(AREA_TYPES)
        msg = f"Invalid area type: {area_type}. Available types: {available_area_types}"
        logger.exception(msg)
        raise ValueError(msg)
    res = handle_get_zone_of_area(area_name, area_type)
    logger.info("Successfully retrieved zone for area %s of type %s", area_name, area_type)
    result_path = f"data/{trace_id}/zone_{area_name}.json"
    save_ee_object(result_path, res)
    logger.info("Saved zone to %s", result_path)
    return {
        "zone_path": result_path,
        "input_arguments": {"area_name": area_name, "area_type": area_type},
    }


@mcp.tool(name="build_map")
def build_map(
    images_paths: list[str],
    feature_collection_path: str,
    color_palettes: list[list[str]],
    names: list[str],
) -> dict[str, Any]:
    """Generate an interactive HTML map visualization with multiple image layers.

    This function creates an interactive web map that displays multiple image layers
    with custom color palettes and names. Each image is rendered as a separate layer
    that can be toggled on/off. A feature collection can be overlaid to show
    geographic boundaries or regions of interest.

    Args:
        images_paths (list[str]): List of paths to image JSON files to display as map layers.
        feature_collection_path (str): Path to feature collection JSON file for boundary overlay.
        color_palettes (list[list[str]]): List of color palettes for each image layer.
        names (list[str]): List of display names for each image layer.

    Returns:
        dict[str, Any]: Dictionary containing the HTML map content and input arguments.
            - html_content (str): HTML content for the interactive map.
            - input_arguments (dict): Contains color palettes and names used.

    Raises:
        ValueError: If the number of color palettes or names doesn't match the number of images.

    Example:
        >>> build_map(
        ...     ["data/session_123/flood.json", "data/session_123/drought.json"],
        ...     "data/session_123/countries.json",
        ...     [["#blue", "#darkblue"], ["#yellow", "#red"]],
        ...     ["Flood Risk", "Drought Risk"]
        ... )
        {
            "html_content": "<html>...</html>",
            "input_arguments": {
                "color_palettes": [["#blue", "#darkblue"], ["#yellow", "#red"]],
                "names": ["Flood Risk", "Drought Risk"]
            }
        }
    """
    logger.info("Called build_map with %d images", len(images_paths))
    if len(images_paths) != len(color_palettes):
        msg = "The number of color palettes must match the number of images"
        logger.exception(msg)
        raise ValueError(msg)
    if len(images_paths) != len(names):
        msg = "The number of names must match the number of images"
        logger.exception(msg)
        raise ValueError(msg)
    res = handle_build_map(images_paths, feature_collection_path, color_palettes, names)  # type: ignore[arg-type]
    logger.info("Successfully built map")
    return {
        "html_content": res,
        "input_arguments": {
            "color_palettes": color_palettes,
            "names": names,
            "feature_collection": feature_collection_path.split("/")[-1],
            "images": [images_paths.split("/")[-1] for images_paths in images_paths],
        },
    }


@mcp.tool(name="delete_temp_dir")
def delete_temp_dir(trace_id: str) -> dict[str, Any]:
    """Delete the temporary directory associated with a processing session.

    This function removes the temporary directory created for a specific trace_id,
    cleaning up all intermediate files generated during the processing session.
    This is typically called at the end of a workflow to free up disk space.

    Args:
        trace_id (str): Unique identifier of the processing session.

    Returns:
        dict[str, Any]: Dictionary containing:
            - input_arguments (dict): Contains 'temp_dir' key with the deleted directory path,
              or a string indicating the directory was already deleted.

    Example:
        >>> delete_temp_dir("session_123")
        {"input_arguments": {"temp_dir": "/path/to/data/session_123"}}
    """
    logger.info("Called delete_temp_dir with trace_id=%s", trace_id)
    temp_dir = Path(f"data/{trace_id}")
    if not temp_dir.exists():
        logger.info("Temporary directory %s already deleted or does not exist", temp_dir)
        return {
            "result": "Temporary directory already deleted or does not exist",
            "input_arguments": {"temp_dir": str(temp_dir)},
        }
    try:
        shutil.rmtree(temp_dir)
        logger.info("Deleted temporary directory %s", temp_dir)
        return {"result": "success", "input_arguments": {"temp_dir": str(temp_dir)}}
    except Exception as e:
        msg = f"Failed to delete temporary directory {temp_dir}: {e}"
        logger.exception(msg)
        return {
            "result": msg,
            "input_arguments": {"temp_dir": str(temp_dir)},
        }


if __name__ == "__main__":
    mcp.run(config.server.transport)  # type: ignore[call-arg]

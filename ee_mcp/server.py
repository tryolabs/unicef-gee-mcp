from config import config
from dotenv import load_dotenv
from handlers import (
    handle_get_all_datasets_and_metadata,
    handle_get_dataset_image,
    handle_mask_image,
)
from initialize import initialize_ee, load_all_datasets
from logging_config import get_logger
from mcp.server.fastmcp import FastMCP
from schemas import DatasetMetadata
from utils import add_input_args_to_result, safe_json_loads

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
@add_input_args_to_result
def get_dataset_image(
    dataset: str,
) -> dict[str, DatasetMetadata | str]:
    """Get an image from Earth Engine and return its JSON representation and metadata.

    Args:
        dataset: The dataset to get the image and metadata for

    Returns:
        A dictionary containing the metadata and JSON representation of the image
        and the input arguments

    Use case:
        Retrieve a global agricultural drought dataset to analyze drought conditions:
        get_dataset_image_and_metadata("agricultural_drought")
    """
    dataset = dataset.lower()
    if dataset not in load_all_datasets(config.path_to_metadata):
        available_datasets = load_all_datasets(config.path_to_metadata)
        msg = f"Invalid dataset '{dataset}'. Available datasets: {available_datasets}"
        logger.error(msg)
        raise ValueError(msg)

    res = handle_get_dataset_image(dataset, config.path_to_metadata)
    return {"image_json": res}


@mcp.tool(name="mask_image")
@add_input_args_to_result
def mask_image(
    image_json: str,
    mask_image_json: str,
) -> dict[str, str]:
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
            "child_population_data.json",
            "hazard_data.json",
        )
    """
    image_json = safe_json_loads(image_json)
    mask_image_json = safe_json_loads(mask_image_json)
    res = handle_mask_image(image_json, mask_image_json)
    return {"image_json": res}


if __name__ == "__main__":
    mcp.run(config.server.transport)

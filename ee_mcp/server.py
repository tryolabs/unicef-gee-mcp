from typing import Any

from config import config
from dotenv import load_dotenv
from handlers import handle_get_dataset_image_and_metadata
from initialize import initialize_ee
from logging_config import get_logger
from mcp.server.fastmcp import FastMCP
from schemas import DatasetMetadata
from utils import add_input_args_to_result

load_dotenv(override=True)

mcp = FastMCP("GEE MCP", port=config.server.port)
initialize_ee(config.path_to_ee_auth)


logger = get_logger(__name__)


@mcp.tool()
@add_input_args_to_result
def get_dataset_image_and_metadata(
    dataset: str,
) -> dict[str, DatasetMetadata | Any]:
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
    res = handle_get_dataset_image_and_metadata(dataset, config.path_to_metadata)
    return res


if __name__ == "__main__":
    mcp.run(config.server.transport)

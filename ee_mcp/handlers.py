from pathlib import Path
from typing import Any

from datasets import get_dataset_metadata
from ee.image import Image
from ee.imagecollection import ImageCollection


def handle_get_dataset_image_and_metadata(
    dataset: str,
    path_to_metadata: Path,
) -> dict[str, Any]:
    """Get an image from Earth Engine and return its JSON representation and metadata.

    Args:
        dataset: The dataset to get the image and metadata for
        path_to_metadata: Path to the metadata YAML file

    Returns:
        A dictionary containing the metadata and JSON representation of the image.
        The metadata includes:
        - image_filename: Name of the image file
        - asset_id: Earth Engine asset identifier
        - description: Description of the dataset
        - source_name: Name of the data source
        - source_url: URL of the data source
        - mosaic: Boolean indicating if this is a mosaic dataset
        - threshold: Optional threshold value for filtering
        - input_arguments: Optional dictionary of input arguments
        - color_palette: Optional list of color palette strings

        The image_json field contains the serialized Earth Engine image object.

    Use case:
        Retrieve a global agricultural drought dataset to analyze drought conditions:
        get_dataset_image_and_metadata("agricultural_drought")
    """
    metadata = get_dataset_metadata(dataset, path_to_metadata)

    if metadata.mosaic:
        image = ImageCollection(metadata.asset_id).mosaic()
    else:
        image = Image(metadata.asset_id)
        if dataset == "agricultural_drought":
            image = image.updateMask(image.lte(100))

    return {
        **metadata.__dict__,
        "image_json": image.serialize(),
    }

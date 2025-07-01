from pathlib import Path

from datasets import load_datasets_metadata
from ee.deserializer import fromJSON
from ee.ee_number import Number
from ee.image import Image
from ee.imagecollection import ImageCollection
from schemas import DatasetMetadata


def handle_get_all_datasets_and_metadata(
    path_to_metadata: Path,
) -> dict[str, DatasetMetadata]:
    """Get all available datasets names and metadata.

    Args:
        path_to_metadata: Path to the metadata YAML file

    Returns:
        A dictionary containing the metadata and JSON representation of the image.
    """
    return load_datasets_metadata(path_to_metadata)


def handle_get_dataset_image(
    dataset: str,
    path_to_metadata: Path,
) -> str:
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
    metadata = load_datasets_metadata(path_to_metadata)[dataset]

    if metadata.mosaic:
        image = ImageCollection(metadata.asset_id).mosaic()
    else:
        image = Image(metadata.asset_id)
        if dataset == "agricultural_drought":
            image = image.updateMask(image.lte(100))

    return image.serialize()


def handle_mask_image(image_json: str, mask_image_json: str) -> str:
    """Mask an Earth Engine image based on a mask.

    Args:
        image_json: JSON string of the Earth Engine image
        mask_image_json: JSON string of the Earth Engine binary image mask.

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the masked Earth Engine image
    """
    image = fromJSON(image_json)
    mask = fromJSON(mask_image_json)
    masked_image = image.updateMask(mask)
    return masked_image.serialize()


def handle_filter_image_by_threshold(image_json: str, threshold: float) -> str:
    """Filter an Earth Engine image based on a threshold value.

    Args:
        image_json: JSON string of the Earth Engine image
        threshold: Numeric value to use as the threshold for filtering

    Returns:
        dict: A dictionary containing:
            - image_json: JSON string of the filtered Earth Engine image
            - input_arguments: The original input arguments used for the operation

    Raises:
        TypeError: If the loaded data is not an Earth Engine Image object
    """
    image = fromJSON(image_json)

    # Create a mask where values are less than threshold
    threshold_ee = Number(threshold)
    filtered_mask = image.lt(threshold_ee) if threshold < 0 else image.gt(threshold_ee)

    return filtered_mask.serialize()

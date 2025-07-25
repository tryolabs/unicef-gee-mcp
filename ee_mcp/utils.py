import json
from ast import literal_eval
from pathlib import Path

from ee.deserializer import fromJSON
from ee.featurecollection import FeatureCollection
from ee.image import Image
from logging_config import get_logger

logger = get_logger(__name__)


def save_ee_object(path: str, serialized_ee_object: str) -> None:
    """Save a serialized Earth Engine object to a file.

    Args:
        path: Path to save the serialized Earth Engine object
        serialized_ee_object: Serialized Earth Engine object to save
    """
    logger.info("Saving vector data to %s", path)

    with Path(path).open("w") as f:
        logger.info("Writing vector data to %s", path)
        json.dump(serialized_ee_object, f)
    logger.info("Saved vector data to %s", path)


def load_ee_object(feature_collection_filename: str) -> FeatureCollection | Image:
    """Load vector data from a JSON file and convert to Earth Engine FeatureCollection or Image.

    Args:
        feature_collection_filename: Path to the JSON file containing the vector data

    Returns:
        Either an Earth Engine FeatureCollection or Image object
    """
    logger.info("Going to load vector data from %s", feature_collection_filename)
    with Path(feature_collection_filename).open("r") as f:
        vector_data = literal_eval(f.read())
        vector_data = fromJSON(vector_data)
    # Get the info without converting to Python dict
    if isinstance(vector_data, Image):
        logger.info("Vector data is an image")
        return vector_data
    elif isinstance(vector_data, FeatureCollection):
        logger.info("Vector data is a feature collection")
        return vector_data
    else:
        if vector_data.getInfo().get("type") == "Image":
            logger.info("Vector data is an image")
            return Image(vector_data)
        elif vector_data.getInfo().get("type") == "FeatureCollection":
            logger.info("Vector data is a feature collection")
            return FeatureCollection(vector_data)
        msg = f"Unknown vector data type: {type(vector_data)}"
        logger.error(msg)
        raise ValueError(msg)

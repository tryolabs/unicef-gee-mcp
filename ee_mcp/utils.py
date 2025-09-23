import json
from ast import literal_eval
from pathlib import Path
from typing import cast

from ee.data import getAsset
from ee.deserializer import fromJSON
from ee.featurecollection import FeatureCollection
from ee.geometry import Geometry
from ee.image import Image
from ee.imagecollection import ImageCollection
from ee.reducer import Reducer
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


def load_image_or_image_collection(asset_id: str) -> Image:
    """Load an EE asset as an Image or mosaicked Image from an ImageCollection.

    If the asset type is IMAGE_COLLECTION, returns ImageCollection(asset_id).mosaic().
    If the asset type is IMAGE, returns Image(asset_id).
    """
    logger.info("Loading asset %s", asset_id)
    try:
        asset_info = getAsset(asset_id)
    except Exception as err:
        msg = f"Failed to retrieve asset metadata for {asset_id}"
        logger.exception(msg)
        raise ValueError(msg) from err

    if not asset_info or "type" not in asset_info:
        msg = f"Asset not found or missing type for {asset_id}"
        logger.error(msg)
        raise ValueError(msg)

    asset_type = str(asset_info.get("type", "")).upper()
    if "IMAGE_COLLECTION" in asset_type:
        logger.info("Asset is an ImageCollection; returning mosaicked Image")
        return ImageCollection(asset_id).mosaic()
    if "IMAGE" in asset_type:
        logger.info("Asset is an Image; returning Image")
        return Image(asset_id)

    msg = f"Unsupported asset type '{asset_type}' for {asset_id}"
    logger.error(msg)
    raise ValueError(msg)


def get_threshold(image_path: str) -> float:
    logger.info("Calculating mean threshold")
    # Create a land-sea mask by converting the reprojected country boundaries to a raster.
    # Land pixels will have a value of 1 and sea pixels will be 0.
    aois = FeatureCollection("projects/unicef-ccri/assets/adm0_simple")

    reference_image = Image("projects/unicef-ccri/assets/heatwave_frequency_2014_2023_avg")
    target_scale = reference_image.projection().nominalScale()
    target_crs = reference_image.projection()

    country_boundaries_reprojected = aois.map(  # type: ignore[misc]
        lambda feature: feature.transform(target_crs)  # type: ignore[misc]
    )

    land_sea_mask = (
        Image(1)
        .clip(country_boundaries_reprojected)
        .unmask(0)
        .reproject(crs=target_crs, scale=target_scale)
        .rename("landsea_mask")  # type: ignore[misc]
    )

    # Mask the hazard layer to include only land pixels using the land_sea_mask.
    hazard_layer = load_ee_object(image_path)
    if not isinstance(hazard_layer, Image):
        msg = "Image must be an Earth Engine image"
        logger.exception(msg)
        raise TypeError(msg)

    hazard_layer_masked = hazard_layer.updateMask(land_sea_mask)

    global_geometry = Geometry.Polygon(  # type: ignore[arg-type]
        [
            [
                [-180, 90],
                [-180, -90],
                [180, -90],
                [180, 90],
            ],
        ],
        None,
        False,
    )

    # Compute the mean hazard value over the global land area.
    threshold = (
        hazard_layer_masked.reduceRegion(
            reducer=Reducer.mean(),
            geometry=global_geometry,  # type: ignore[arg-type]
            scale=hazard_layer.projection().nominalScale(),
            bestEffort=True,
        )
        .values()
        .get(0)
    )
    threshold = cast("float", threshold.getInfo())
    logger.info("Threshold: %s", threshold)
    return threshold

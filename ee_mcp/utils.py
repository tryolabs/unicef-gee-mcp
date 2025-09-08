import json
from ast import literal_eval
from pathlib import Path
from typing import cast

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


def get_threshold(asset_id: str, *, mosaic: bool) -> float:
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
    hazard_layer = ImageCollection(asset_id).mosaic() if mosaic else Image(asset_id)
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

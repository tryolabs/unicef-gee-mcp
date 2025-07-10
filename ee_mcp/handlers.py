from pathlib import Path
from typing import cast

import ee
import geemap.foliumap as geemap
import pycountry
from constants import ADMIN_LEVEL_1_BOUNDRIES_DATASET, COUNTRY_BOUNDRIES_DATASET
from datasets import load_datasets_metadata
from ee.deserializer import fromJSON
from ee.ee_number import Number
from ee.errormargin import ErrorMargin
from ee.feature import Feature
from ee.featurecollection import FeatureCollection
from ee.filter import Filter
from ee.image import Image
from ee.imagecollection import ImageCollection
from ee.reducer import Reducer
from logging_config import get_logger
from schemas import AREA_TYPES, REDUCERS, DatasetMetadata

logger = get_logger(__name__)

TH_SHAPE_AREA = 33


def handle_get_all_datasets_and_metadata(
    path_to_metadata: Path,
) -> dict[str, DatasetMetadata]:
    """Get all available datasets names and metadata.

    Args:
        path_to_metadata: Path to the metadata YAML file

    Returns:
        dict[str, DatasetMetadata]: A dictionary containing the metadata for all datasets.
    """
    metadata = load_datasets_metadata(path_to_metadata)
    logger.info("Loaded %d datasets", len(metadata))
    return metadata


def handle_get_dataset_image(
    dataset: str,
    path_to_metadata: Path,
) -> str:
    """Get an image from Earth Engine and return its JSON representation.

    Args:
        dataset: The dataset to get the image for
        path_to_metadata: Path to the metadata YAML file

    Returns:
        str: JSON string of the Earth Engine image object.

    Use case:
        Retrieve a global agricultural drought dataset to analyze drought conditions:
        get_dataset_image_and_metadata("agricultural_drought")
    """
    try:
        metadata = load_datasets_metadata(path_to_metadata)[dataset]
        logger.debug("Found metadata for dataset %s: %s", dataset, metadata)
    except KeyError as err:
        available_datasets = list(load_datasets_metadata(path_to_metadata).keys())
        msg = f"Invalid dataset '{dataset}'. Available datasets: {available_datasets}"
        logger.exception(msg)
        raise KeyError(msg) from err

    if metadata.mosaic:
        logger.debug("Creating mosaic image for dataset %s", dataset)
        image = ImageCollection(metadata.asset_id).mosaic()
    else:
        logger.debug("Creating single image for dataset %s", dataset)
        image = Image(metadata.asset_id)
        if dataset == "agricultural_drought":
            logger.debug("Applying mask for agricultural drought dataset")
            image = image.updateMask(image.lte(100))

    return image.serialize()


def handle_mask_image(image_json: str, mask_image_json: str) -> str:
    """Mask an Earth Engine image based on a mask.

    Args:
        image_json: JSON string of the Earth Engine image
        mask_image_json: JSON string of the Earth Engine binary image mask.

    Returns:
        str: JSON string of the masked Earth Engine image
    """
    image: Image = fromJSON(image_json)
    mask: Image = fromJSON(mask_image_json)
    masked_image = image.updateMask(mask)
    return masked_image.serialize()


def handle_filter_image_by_threshold(image_json: str, threshold: float) -> str:
    """Filter an Earth Engine image based on a threshold value.

    Args:
        image_json: JSON string of the Earth Engine image
        threshold: Numeric value to use as the threshold for filtering

    Returns:
        str: JSON string of the filtered Earth Engine image

    Raises:
        TypeError: If the loaded data is not an Earth Engine Image object
    """
    image = fromJSON(image_json)

    # Create a mask where values are less than threshold
    threshold_ee: Number = Number(threshold)
    filtered_mask: Image = image.lt(threshold_ee) if threshold < 0 else image.gt(threshold_ee)

    return filtered_mask.serialize()


def handle_union_binary_images(
    binary_images_jsons: list[str],
) -> str:
    """Union multiple binary images.

    Args:
        binary_images_jsons: List of JSON strings of the binary images to union.
            Each JSON should point to a valid Earth Engine Image.

    Returns:
        str: JSON string of the union result
    """
    # Unmask the image to ensure non-data is treated as 0
    union: Image = fromJSON(binary_images_jsons[0]).unmask(0)
    for i, path in enumerate(binary_images_jsons[1:], 1):
        logger.debug("Processing image %d of %d for union", i + 1, len(binary_images_jsons))
        new_data: Image = fromJSON(path).unmask(0)
        union = union.Or(new_data)

    return union.serialize()


def handle_intersect_binary_images(
    binary_images_jsons: list[str],
) -> str:
    """Intersect multiple binary images.

    Args:
        binary_images_jsons: List of JSON strings of the binary images to intersect.
            Each JSON should point to a valid Earth Engine Image.

    Returns:
        str: JSON string of the intersection result
    """
    intersection: Image = fromJSON(binary_images_jsons[0])
    for i, path in enumerate(binary_images_jsons[1:], 1):
        logger.debug("Processing image %d of %d for intersection", i + 1, len(binary_images_jsons))
        new_data: Image = fromJSON(path)
        intersection = intersection.And(new_data)

    return intersection.serialize()


def handle_intersect_feature_collections(feature_collections_jsons: list[str]) -> str:
    """Perform a geometric intersection of multiple feature collections.

    Args:
        feature_collections_jsons: List of JSON strings of the feature collections to intersect.
            Each JSON should point to a valid Earth Engine FeatureCollection.

    Returns:
        str: JSON string of the intersection result

    Raises:
        TypeError: If any input is an Image
    """
    intersection = fromJSON(feature_collections_jsons[0])
    if isinstance(intersection, Image):
        msg = "Image cannot be intersected"
        logger.exception(msg)
        raise TypeError(msg)

    for i, path in enumerate(feature_collections_jsons[1:], 1):
        logger.debug(
            "Processing feature collection %d of %d for intersection",
            i + 1,
            len(feature_collections_jsons),
        )
        new_fc = fromJSON(path)
        if isinstance(new_fc, Image):
            msg = "Image cannot be intersected"
            logger.exception(msg)
            raise TypeError(msg)
        intersection = intersection.map(
            lambda f, fc=new_fc: intersect_feature(cast("Feature", f), fc)
        )

    return intersection.serialize()


def handle_merge_feature_collections(feature_collections_jsons: list[str]) -> str:
    """Merge multiple feature collections into a single combined collection.

    Args:
        feature_collections_jsons: List of JSON strings of the feature collections to merge.
            Each JSON should point to a valid Earth Engine FeatureCollection.

    Returns:
        str: JSON string of the merged result

    Raises:
        TypeError: If any input is an Image
    """
    union = fromJSON(feature_collections_jsons[0])
    if isinstance(union, Image):
        msg = "Image cannot be unioned"
        logger.exception(msg)
        raise TypeError(msg)

    for i, path in enumerate(feature_collections_jsons[1:], 1):
        logger.debug(
            "Processing feature collection %d of %d for merge",
            i + 1,
            len(feature_collections_jsons),
        )
        new_data = fromJSON(path)
        if isinstance(new_data, Image):
            msg = "Image cannot be unioned"
            logger.exception(msg)
            raise TypeError(msg)
        union = union.merge(new_data).union()

    return union.serialize()


def intersect_feature(feature: Feature, feature_collection: FeatureCollection) -> Feature:
    """Intersect a feature with a feature collection.

    Computes the geometric intersection between a feature and a feature collection,
    preserving the properties of the input feature.

    Args:
        feature: The feature to intersect
        feature_collection: The feature collection to intersect with

    Returns:
        Feature: A new feature representing the intersection, with properties copied from
                the input feature
    """
    intersected = feature.geometry().intersection(feature_collection.geometry(), ErrorMargin(100))
    return Feature(Feature(intersected).copyProperties(feature))


def handle_reduce_image(
    image_json: str,
    feature_collection_json: str,
    reducer: REDUCERS,
    scale: float = 92.76624195666344,  # scale of child population data
) -> float:
    """Reduce an image by applying a reducer to its pixels within specified regions.

    Args:
        image_json: The JSON string of the image to reduce
        feature_collection_json: The JSON string of the geometry to reduce the image to
        reducer: The reducer to apply
        scale: The scale of the image. It should be 100 unless otherwise specified.

    Returns:
        float: The reduced value

    Raises:
        ValueError: If no statistics are found
    """
    image: Image = fromJSON(image_json)
    feature_collection: FeatureCollection = fromJSON(feature_collection_json)
    reduced = image.reduceRegions(
        reducer=getattr(Reducer, reducer)(),
        collection=feature_collection,
        scale=scale,
        crs="EPSG:4326",
    )
    logger.debug("Getting statistics from reduced regions")
    stats = reduced.getInfo()

    if stats is None:
        msg = "No statistics found"
        logger.exception(msg)
        raise ValueError(msg)

    aggregation_result = 0
    feature_count = len(stats["features"])
    logger.debug("Processing %d features for aggregation", feature_count)
    for feature in stats["features"]:
        aggregation_result += feature["properties"][reducer]

    return aggregation_result


def handle_get_zone_of_area(area_name: str, area_type: AREA_TYPES) -> str:
    """Get the zone boundary for a specified area.

    Args:
        area_name: Name of the area to get boundary for.
                If it is a country, it should be the ISO 3166-1 alpha-3 code.
        area_type: Type of area - either 'country' or 'admin1'. Determines which
            dataset to query.

    Returns:
        str: A JSON string of the zone boundary.
    """
    if area_type == "country":
        area_name = get_country_code(area_name)
        logger.debug("Using country code: %s", area_name)
        countries_boundries = FeatureCollection(COUNTRY_BOUNDRIES_DATASET)

        area_boundry = countries_boundries.filter(Filter.eq("iso3", area_name))

        shape_area = area_boundry.first().getNumber("Shape_Area")

        simplification_tolerance = ee.Algorithms.If(
            shape_area.gt(Number(TH_SHAPE_AREA)), 10000, 100
        )

        area_boundry = FeatureCollection(area_boundry.geometry().simplify(simplification_tolerance))

    else:
        logger.debug("Using admin level 1 boundaries for area: %s", area_name)
        admin_level_1_boundries = FeatureCollection(ADMIN_LEVEL_1_BOUNDRIES_DATASET)
        area_boundry = admin_level_1_boundries.filter(Filter.eq("shapeName", area_name))

    area_boundry_json = area_boundry.serialize()

    return area_boundry_json


def standarize_country_name(country: str) -> str:
    """Standardize a country name to its official form.

    Uses pycountry to look up the official name of a country from various input formats.

    Args:
        country: Country name, 2-letter code, or 3-letter code to standardize.

    Returns:
        str: Official country name if found, otherwise returns the input unchanged.
    """
    try:
        country_obj = (
            pycountry.countries.get(name=country)
            or pycountry.countries.get(alpha_2=country)
            or pycountry.countries.get(alpha_3=country)
        )
        if country_obj:
            logger.debug("Found standardized country name: %s", country_obj.name)
            return country_obj.name
        else:
            logger.debug("Country not found in pycountry, returning original: %s", country)
            return country
    except KeyError:
        logger.debug("KeyError occurred, returning original country name: %s", country)
        return country


def get_country_code(country: str) -> str:
    """Get the 3-letter ISO country code for a country.

    Standardizes the country name first, then looks up its ISO 3166-1 alpha-3 code.

    Args:
        country: Country name, 2-letter code, or 3-letter code to look up.

    Returns:
        str: 3-letter ISO country code if found, otherwise returns the input unchanged.
    """
    try:
        country = standarize_country_name(country)
        country_obj = pycountry.countries.get(name=country)
        if country_obj:
            logger.debug("Found country code: %s", country_obj.alpha_3)
            return country_obj.alpha_3
        else:
            logger.debug("Country code not found, returning original: %s", country)
            return country
    except KeyError:
        logger.debug("KeyError occurred, returning original country: %s", country)
        return country


def handle_build_map(
    images_json: list[str],
    feature_collection_json: str,
    color_palettes: list[list[str]],
    names: list[str],
) -> str:
    """Build a map from images and vector data and save it to an HTML file.

    Args:
        images_json: List of JSON strings of the Earth Engine images to display on the map
        feature_collection_json: JSON string of the vector data (e.g. GeoJSON) defining the
            boundaries to overlay the images on
        color_palettes: List of color palettes to use for each image layer. Each palette should
            be a list of color strings (e.g. ["#ff0000", "#00ff00"])
        names: List of names for each image layer. Must match length of images_json.

    Returns:
        str: The filename of the saved HTML map file
    """
    # Deserialize the JSON strings to Earth Engine objects
    images = [fromJSON(image_json) for image_json in images_json]
    vector_data = fromJSON(feature_collection_json)

    demographic_map = geemap.Map(basemap="UN.ClearMap")

    default_color_palette = ["#F4E7E1", "#FF9B45", "#D5451B", "#521C0D"]

    for i, image in enumerate(images):
        logger.info("Adding layer %s", names[i])
        clipped_image = image.clip(vector_data)
        # Apply mask to show only non-zero values
        masked_image: Image = clipped_image.updateMask(clipped_image.gt(0))

        max_value = list(
            masked_image.reduceRegion(
                reducer=Reducer.max(),
                geometry=vector_data.geometry(),
                scale=1000,
                maxPixels=int(1e9),
            )
            .getInfo()
            .values()  # type: ignore[misc]
        )[0]

        vis_params = {
            "min": 0,
            "max": max_value,
            "palette": (color_palettes[i] if color_palettes[i] != [] else default_color_palette),
        }

        demographic_map.add_layer(masked_image, vis_params, names[i])  # type: ignore[misc]

    demographic_map.center_object(vector_data, max_error=0.1)  # type: ignore[misc]

    # Generate HTML string and return it
    html_string = demographic_map.to_html()  # type: ignore[misc]

    if html_string is None:
        msg = "Failed to generate HTML string"
        logger.exception(msg)
        raise ValueError(msg)

    return html_string

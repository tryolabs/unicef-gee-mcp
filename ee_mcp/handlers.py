from pathlib import Path
from typing import cast

import ee
import pycountry
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
from schemas import AREA_TYPES, REDUCERS, DatasetMetadata

BASE_ASSETS_PATH = "projects/unicef-ccri/assets"
COUNTRY_BOUNDRIES_DATASET = f"{BASE_ASSETS_PATH}/adm0_wfp"
ADMIN_LEVEL_1_BOUNDRIES_DATASET = "WM/geoLab/geoBoundaries/600/ADM1"
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
    return load_datasets_metadata(path_to_metadata)


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
    for path in binary_images_jsons[1:]:
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
    for path in binary_images_jsons[1:]:
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
        raise TypeError(msg)

    for path in feature_collections_jsons[1:]:
        new_fc = fromJSON(path)
        if isinstance(new_fc, Image):
            msg = "Image cannot be intersected"
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
        raise TypeError(msg)

    for path in feature_collections_jsons[1:]:
        new_data = fromJSON(path)
        if isinstance(new_data, Image):
            msg = "Image cannot be unioned"
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
    stats = reduced.getInfo()

    if stats is None:
        msg = "No statistics found"
        raise ValueError(msg)

    aggregation_result = 0
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
        countries_boundries = FeatureCollection(COUNTRY_BOUNDRIES_DATASET)

        area_boundry = countries_boundries.filter(Filter.eq("iso3", area_name))

        shape_area = area_boundry.first().getNumber("Shape_Area")

        simplification_tolerance = ee.Algorithms.If(
            shape_area.gt(Number(TH_SHAPE_AREA)), 10000, 100
        )

        area_boundry = FeatureCollection(area_boundry.geometry().simplify(simplification_tolerance))

    else:
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
            return country_obj.name
        else:
            return country
    except KeyError:
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
            return country_obj.alpha_3
        else:
            return country
    except KeyError:
        return country

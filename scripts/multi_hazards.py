import logging
import os
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "ee_mcp"))
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent / "ee_mcp")

from ee.image import Image
from ee.imagecollection import ImageCollection

from ee_mcp.config import config as app_config
from ee_mcp.handlers import (
    handle_filter_image_by_threshold,
    handle_get_all_datasets_and_metadata,
    handle_get_zone_of_area,
    handle_intersect_binary_images,
    handle_mask_image,
    handle_reduce_image,
    handle_union_binary_images,
)
from ee_mcp.initialize import initialize_ee
from ee_mcp.utils import save_ee_object

logger = logging.getLogger("multi_hazards")
logging.basicConfig(level=logging.INFO)


def calculate_multi_hazard_exposure(
    datasets: list[str],
    country_name: str = "Colombia",
) -> dict[str, Any]:
    """Calculate exposure of children to multiple hazards for a given country.

    Returns a dictionary with sums for both hazards, either hazard, and per-dataset sums.
    """
    output_dir = Path("data/123")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load metadata and initialize Earth Engine
    initialize_ee(app_config.path_to_ee_auth)
    metadata = handle_get_all_datasets_and_metadata(app_config.path_to_metadata)

    # Prepare binary hazard masks (saved as files for handler compatibility)
    binary_mask_paths: list[str] = []
    for dataset_name in datasets:
        dataset_meta = metadata[dataset_name]
        if dataset_meta.mosaic:
            image = ImageCollection(dataset_meta.asset_id).mosaic()
        else:
            image = Image(dataset_meta.asset_id)
            if dataset_name == "agricultural_drought":
                image = image.updateMask(image.lte(100))

        image_json = image.serialize()
        image_path = str(output_dir / f"image_{dataset_name}.json")
        save_ee_object(image_path, image_json)

        threshold = float(dataset_meta.threshold or 0)
        binary_json = handle_filter_image_by_threshold(image_path, threshold)
        binary_path = str(output_dir / f"binary_{dataset_name}.json")
        save_ee_object(binary_path, binary_json)
        binary_mask_paths.append(binary_path)

    # Build boolean combinations
    both_json = handle_intersect_binary_images(binary_mask_paths)
    either_json = handle_union_binary_images(binary_mask_paths)
    both_path = str(output_dir / "both_hazard_zones.json")
    either_path = str(output_dir / "either_hazard_zones.json")
    save_ee_object(both_path, both_json)
    save_ee_object(either_path, either_json)

    # Children population image
    child_meta = metadata["children_population"]
    child_image = ImageCollection(child_meta.asset_id).mosaic()
    child_image_path = str(output_dir / "children_population.json")
    save_ee_object(child_image_path, child_image.serialize())

    # Mask children population with hazard zones
    masked_both_json = handle_mask_image(child_image_path, both_path)
    masked_either_json = handle_mask_image(child_image_path, either_path)
    masked_both_path = str(output_dir / "children_population_hazard_both.json")
    masked_either_path = str(output_dir / "children_population_hazard_either.json")
    save_ee_object(masked_both_path, masked_both_json)
    save_ee_object(masked_either_path, masked_either_json)

    masked_dataset_paths: list[str] = [
        str(output_dir / f"children_population_hazard_{name}.json") for name in datasets
    ]
    for dataset_name, masked_dataset_path in zip(datasets, masked_dataset_paths, strict=True):
        mask_path = str(output_dir / f"binary_{dataset_name}.json")
        masked_dataset_json = handle_mask_image(child_image_path, mask_path)
        save_ee_object(masked_dataset_path, masked_dataset_json)

    # Country zone
    zone_json = handle_get_zone_of_area(country_name, "country")
    zone_path = str(output_dir / f"zone_{country_name}.json")
    save_ee_object(zone_path, zone_json)

    # Reduce (sum) over country
    both_sum = handle_reduce_image(masked_both_path, zone_path, "sum")
    either_sum = handle_reduce_image(masked_either_path, zone_path, "sum")

    dataset_sums: list[float] = [
        handle_reduce_image(path, zone_path, "sum") for path in masked_dataset_paths
    ]

    return {
        "both_hazard_sum": both_sum,
        "either_hazard_sum": either_sum,
        **{f"dataset{i + 1}_hazard_sum": value for i, value in enumerate(dataset_sums)},
        "paths": {
            "both_hazard_zones": both_path,
            "either_hazard_zones": either_path,
            "children_population": child_image_path,
            "zone": zone_path,
        },
    }


if __name__ == "__main__":
    countries = ["Colombia", "Angola", "Nicaragua", "Uruguay"]
    for country in countries:
        result = calculate_multi_hazard_exposure(
            ["plasmodium_vivax", "plasmodium_falciparum"], country
        )
        logger.info("Country: %s", country)
        logger.info("Both: %s", result["both_hazard_sum"])
        logger.info("Either: %s", result["either_hazard_sum"])
        logger.info("Dataset 1: %s", result.get("dataset1_hazard_sum"))
        logger.info("Dataset 2: %s", result.get("dataset2_hazard_sum"))

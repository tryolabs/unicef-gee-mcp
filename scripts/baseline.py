"""Baseline extraction script for benchmarking hazard exposure per country (ADM0)."""

import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "ee_mcp"))
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent / "ee_mcp")

from ee.ee_number import Number
from ee.featurecollection import FeatureCollection
from ee.filter import Filter
from ee.geometry import Geometry
from ee.image import Image
from ee.imagecollection import ImageCollection
from ee.reducer import Reducer

from ee_mcp.initialize import initialize_ee

logger = logging.getLogger("baseline")
logging.basicConfig(level=logging.INFO)

initialize_ee(Path("ee_auth.json"))

# %%
all_hazards = [
    {
        "id": "projects/unicef-ccri/assets/river_flood_r100",
        "threshold": 0.01,
        "name": "river_flood_100yr_jrc_2024",
    },
    {
        "id": "projects/unicef-ccri/assets/coastal_flood_r100",
        "threshold": 0,
        "name": "coastal_flood_100yr_jrc_2024",
    },
    {
        "id": "projects/unicef-ccri/assets/storm_giri_rp100",
        "threshold": 17.5,
        "name": "tropical_storm_100yr_giri_2024",
    },
    {
        "id": "projects/unicef-ccri/assets/ASI_return_level_100yr",
        "threshold": 30,
        "name": "agricultural_drought_fao_1984-2023",
    },
    {
        "id": "projects/unicef-ccri/assets/spei12_period_mean_2014_2024",
        "threshold": -1,
        "name": "drought_spei_copernicus_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/spi12_period_mean_2014_2024",
        "threshold": -1,
        "name": "drought_spi_copernicus_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/heatwave_frequency_return_level_100yr",
        "threshold": "Mean",  # 16.8
        "name": "heatwave_frequency_ecmwf_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/heatwave_duration_return_level_100yr",
        "threshold": "Mean",  # 92.4
        "name": "heatwave_duration_ecmwf_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/heatwave_severity_return_level_100yr",
        "threshold": "Mean",  # 3.6
        "name": "heatwave_severity_ecmwf_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/high_temp_degree_days_return_level_100yr",
        "threshold": 35,
        "name": "extreme_heat_ecmwf_2014-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/FIRMS_FRP_90th_percentile",
        "threshold": "Mean",
        "name": "fire_FRP_nasa_2001-2024",
    },
    {
        "id": "projects/unicef-ccri/assets/FIRMS_count_90th_percentile",
        "threshold": "Mean",
        "name": "fire_frequency_nasa_2001-2023",
    },
    {
        "id": "projects/unicef-ccri/assets/sand_dust_storm_annual",
        "threshold": 0,
        "name": "sand_dust_storm_unccd_2024",
    },
    {
        "id": "projects/unicef-ccri/assets/pm25_p90_1998_2023",
        "threshold": 5,
        "name": "air_pollution_pm25_1998-2023",
    },
    {
        "id": "projects/unicef-ccri/assets/Pv_average_2013_2022",
        "threshold": 0.001,
        "name": "vectorborne_malariapv_2012-2022",
    },
    {
        "id": "projects/unicef-ccri/assets/Pf_average_2013_2022",
        "threshold": 0.001,
        "name": "vectorborne_malariapf_2012-2022",
    },
]


def get_threshold(hazard_layer: Image) -> Number:
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
    return Number(threshold)


# %%
countries = ["AGO", "NIC", "URY", "COL"]
full_df = pd.DataFrame(columns=["country", "id", "value"])
for hazard in all_hazards:
    df_hazard = pd.DataFrame(columns=["country", "id", "value"])
    for country in countries:
        asset_id_string = hazard["id"]
        threshold_value_input = hazard["threshold"]
        logger.info(
            "Processing %s with threshold %s for %s",
            asset_id_string,
            threshold_value_input,
            country,
        )

        if asset_id_string in {
            "projects/unicef-ccri/assets/river_flood_r100",
            "projects/unicef-ccri/assets/coastal_flood_r100",
            "projects/unicef-ccri/assets/storm_giri_rp100",
        }:
            hazard_layer = ImageCollection(asset_id_string).mosaic()
        else:
            hazard_layer = Image(asset_id_string)

        childpop = ImageCollection("projects/unicef-ccri/assets/childpop_constrained").mosaic()

        aois = FeatureCollection("projects/unicef-ccri/assets/adm0_simple")
        if country:
            logger.info("Filtering by country")
            aois = aois.filter(Filter.eq("ISO3", country))

        if threshold_value_input == "Mean":
            threshold_number = get_threshold(hazard_layer)
        else:
            threshold_number = Number(float(threshold_value_input))

        threshold_val: float = cast("float", threshold_number.getInfo())
        logger.info("Threshold: %s", threshold_val)

        if asset_id_string == "projects/unicef-ccri/assets/ASI_cropland_avg_2014_2023":
            logger.info("Updating mask for agricultural drought")
            hazard_layer = hazard_layer.updateMask(hazard_layer.lte(100))
            exposed_population = childpop.updateMask(hazard_layer.gt(threshold_number))
        elif threshold_val < 0:
            logger.info("Updating mask for negative threshold")
            exposed_population = childpop.updateMask(hazard_layer.lt(threshold_number))
        else:
            logger.info("Updating mask for positive threshold")
            exposed_population = childpop.updateMask(hazard_layer.gt(threshold_number))

        population_by_aoi = exposed_population.reduceRegions(
            collection=aois,
            reducer=Reducer.sum(),
            scale=100,
            crs="EPSG:4326",
        )

        final_collection = population_by_aoi.map(
            lambda feature: feature.set("child_population_exposed", feature.get("sum"))  # type: ignore[misc]
        )

        res = final_collection.getInfo()
        logger.info(
            "Finish processing, %s with threshold %s for %s",
            asset_id_string,
            threshold_val,
            country,
        )

        # Convert results to DataFrame
        features = res["features"]
        rows: list[dict[str, Any]] = []
        for feature in features:
            properties = feature["properties"]
            rows.append(properties)

        result_df = pd.DataFrame(rows)
        df_hazard.loc[len(df_hazard)] = [
            country,
            asset_id_string,
            result_df["child_population_exposed"],
        ]
        full_df.loc[len(full_df)] = [
            country,
            asset_id_string,
            result_df["child_population_exposed"],
        ]

    # Export to CSV
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{hazard['name']}_exposure_adm0.csv"
    df_hazard.to_csv(output_file, index=False)
    logger.info("Results exported to %s", output_file)

# %%

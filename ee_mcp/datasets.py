from pathlib import Path
from typing import Any

import yaml
from schemas import DatasetMetadata, load_all_datasets_enum

BASE_ASSETS_PATH = "projects/unicef-ccri/assets"


def get_dataset_metadata(dataset: str, path_to_metadata: Path) -> DatasetMetadata:
    """Get metadata for a dataset.

    Args:
        dataset: The dataset name to get metadata for
        path_to_metadata: Path to the metadata YAML file

    Returns:
        DatasetMetadata: The metadata for the specified dataset

    Raises:
        KeyError: If the dataset is not found in the metadata
        ValueError: If the metadata file is invalid or missing
    """
    all_datasets_enum = load_all_datasets_enum(path_to_metadata)
    if all_datasets_enum is None:
        msg = "Failed to load datasets enum"
        raise ValueError(msg)

    # Convert string dataset name to enum value
    enum_value = getattr(all_datasets_enum, dataset.upper(), None)
    if enum_value is None:
        msg = f"Dataset '{dataset}' not found"
        raise KeyError(msg)

    metadata = load_datasets_metadata(path_to_metadata)[enum_value]
    return metadata


def load_datasets_metadata(path_to_metadata: Path) -> dict[Any, DatasetMetadata]:
    """Load dataset metadata from YAML file and convert to the expected format.

    Args:
        path_to_metadata: Path to the metadata YAML file containing dataset configurations

    Returns:
        dict[Any, DatasetMetadata]: Dictionary mapping dataset enum values to their metadata

    Raises:
        FileNotFoundError: If the metadata file doesn't exist
        ValueError: If the YAML structure is invalid or missing required keys
        yaml.YAMLError: If there's an error parsing the YAML file
    """
    metadata: dict[Any, DatasetMetadata] = {}
    try:
        with path_to_metadata.open("r") as file:
            data = yaml.safe_load(file)

        all_datasets_enum = load_all_datasets_enum(path_to_metadata)

        for dataset_name, dataset_config in data["datasets"].items():
            # Convert the dataset name to the corresponding enum value
            enum_name = dataset_name.upper()
            if hasattr(all_datasets_enum, enum_name):
                enum_value = getattr(all_datasets_enum, enum_name)

                if "asset_id" in dataset_config:
                    dataset_config["asset_id"] = f"{BASE_ASSETS_PATH}/{dataset_config['asset_id']}"

                metadata[enum_value] = DatasetMetadata(**dataset_config)

    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        msg = f"Error loading datasets metadata: {e}"
        raise ValueError(msg) from e

    return metadata

from pathlib import Path

import yaml
from schemas import DatasetMetadata

BASE_ASSETS_PATH = "projects/unicef-ccri/assets"


def load_datasets_metadata(path_to_metadata: Path) -> dict[str, DatasetMetadata]:
    """Load dataset metadata from YAML file and convert to the expected format.

    Args:
        path_to_metadata: Path to the metadata YAML file containing dataset configurations

    Returns:
        dict[str, DatasetMetadata]: Dictionary mapping dataset names to their metadata

    Raises:
        FileNotFoundError: If the metadata file doesn't exist
        ValueError: If the YAML structure is invalid or missing required keys
        yaml.YAMLError: If there's an error parsing the YAML file
    """
    metadata: dict[str, DatasetMetadata] = {}
    try:
        with path_to_metadata.open("r") as file:
            data = yaml.safe_load(file)

        for dataset_name, dataset_config in data["datasets"].items():
            if "asset_id" in dataset_config:
                dataset_config["asset_id"] = f"{BASE_ASSETS_PATH}/{dataset_config['asset_id']}"

                metadata[dataset_name] = DatasetMetadata(**dataset_config)

    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        msg = f"Error loading datasets metadata: {e}"
        raise ValueError(msg) from e

    return metadata

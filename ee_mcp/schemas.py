from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class ServerConfig:
    port: int
    transport: Literal["stdio", "sse", "streamable-http"]


@dataclass
class Config:
    server: ServerConfig
    path_to_metadata: Path
    path_to_ee_auth: Path


@dataclass
class DatasetMetadata:
    image_filename: str
    asset_id: str
    description: str
    source_name: str
    source_url: str
    mosaic: bool = False
    threshold: float | None = None
    input_arguments: dict[str, Any] | None = None
    color_palette: list[str] | None = None


def load_all_datasets_enum(path_to_metadata: Path) -> Enum | None:
    """Load dataset names from the YAML metadata file and create enum values."""
    try:
        with path_to_metadata.open("r") as file:
            data = yaml.safe_load(file)
            if data and "datasets" in data:
                dataset_names = list(data["datasets"].keys())
                all_datasets = Enum(
                    "ALL_DATASETS",
                    {name.upper(): name for name in dataset_names},
                    type=str,
                )
                return all_datasets

    except (FileNotFoundError, yaml.YAMLError):
        msg = "Failed to load dataset metadata"
        raise ValueError(msg) from None


REDUCERS = Literal["mean", "max", "min", "sum", "median", "std"]
AREA_TYPES = Literal["country", "admin1"]

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class ServerConfig:
    port: int
    transport: Literal["stdio", "sse", "streamable-http"]


@dataclass
class Config:
    server: ServerConfig


def load_all_datasets_enum() -> Enum | None:
    """Load dataset names from the YAML metadata file and create enum values."""
    from constants import PATH_TO_HAZARDS_METADATA

    try:
        with Path(PATH_TO_HAZARDS_METADATA).open("r") as file:
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

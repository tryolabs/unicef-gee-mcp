from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Transport = Literal["stdio", "sse", "streamable-http"]


@dataclass
class ServerConfig:
    port: int
    transport: Transport


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


REDUCERS = Literal["mean", "max", "min", "sum", "median", "std"]
AREA_TYPES = Literal["country", "admin1"]

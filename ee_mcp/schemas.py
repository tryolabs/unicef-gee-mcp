from dataclasses import dataclass
from typing import Literal


@dataclass
class ServerConfig:
    port: int
    transport: Literal["stdio", "sse", "streamable-http"]


@dataclass
class Config:
    server: ServerConfig

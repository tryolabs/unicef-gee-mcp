# UNICEF Google Earth Engine MCP Server

The UNICEF Google Earth Engine (GEE) MCP Server provides access to geospatial data and analysis capabilities through Google Earth Engine. This Model Context Protocol (MCP) server exposes specialized tools for querying, processing, and visualizing geospatial datasets related to children's environmental risks and demographics.

## Overview

This MCP server serves as the geospatial data backend for the UNICEF Geosphere project, providing access to:

- **Hazard Datasets**: Natural disaster and climate risk data (floods, droughts, heatwaves, storms)
- **Demographic Data**: Population and children-specific spatial datasets
- **Spatial Analysis**: Advanced geospatial processing and visualization tools

## Features

### Core Capabilities

- **Dataset Discovery**: Browse available hazard and demographic datasets
- **Image Processing**: Filter, mask, threshold, and combine geospatial images
- **Feature Operations**: Spatial intersections, unions, and merging
- **Spatial Analysis**: Zonal statistics and area calculations
- **Map Generation**: Interactive HTML map creation with visualizations

### Specialized Functions

- **Multi-hazard Analysis**: Combine different hazard datasets
- **Population Exposure**: Calculate children at risk from environmental hazards
- **Custom Visualizations**: Generate maps with UNICEF-specific styling

## Technology Stack

- **Google Earth Engine**: Planetary-scale geospatial analysis, official GEE client library
- **FastMCP**: Model Context Protocol server framework
- **Folium**: Interactive map generation

## Project Structure

```
ee_mcp/
├── server.py              # MCP server and tool definitions
├── handlers.py            # Tool implementation and business logic
├── config.py              # Configuration and settings management
├── initialize.py          # Google Earth Engine authentication setup
├── datasets.py            # Dataset catalog and metadata
├── utils.py               # Utility functions for data processing
├── schemas.py             # Pydantic models and validation
├── constants.py           # Application constants
├── hazards_metadata.yaml  # Comprehensive dataset metadata
├── config.yaml            # Server configuration
└── logging_config.py      # Logging setup
```

## Prerequisites

Before setting up the UNICEF GEE MCP Server, ensure you have:

- An active Google Cloud Project with Earth Engine API enabled
- A dedicated service account with JSON key file for server authentication
- Earth Engine access permissions granted to the service account
- Permissions to access UNICEF's private Earth Engine assets

## Installation

### Dependencies

```bash
# Install dependencies using uv
uv sync
```

### Google Earth Engine Authentication

1. **Create service account** in Google Cloud Console
2. **Download JSON key file**
3. **Enable Earth Engine API** for your project
4. **Grant Earth Engine access** to the service account

## Configuration

### Environment Setup

The server requires Google Earth Engine authentication via service account:

```bash
# Set service account credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Or mount as Docker secret
/run/secrets/ee_auth.json
```

### Server Configuration

**`ee_mcp/config.yaml`**:

```yaml
server:
  host: "0.0.0.0" # Server bind address
  port: 8003 # Server port
  transport: "sse" # MCP transport protocol
```

### Dataset Configuration

The server uses `hazards_metadata.yaml` for dataset definitions. Each dataset entry must include the following fields:

**Required Fields:**

- **`asset_id`** (string): Google Earth Engine asset identifier for the dataset
- **`image_filename`** (string): JSON filename for cached image data
- **`description`** (string): Human-readable description of the dataset and its purpose
- **`mosaic`** (boolean): Whether the dataset should be processed as a mosaic or single image
- **`source_name`** (string): Name of the data source organization
- **`source_url`** (string): URL to the original data source or documentation
- **`color_palette`** (array): List of hex color codes for visualization (from low to high values)

**Optional Fields:**

- **`threshold`** (number): Default threshold value for filtering or classification

**Example Configuration:**

## Available Tools

The MCP server exposes 12 specialized tools for geospatial analysis:

### 1. Dataset and Metadata Tools

#### `get_all_datasets_and_metadata()`

Returns comprehensive information about all available datasets.

**Returns**: Dictionary with dataset IDs, descriptions, sources, and visualization parameters.

#### `get_dataset_image_and_metadata(dataset_id: str)`

Retrieves a specific dataset image with its metadata.

**Parameters**:

- `dataset_id`: Identifier for the dataset (e.g., "river_flood", "agricultural_drought")

**Returns**: Earth Engine Image object with metadata.

### 2. Image Processing Tools

#### `mask_image(image_data: str, geometry_data: str)`

Applies a spatial mask to an image using a geometry.

**Parameters**:

- `image_data`: Serialized Earth Engine Image
- `geometry_data`: Serialized Earth Engine Geometry for masking

**Returns**: Masked image with only values within the geometry.

#### `filter_image_by_threshold(image_data: str, threshold: float, comparison: str)`

Filters image pixels based on value thresholds.

**Parameters**:

- `image_data`: Serialized Earth Engine Image
- `threshold`: Numeric threshold value
- `comparison`: Comparison operator ("gt", "gte", "lt", "lte", "eq")

**Returns**: Binary image with pixels meeting the threshold condition.

### 3. Binary Image Operations

#### `union_binary_images(image1_data: str, image2_data: str)`

Creates a union (OR operation) of two binary images.

**Returns**: Combined image showing areas where either input image has values.

#### `intersect_binary_images(image1_data: str, image2_data: str)`

Creates an intersection (AND operation) of two binary images.

**Returns**: Combined image showing areas where both input images have values.

### 4. Feature Collection Operations

#### `intersect_feature_collections(fc1_data: str, fc2_data: str)`

Finds spatial intersection between two feature collections.

**Parameters**:

- `fc1_data`: Serialized Earth Engine FeatureCollection
- `fc2_data`: Serialized Earth Engine FeatureCollection

**Returns**: Features that spatially intersect between the two collections.

#### `merge_feature_collections(fc1_data: str, fc2_data: str)`

Combines two feature collections into one.

**Returns**: Merged FeatureCollection containing all features from both inputs.

### 5. Spatial Analysis Tools

#### `reduce_image(image_data: str, geometry_data: str, reducer: str)`

Performs spatial reduction (statistics) over an image within a geometry.

**Parameters**:

- `image_data`: Serialized Earth Engine Image
- `geometry_data`: Serialized Earth Engine Geometry
- `reducer`: Reduction operation ("sum", "mean", "count", "max", "min")

**Returns**: Statistical result of the reduction operation.

#### `get_zone_of_area(geometry_data: str, buffer_distance: float)`

Creates a buffer zone around a geometry.

**Parameters**:

- `geometry_data`: Serialized Earth Engine Geometry
- `buffer_distance`: Buffer distance in meters

**Returns**: Buffered geometry representing the zone of area.

### 6. Visualization Tools

#### `build_map(image_data: str, geometry_data: str, vis_params: dict)`

Generates an interactive HTML map visualization.

**Parameters**:

- `image_data`: Serialized Earth Engine Image
- `geometry_data`: Serialized Earth Engine Geometry
- `vis_params`: Visualization parameters (colors, opacity, etc.)

**Returns**: HTML string containing interactive map with data layers.

## Development

### Running the Server

```bash
# Development mode
mcp dev ee_mcp/server.py

# Production mode
uv run ee_mcp/server.py
```

### Testing

```bash
# Run all tests
uv run pytest

# Run integration tests
uv run pytest tests/test_integration.py -v
```

### Development Setup

1. **Clone repository**
2. **Install dependencies**: `uv sync`
3. **Set up GEE authentication**
4. **Configure test environment**
5. **Run tests to verify setup**

## Security

- **Service Account Keys**: Securely managed via Docker secrets
- **Least Privilege**: Service account has minimal required permissions
- **Private Assets**: UNICEF datasets stored in private Earth Engine assets
- **Network Security**: Server accessible only within internal network

## Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 and use type hints
2. **Testing**: Add comprehensive tests for new tools
3. **Documentation**: Update tool descriptions and examples

### Adding New Tools

1. **Define tool** in `server.py` with `@mcp.tool()` decorator
2. **Implement handler** in `handlers.py`
3. **Add validation** schemas in `schemas.py`
4. **Write tests** in `tests/test_handlers.py`
5. **Update documentation** in README

### Dataset Integration

1. **Add metadata** to `hazards_metadata.yaml`
2. **Verify asset permissions** for Earth Engine assets
3. **Test data access** with integration tests
4. **Document data sources** and licensing

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Submit issues on GitHub repository
- **Earth Engine Support**: Google Earth Engine Help Center
- **UNICEF Data**: Contact UNICEF data team for asset access
- **Technical Support**: Repository maintainers

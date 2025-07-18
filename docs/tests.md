# Tests Documentation

## Overview

The UNICEF GEE MCP project contains comprehensive unit, integration, and functional tests for Google Earth Engine integration, image processing, and geospatial data analysis functionality.

## Test Structure

### Test Files

- **`test_schemas.py`** - Tests data schema validation and serialization
- **`test_utils.py`** - Tests utility functions for data processing
- **`test_config.py`** - Tests configuration loading and validation
- **`test_handlers.py`** - Tests handler functions for datasets and metadata
- **`test_integration.py`** - Tests integration with Earth Engine APIs and image processing
- **`conftest.py`** - Test fixtures, mocks, and shared configuration

### Test Categories

#### Unit Tests

- **Schema Tests**: Data validation, serialization/deserialization
- **Utility Tests**: Helper functions, data transformation utilities
- **Configuration Tests**: Config loading, Earth Engine authentication
- **Handler Tests**: Dataset metadata handling, file operations

#### Integration Tests

- **Earth Engine Integration**: Image processing, feature collection operations
- **Dataset Operations**: Loading datasets, applying filters and thresholds
- **Geospatial Analysis**: Zone analysis, image masking, binary operations

#### Functional Tests

- **End-to-End Workflows**: Complete data processing pipelines
- **MCP Server Functions**: Server endpoint testing with real data

## Key Test Coverage

### Core Functionality

- ✅ Earth Engine authentication and initialization
- ✅ Dataset metadata loading and validation
- ✅ Image processing and filtering operations
- ✅ Feature collection intersections and unions
- ✅ Binary image operations (union, intersection)
- ✅ Zone analysis and area calculations

### Specific Operations Tested

- **Image Operations**:
  - `filter_image_by_threshold()` - Apply thresholds to images
  - `mask_image()` - Apply masks to images
  - `reduce_image()` - Reduce images using various methods
- **Feature Collections**:
  - `intersect_feature_collections()` - Intersection operations
  - `merge_feature_collections()` - Merging operations
  - `get_zone_of_area()` - Zone extraction
- **Binary Operations**:
  - `union_binary_images()` - Union of binary images
  - `intersect_binary_images()` - Intersection of binary images

### Test Datasets

Tests use sample datasets including:

- **river_flood** - GLOFAS flood hazard data
- **agricultural_drought** - ERA5 drought indicators
- **cyclone** - Cyclone hazard data

## Running Tests

### Prerequisites

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Ensure Earth Engine authentication is set up
# Place your service account key in ee_auth.json
```

### Run All Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ee_mcp --cov-report=html

# Run specific test categories
uv run pytest tests/test_integration.py  # Integration tests only
uv run pytest tests/test_handlers.py     # Handler tests only
uv run pytest tests/test_schemas.py      # Schema tests only

# Run specific test class
uv run pytest tests/test_integration.py::TestImageOperations

# Run with verbose output
uv run pytest -v

# Run with Earth Engine mocking (for CI/CD)
uv run pytest --mock-ee
```

## Test Configuration

Tests are configured via `pyproject.toml`:

- Test path: `tests/`
- Python path includes: `[".", "ee_mcp"]`
- Coverage excludes test files and `__init__.py`

## Test Fixtures

The `conftest.py` file provides:

- **Earth Engine Mocking**: Mock EE classes for testing without authentication
- **Sample Configurations**: Test configuration data
- **Temporary Files**: Test metadata and authentication files
- **Mock Datasets**: Sample dataset definitions for testing

## Authentication Requirements

- **Service Account**: Tests require a valid Earth Engine service account key
- **Metadata Files**: Tests use sample metadata configurations
- **Mock Support**: Tests can run with mocked Earth Engine for CI/CD environments

## Notes

- Integration tests require valid Earth Engine authentication
- Some tests create temporary files that are automatically cleaned up
- Mock fixtures allow testing without real Earth Engine API calls
- Test datasets use realistic data structures but with sample/mock data

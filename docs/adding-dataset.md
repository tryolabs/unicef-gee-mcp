# Adding a new dataset to `hazards_metadata.yaml`

> This guide explains how to register a new hazard or demographic dataset so it can be discovered and used by the MCP tools and scripts.

## Where the metadata lives

- File: `ee_mcp/hazards_metadata.yaml`
- Loader: `ee_mcp/datasets.py::load_datasets_metadata`
- Model: `ee_mcp/schemas.py::DatasetMetadata`

Important: the loader automatically prefixes every `asset_id` with the base path in `ee_mcp/constants.py` (`BASE_ASSETS_PATH = "projects/unicef-ccri/assets"`). Provide only the asset suffix (e.g., `river_flood_r100`), not the full path. If you need to use assets outside this base path, update `BASE_ASSETS_PATH` appropriately first.

## Required steps

1. Open `ee_mcp/hazards_metadata.yaml`.
2. Under the top-level key `datasets:`, add a new entry using a unique dataset key.
3. Provide the required fields, and any optional fields your workflow needs.
4. Validate by loading metadata and/or running tests (see Validation below).

## Fields and what they do

Required fields:

- `asset_id` (string; suffix only)
  - The Earth Engine asset identifier suffix. The loader will build the full path as `projects/unicef-ccri/assets/{asset_id}`.
  - Examples: `river_flood_r100`, `childpop_constrained`.
- `description` (string)
  - Human-readable description of the dataset and units/meaning of values.
- `source_name` (string)
  - Source organization name (e.g., "ECMWF", "WorldPop").
- `source_url` (string)
  - Link to the source dataset or documentation.

Optional fields:

- `threshold` (number | "mean")
  - Default threshold used when converting to a binary mask.
  - Semantics in handlers: if the threshold is negative, pixels `< threshold` are kept; otherwise pixels `> threshold` are kept.
  - If set to the string `"mean"`, the loader computes the global land mean of the dataset (masking out ocean using ADM0 boundaries) and replaces it with that numeric value at load time.
- `color_palette` (list of hex strings)
  - Suggested visualization colors from low to high values. Not automatically applied by the server; clients and scripts can use it to drive map styling (e.g., `build_map`).

## Special behavior

- `agricultural_drought` dataset: when requested via handlers, an additional mask `image.lte(100)` is applied before further processing.

## Example entry

```yaml
datasets:
  air_pollution:
    asset_id: "pm25_p90_1998_2023" # suffix only; loader prefixes with BASE_ASSETS_PATH
    description: "PM2.5 90th percentile concentration (1998–2023)."
    source_name: "ACAG"
    source_url: "https://sites.wustl.edu/acag/datasets/surface-pm2-5/"
    threshold: 5 # keep pixels > 5 µg/m³
    color_palette: ["#cec0b8", "#b2a59b", "#9a9381", "#7a745d", "#6f634b"]
```

## Validation

Quick options to validate your new entry:

- Programmatic load
  - `uv run python -c "from pathlib import Path; from ee_mcp.datasets import load_datasets_metadata; print(load_datasets_metadata(Path('ee_mcp/hazards_metadata.yaml')).keys())"`
- Integration check
  - `uv run pytest tests/test_integration.py::TestMCPServerIntegration::test_get_all_datasets_and_metadata_endpoint -v`
- Smoke test via server tools (requires EE auth)
  - Use the `get_all_datasets_and_metadata` and `get_dataset_image_and_metadata` tools from the MCP server to confirm discovery and image retrieval.

## Tips & troubleshooting

- If you accidentally provide a full asset path (e.g., `projects/unicef-ccri/assets/river_flood_r100`), the loader will prefix it again, resulting in an invalid path. Fix by switching back to the suffix-only form.
- `threshold: "mean"` requires Earth Engine access and performs a global reduction; expect additional latency on first load.
- Choose `mosaic: true` only for assets that are ImageCollections; single Images should use `false`.

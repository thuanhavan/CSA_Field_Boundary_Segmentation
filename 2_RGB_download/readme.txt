# RGB and Mask Download Workflow

## Overview
- This part contains two notebooks for downloading data from Google Earth Engine (GEE):
   - `1a_rgb_download.ipynb` — downloads Sentinel-2 RGB imagery.
   - `1b_mask_download.ipynb` — builds and downloads a crop mask layer.
- Folders are generated automatically during setup; 

## Prerequisites (general setup)
- Complete environment setup following instructions in `1_Environment_setup/RGB_download/readme.txt`.
- Launch Jupyter Lab or VS Code with the correct environment (e.g., `rgb_env`).
- Sign in to Earth Engine in the notebook when prompted (`ee.Authenticate()`), then `ee.Initialize()`.

## Output locations (auto-managed)
- Output folders are resolved automatically in the notebooks and saved under:
   - `5_Data/RGB_download/<Province>` for RGB tiles
   - `5_Data/Mask_download/<Province>` for mask tiles

## Parallel downloads and billing (important)
- Single-tile (sequential) downloads are the default and work without billing.
- Parallel downloads are optional and commented out by default. If you enable them, Google may throttle or block concurrent requests unless your Earth Engine account is linked to a billing-enabled Google Cloud Project.
- If needed, enable billing in your Earth Engine settings and limit `cpus_` to a conservative value.

---

## RGB imagery download (1a_rgb_download.ipynb)
1. Open `1a_rgb_download.ipynb`.
2. Set your province code (e.g., `provName = 'AB' | 'SK' | 'MB'`). Output directories are set automatically.
3. The notebook loads the province grid and computes `grid_size`. For testing, slice a small subset of tiles.
4. Recommended: run a single-tile test cell first to verify output.
5. Download options:
    - Sequential (default, recommended without billing):
       - Use the single-tile cell or a short loop over `argument_list_config_all[0:N]` that calls `get_crp_rgb_from_asset(*argument)`.
    - Parallel (optional, requires billing):
       - Uncomment the parallel cell and set `cpus_` according to your limits. Keep values modest to avoid throttling.

Notes:
- RGB naming convention includes year and tile index; keep track of the tiles you download for matching with mask outputs.

## Mask download (1b_mask_download.ipynb)
1. Open `1b_mask_download.ipynb`.
2. Set your province code (`provName = 'AB' | 'SK' | 'MB'`). Output directories are set automatically.
3. The notebook loads the same grid and prepares `argument_list_config_all = [(out_dir, tile_id, tile_feature), ...]`.
4. Recommended: run a single-tile test (there’s a cell that unpacks one tuple and calls `get_crp_mask`).
5. Download options:
    - Sequential (default, recommended without billing):
       - Loop over a subset: `for args in argument_list_config_all[0:N]: get_crp_mask(*args)`.
    - Parallel (optional, requires billing):
       - Uncomment the parallel cell and set `cpus_`. Without billing, jobs may stall at 0%.

---

## Keep RGB and mask tiles matched
- Use the same grid and tile index ranges for both notebooks so outputs align.
- Tips to avoid mismatches:
   - Download the same slice (e.g., `[0:50]`) for RGB and mask.
   - Ensure the province and grid source are identical in both notebooks.
   - Compare counts of files produced per province and spot-check a few tile IDs.

## Troubleshooting
- Authentication issues: rerun `ee.Authenticate()` and `ee.Initialize()`.
- Empty or missing data: retry the tile; if persistent, test smaller geometry.
- Parallel downloads hang or stay at 0%: keep parallel cells commented and use sequential mode, or enable billing for your Earth Engine Cloud Project.

## Additional notes
- You may use sample data for testing without running downloads (see repository-level documentation, if provided).

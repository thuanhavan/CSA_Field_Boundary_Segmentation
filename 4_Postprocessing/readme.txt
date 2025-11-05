# Postprocessing Workflow

## Description
Part 4 performs comprehensive cleaning and refinement of the raw segmentation results from Part 3:
- **4a: Boundary Cleaning** - Cleans and intersects segmentation boundaries across multiple years
- **4b: Crop Mask Application** - Applies crop mask statistics to filter and refine field boundaries

## Prerequisites
- Complete environment setup following instructions in `1_Environment_setup/ArcGIS_SAM/readme.txt`
- Ensure you have the cloned environment activated
- **Complete Part 1 - Folder Setup:**
  - Run `1_Environment_setup/Folder_Structure/folder_setup.ipynb` to create required folder structure
- **Complete Part 2 workflow:**
  - Run `2_RGB_download/1a_rgb_download.ipynb` to download RGB images
  - Run `2_RGB_download/1b_mask_download.ipynb` to download crop masks
- **Complete Part 3 workflow:**
  - Run `3_Segmentation/3a_arcpy_rgb_segmentation_new.ipynb` to generate segmentation boundaries

## Usage Steps

### Step 1: Boundary Cleaning (4a)
1. Open ArcGIS Pro Python Command Prompt
2. Activate your cloned environment: `conda activate field-boundary-seg`
3. Set working directory: `cd C:\Your\Project\Path\4_Postprocessing`
4. Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
5. Edit `4a_arcpy_clean_shp_new.ipynb`:
   - **Select province**: Set `provName = 'SK'` (options: 'AB' for Alberta, 'SK' for Saskatchewan, 'MB' for Manitoba)
   - The notebook automatically:
     - Reads segmentation results from `5_Data/Segmentation/{Province}/`
     - Groups boundaries by base name (removes year suffixes)
     - Performs intersection across multiple years
     - Applies negative buffer and overlap removal
     - Saves cleaned boundaries to `5_Data/Postprocessing/{Province}/`
   - Adjust parameters if needed (MIN_AREA_HA, NEG_BUFFER, etc.)
   - Run the notebook

### Step 2: Crop Mask Application (4b)
1. Continue in the same Jupyter session or reopen as above
2. Edit `4b_cropmask_new.ipynb`:
   - **Select province**: Set `provName = 'SK'` (must match province from 4a)
   - The notebook automatically:
     - Reads cleaned boundaries from `5_Data/Postprocessing/{Province}/`
     - Matches each boundary with corresponding crop mask from `5_Data/Mask_download/{Province}/`
     - Calculates zonal statistics (mean crop probability per field)
     - Filters fields by minimum area (default 2.0 ha) and crop probability (default 0.4)
     - Saves final results to `5_Data/Final_Output/{Province}/`
   - Adjust filter parameters if needed (MIN_HA_DEFAULT, MIN_MEAN_DEFAULT)
   - Run the notebook

### File Structure
This workflow uses automatic folder structure organized by province:
```
5_Data/
├── Segmentation/
│   └── Saskatchewan/                           # Input from Part 3
│       ├── Boundary_rgb_SK_2021_50_1.shp
│       ├── Boundary_rgb_SK_2022_50_1.shp
│       └── ...
├── Mask_download/
│   └── Saskatchewan/                           # Input from Part 2
│       ├── crop_mask_50_1.tif
│       ├── crop_mask_51_1.tif
│       └── ...
├── Postprocessing/
│   └── Saskatchewan/                           # Output from 4a
│       ├── Boundary_rgb_SK_50_1_intersect.shp  # Grouped & cleaned boundaries
│       ├── Boundary_rgb_SK_51_1_intersect.shp
│       └── ...
└── Final_Output/
    └── Saskatchewan/                           # Output from 4b
        ├── Boundary_rgb_SK_50_1_intersect_cropland.shp  # Final filtered fields
        ├── Boundary_rgb_SK_51_1_intersect_cropland.shp
        └── ...
```

**Notes:**
- Province selection (`provName`) must be consistent across both notebooks
- All folders are created automatically by `folder_setup.ipynb` from Part 1
- 4a groups boundaries by base name, removing year suffixes (e.g., `_2021`, `_2022`)
- 4b matches boundaries with masks using tile keys extracted from filenames
- Crop mask matching: `Boundary_rgb_SK_50_1_intersect.shp` → `crop_mask_50_1.tif`

## Troubleshooting

### General Issues
- **Environment issues**: If imports fail, verify the environment was cloned correctly and ArcGIS Pro Python is activated
- **File locks**: Ensure ArcGIS Pro is closed when running scripts to avoid file lock conflicts
- **Memory issues**: Processing large provinces may require 16GB+ RAM. Consider processing smaller regions or tiles

### 4a Issues (Boundary Cleaning)
- **Missing shapefiles**: Ensure you've run `3a_arcpy_rgb_segmentation_new.ipynb` first to create boundary files
- **No files to process**: Verify the correct province is selected and segmentation outputs exist
- **Grouping issues**: The script groups files by removing year patterns (_2021, _2022, etc.). Ensure your files follow the naming convention
- **Scratch GDB errors**: The script creates temporary geodatabases. Ensure you have write permissions in the project folder

### 4b Issues (Crop Mask Application)
- **Missing mask files**: Ensure you've run `2_RGB_download/1b_mask_download.ipynb` first to download crop masks
- **Raster not found**: Verify crop mask .tif files exist in `5_Data/Mask_download/{Province}/`
- **Matching errors**: The script extracts tile keys from filenames (e.g., "50_1" from "Boundary_rgb_SK_50_1_intersect.shp"). Ensure your files follow this naming convention
- **Spatial Analyst license**: This notebook requires ArcGIS Spatial Analyst extension. Verify it's available with `arcpy.CheckOutExtension("Spatial")`

### Parameter Tuning
- **4a Parameters** (in `shp_clean_func_new.py`):
  - `MIN_AREA_HA = 0.1`: Minimum area (hectares) to keep during cleaning. Increase to filter smaller polygons
  - `NEG_BUFFER = "-0.2 Meters"`: Negative buffer to remove slivers. Increase magnitude for more aggressive cleaning
  - `POS_BUFFER = "0.4 Meters"`: Positive buffer to restore edges. Should be ~2× negative buffer
  
- **4b Parameters** (in notebook):
  - `MIN_MEAN_DEFAULT = 0.4`: Minimum crop probability (0-1). Fields below this are filtered out
  - `MIN_HA_DEFAULT = 2.0`: Minimum field area (hectares) in final output. Increase to remove small fields

## Additional Technical Notes

#################### shp_clean_func_new.py - Boundary Cleaning Functions ####################
# Purpose:
#   Batch-clean boundary shapefiles by intersecting same-area layers (e.g., by year),
#   thinning by area, counting overlaps, and buffering to remove slivers—then write
#   a final per-area shapefile. Optimized to run jobs in parallel (threads or processes).
#
# What it does (per job/group of inputs):
#   1) Intersect all input polygons (ALL attributes preserved)
#   2) MultipartToSinglepart
#   3) Add area_ha (GEODESIC)
#   4) Select polygons with area_ha >= MIN_AREA_HA (early reduction)
#   5) CountOverlappingFeatures (fewer features → faster)
#   6) Buffer inward (NEG_BUFFER) to trim edges / remove tiny slivers
#   7) Buffer outward (POS_BUFFER) to restore original footprint thickness
#   8) Save final shapefile to OUTPUT_SUBDIR
#
# How inputs are grouped:
#   - Shapefiles are grouped by basename with year tokens normalized
#     (e.g., "Boundary_AB_2021_Muni_0001.shp" and "Boundary_AB_2022_Muni_0001.shp"
#      become one job). Requires ≥ 2 layers per group to run.
#
# Key configuration knobs:
#   - MIN_AREA_HA   : minimum polygon area (hectares) after step 3
#   - NEG_BUFFER    : e.g., "-20 Meters" (inward shrink)
#   - POS_BUFFER    : e.g., "20 Meters"  (restore outward)
#   - BUFFER_METHOD : "PLANAR" (projected data; faster) or "GEODESIC"
#   - PARALLEL_PCT  : ArcGIS tool-level parallelism (e.g., "75%")
#   - MAX_WORKERS   : thread/process pool size (small values avoid GP contention)
#   - POOL_MODE     : "thread", "process", or "auto"
#
# Outputs:
#   - One shapefile per group in <INPUT_FOLDER>/<OUTPUT_SUBDIR>/ with the base name
#     cleaned of year tokens (e.g., "Boundary_AB_Muni_0001_intersect.shp").
#
# Performance & robustness:
#   - Uses a per-worker scratch file geodatabase (more stable than in_memory)
#   - Orders operations to reduce feature count before expensive steps
#   - Cleans temporary data; logs per-job success/failure
#
# Assumptions / notes:
#   - For PLANAR buffering/metrics, input data should be in an appropriate projected CRS
#   - GEODESIC area is used for area_ha (independent of buffer method)
#   - Shapefile limits apply (field name lengths, types). Consider GDB if hitting limits.
#   - Requires ArcGIS Pro with Spatial Analyst for CountOverlappingFeatures in some installs
###################################################

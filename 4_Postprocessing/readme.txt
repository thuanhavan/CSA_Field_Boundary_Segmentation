# Postprocessing Workflow

## Description
- Part 4 performs comprehensive cleaning and refinement of the raw segmentation results from Part 3
- Includes cleaning with masks, boundary processing, and filtering operations
- Uses `4a_arcpy_clean_shp.ipynb` for all postprocessing tasks

## Prerequisites
- Complete environment setup following instructions in `1_Environment_setup/ArcGIS_SAM/readme.txt`
- Ensure you have the cloned environment activated
- **Complete Part 2 workflow:**
  1. RGB Images: Ensure `segmentation_example/RGB_clip/` contains raw RGB (tif) files from GEE download (`1a_rgb_download.ipynb`), sample data, or your own RGB images
  2. Create Masks: Run `2_RGB_download/1b_rgb_mean_mask.ipynb` on the RGB images to generate processed images and masks
- **Complete Part 3 workflow:**
  1. Segmentation: Run `3a_arcpy_rgb_segmentation.ipynb`

## Usage Steps
1. Open ArcGIS Pro Python Command Prompt
2. Activate your cloned environment: `conda activate field-boundary-seg`
3. Set working directory: `cd C:\Your\Project\Path\4_Postprocessing`
4. Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
5. **Create required folders manually:**
   - Create `segmentation_example/shp_clean/` folder
   - Create `segmentation_example/tmp_to_process/` folder
6. Edit `4a_arcpy_clean_shp.ipynb`:
   - Update `input_folder` to point to segmentation results (`segmentation_example/RGB_mask/segment/`)
   - Update `mask_folder` to point to mask shapefiles (`segmentation_example/RGB_mask/shp/`)
   - Update `output_folder` and `temp_base` paths as needed
   - Run the notebook (performs all cleaning, filtering, and boundary processing)

### File Structure
This workflow uses the complete structure from Parts 2-3 and creates additional folders:
```
segmentation_example/
├── RGB_clip/                           # From Part 2: Raw RGB images
│   └── example_RGB_download.tif
├── RGB_mask/                           # Main processing folder
│   ├── rgb/                           # From Part 2: Processed RGB images
│   │   └── example_RGB_processed.tif
│   ├── shp/                           # From Part 2: Input mask shapefiles
│   │   └── example_mask.shp
│   └── segment/                       # From Part 3: Raw segmentation output
│       ├── example_boundary.shp
│       └── shp_clean/                 # Step 6: Final cleaned results (created by 4a)
│           └── example_boundary_final.shp
├── shp_clean/                         # Step 5: Create manually - Intermediate cleaned results
│   └── example_boundary_clean.shp
└── tmp_to_process/                    # Step 5: Create manually - Temporary processing files
    └── boundary_temp_folders/
```

## Troubleshooting
- **Missing mask files**: If you get "file not found" errors in `4a_arcpy_clean_shp.ipynb`, ensure you've run `2_RGB_download/1b_rgb_mean_mask.ipynb` first
- **Missing shapefiles**: Ensure you've run `3a_arcpy_rgb_segmentation.ipynb` first to create the required boundary files
- **Path errors**: Verify the `input_folder`, `mask_folder`, and `output_folder` paths match your actual data locations
- **Missing folders**: Ensure you've created `shp_clean/` and `tmp_to_process/` folders as specified in step 5
- **Environment issues**: If imports fail, verify the environment was cloned correctly and deep learning frameworks were installed before cloning
- **File locks**: Ensure ArcGIS Pro is closed when running scripts to avoid file lock conflicts

## Additional Notes


### Usage Notes
- **4a processes**: Raw segmentation output from `RGB_mask/segment/` using masks from `RGB_mask/shp/`
- Update all folder paths in the notebook to match your data location
- The notebook processes all `Boundary_*.shp` files in the input folder
- Creates intermediate output in the `shp_clean/` folder
- **Final cleaned files**: Located in `RGB_mask/segment/shp_clean/` with `_final.shp` suffix
- Temporary processing files are stored in `tmp_to_process/`



#################### shp_clean ####################
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

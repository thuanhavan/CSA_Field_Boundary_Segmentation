# Running Field Boundary Segmentation

## Description
- Part 3 uses the SAM to create a map of field borders from RGB images
- Produces raw segmentation output that will be cleaned in Part 4 

## Prerequisites
- Complete environment setup following instructions in `1_Environment_setup/ArcGIS_SAM/readme.txt`
- Download SAM.dlpk from: https://www.arcgis.com/home/item.html?id=9b67b441f29f4ce6810979f5f0667ebe
- Update the `sam_model` path in the notebook to match your SAM.dlpk location
- **Complete Part 2 workflow:**
  1. RGB Images: Ensure `segmentation_example/RGB_clip/` contains raw RGB (tif) files from GEE download (`1a_rgb_download.ipynb`), sample data, or your own RGB images
  2. Create Masks: Run `2_RGB_download/1b_rgb_mean_mask.ipynb` on the RGB images to generate processed images and masks

## Usage Steps
1. Open ArcGIS Pro Python Command Prompt
2. Activate your cloned environment: `conda activate field-boundary-seg`
3. Set working directory: `cd C:\Your\Project\Path\3_Segmentation`
4. Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
5. Edit `3a_arcpy_rgb_segmentation.ipynb`:
   - Update path to SAM model (SAM.dlpk file)
   - Update input path to RGB images folder (`segmentation_example/RGB_mask/rgb/`)
   - Update output path for segmentation results (`segmentation_example/RGB_mask/segment/`)
   - Run the notebook

### File Structure
This workflow uses the structure from Part 2 and creates segmentation outputs:
```
segmentation_example/
├── RGB_clip/                   # From Part 2: Raw downloaded images  
│   └── example_RGB_download.tif
└── RGB_mask/
    ├── rgb/                    # From Part 2: Input RGB images (referenced in Step 5)
    │   └── example_RGB_processed.tif
    ├── shp/                    # From Part 2: Input mask shapefiles (for Part 4)
    │   └── example_mask.shp
    └── segment/                # Step 5: Created by 3a_arcpy_rgb_segmentation.ipynb (set via output_folder)
        └── example_boundary.shp
```

## Troubleshooting
- **Image holes/gaps**: If you encounter holes in processed images, redownload the missing areas from your data source
- **Brightness variations**: Satellite imagery may have different brightness levels where images are stitched together. This can cause segmentation problems in those areas and may require brightness normalization
- **Memory issues**: Ensure you have sufficient VRAM (8GB+ recommended) 
- **Environment issues**: If imports fail, verify the environment was cloned correctly and deep learning frameworks were installed before cloning
- **File locks**: Ensure ArcGIS Pro is closed when running scripts to avoid file lock conflicts
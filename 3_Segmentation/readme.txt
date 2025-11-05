# Running Field Boundary Segmentation

## Description
- Part 3 uses the SAM (Segment Anything Model) to create a map of field borders from RGB images
- Produces raw segmentation output that will be cleaned in Part 4 

## Prerequisites
- Complete environment setup following instructions in `1_Environment_setup/ArcGIS_SAM/readme.txt`
- Download SAM.dlpk from: https://www.arcgis.com/home/item.html?id=9b67b441f29f4ce6810979f5f0667ebe
- Place SAM.dlpk in `5_Data/Models/` folder
- **Complete Part 1 - Folder Setup:**
  - Run `1_Environment_setup/Folder_Structure/folder_setup.ipynb` to create required folder structure
- **Complete Part 2 workflow:**
  - Run `2_RGB_download/1a_rgb_download.ipynb` to download RGB images from Google Earth Engine

## Usage Steps
1. Open ArcGIS Pro Python Command Prompt
2. Activate your cloned environment: `conda activate field-boundary-seg`
3. Set working directory: `cd C:\Your\Project\Path\3_Segmentation`
4. Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
5. Edit `3a_arcpy_rgb_segmentation_new.ipynb`:
   - **Select province**: Set `provName = 'SK'` (options: 'AB' for Alberta, 'SK' for Saskatchewan, 'MB' for Manitoba)
   - The notebook automatically:
     - Reads RGB images from `5_Data/RGB_download/{Province}/`
     - Loads SAM model from `5_Data/Models/SAM.dlpk`
     - Saves segmentation results to `5_Data/Segmentation/{Province}/`
   - Run the notebook

### File Structure
This workflow uses automatic folder structure organized by province:
```
5_Data/
├── Models/
│   └── SAM.dlpk                        # SAM model (download and place here)
├── RGB_download/
│   ├── Alberta/                        # RGB images for Alberta
│   ├── Saskatchewan/                   # RGB images for Saskatchewan
│   │   ├── rgb_SK_2021_50_1.tif
│   │   ├── rgb_SK_2022_50_1.tif
│   │   └── ...
│   └── Manitoba/                       # RGB images for Manitoba
└── Segmentation/
    ├── Alberta/                        # Segmentation output for Alberta
    ├── Saskatchewan/                   # Segmentation output for Saskatchewan
    │   ├── Boundary_rgb_SK_2021_50_1.shp
    │   ├── Boundary_rgb_SK_2022_50_1.shp
    │   └── ...
    └── Manitoba/                       # Segmentation output for Manitoba
```

**Notes:**
- Province selection in the notebook (`provName = 'SK'`) automatically determines input/output folders
- All folders are created automatically by `folder_setup.ipynb` from Part 1
- Segmentation outputs are named `Boundary_{filename}.shp` based on input RGB filenames

## Troubleshooting
- **Image holes/gaps**: If you encounter holes in processed images, redownload the missing areas from your data source
- **Brightness variations**: Satellite imagery may have different brightness levels where images are stitched together. This can cause segmentation problems in those areas and may require brightness normalization
- **Memory issues**: Ensure you have sufficient VRAM (8GB+ recommended) 
- **Environment issues**: If imports fail, verify the environment was cloned correctly and deep learning frameworks were installed before cloning
- **File locks**: Ensure ArcGIS Pro is closed when running scripts to avoid file lock conflicts
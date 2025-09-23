# RGB Download Workflow

## Description
- Part 2 downloads Sentinel-2 RGB imagery using Google Earth Engine for segmentation
- Establishes the project file structure used by subsequent parts

## Prerequisites
- Complete environment setup following instructions in `1_Environment_setup/RGB_download/readme.txt`
- Ensure you have the RGB environment activated (e.g., `rgb_env`)
- Google Earth Engine account with authentication

## Usage Steps
1. Open Anaconda Prompt or Terminal
2. Activate your RGB environment: `conda activate rgb_env`
3. Set working directory: `cd C:\Your\Project\Path\2_RGB_download`
4. **Create base folder**: Create a `segmentation_example/` folder in your project directory to manage all data
5. **Create data folders**: Create `segmentation_example/RGB_clip/` and `segmentation_example/RGB_mask/` folders
6. Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
7. Edit `1a_rgb_download.ipynb`:
   - Set `prov`, `provName`, and `asset_path` variables for your target province
   - Adjust `grid_size` (small for testing, full province size for production)
   - Update `out_dir` for output location (uses the `segmentation_example/RGB_clip/` folder)
   - Run the notebook
   - **Alternative**: Skip this step and use sample data (see Additional Notes section)
   - **Custom data**: You can also place your own RGB images directly in the `RGB_clip/` folder


## Troubleshooting
- **Authentication error**: Run `ee.Authenticate()` again and follow the link to paste the token
- **Missing package**: Ensure your environment is activated and run `conda list` to check installed packages
- **Empty tiles**: Some downloaded tiles may be empty or contain missing data - redownload individually or use smaller grid
- **Missing data sections**: Downloaded tiles may contain sections of missing data - redownload individually or as a group by removing bad tiles from output and running download again
- **Persistent missing data**: If redownloaded tiles still have missing data, make a smaller grid over the missing area and download smaller images
- **Segmentation failures**: If multiple years do not have identical shape and bands, segmentation will fail

## Additional Notes

### Using Sample Data (Alternative to Step 7)
Instead of downloading imagery with Google Earth Engine, you can use the sample data provided:

1. **Create folder structure**: Manually create `segmentation_example/RGB_clip/` folder in your project directory (if not already done in Step 5)
2. **Copy sample files**: Copy the `.tif` files from `6. Data/` folder into the `RGB_clip/` folder
3. **Skip step 7**: Skip the `1a_rgb_download.ipynb` step entirely

**Note**: This approach uses pre-downloaded sample data instead of downloading new imagery, making it ideal for testing the workflow without needing Google Earth Engine authentication.

### Customization Tips
- **Change years**: Edit the `yrList` variable
- **Change output location**: Edit the `out_dir` variable
- **Parallelization**: Adjust `cpus_` for number of parallel downloads
- **Redownload specific tiles**: Modify `grid_size` and tile indices
- **Whole province**: Set `grid_size = list_roi_all.size().getInfo()`

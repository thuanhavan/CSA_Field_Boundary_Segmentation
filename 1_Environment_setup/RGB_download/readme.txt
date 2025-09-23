# RGB Download Environment Setup

## Description
- Sets up Python environment for downloading Sentinel-2 RGB imagery using Google Earth Engine
- Creates conda environment with all required packages for the RGB download workflow in part 2_RGB_download
- Environment can also be used to run the Accuracy assessment in part 5_Acccuracy_assessment 

## Prerequisites
- Anaconda or Miniconda installed (https://docs.conda.io/)
- Anaconda/Miniconda must be installed in user folder or run with admin permission
- Internet access for downloading packages
- Google Earth Engine account (https://signup.earthengine.google.com/)

## Setup Steps
1. Open Anaconda Prompt (Windows: Start → search "Anaconda Prompt")
2. Navigate to project folder: `cd C:\Your\Project\Path\1_Environment_setup\RGB_download`
3. Create environment: `conda env create -f environment.yml`
4. Activate environment: `conda activate rgb-environment`
5. Launch Jupyter: `jupyter lab` or use VS Code with correct environment

## Troubleshooting
- **Authentication error**: Run `ee.Authenticate()` and follow the link to paste token
- **Missing package**: Ensure environment is activated and run `conda list` to check installed packages
- **Permission errors**: Ensure Anaconda is installed in user folder or run with admin permission
- **Environment creation fails**: Check internet connection and try again


## Additional Notes

### VS Code Setup
If using VS Code with Jupyter extension:
1. Navigate to project root: `cd C:\Your\Project\Path\CSA_Field_Boundary_Segmentation`
2. Open VS Code: `code .`
3. Set notebook environment to your new environment (e.g., 'rgb_env')


# ArcGIS SAM Environment Setup

## Description
- Sets up ArcGIS Pro environment for field boundary segmentation using SAM deep learning model
- Requires cloning existing ArcGIS Pro environment with deep learning library installed

## Prerequisites
- ArcGIS Pro 3.3+ installed and licensed
- Administrator access for deep learning frameworks installation
- Internet access for downloading model and frameworks
- **CRITICAL**: Install deep learning frameworks BEFORE cloning the environment
- GPU recommended (Can run on CPU but will be significantly slower) consult https://github.com/Esri/deep-learning-frameworks for hardware requirements

## Setup Steps

1. Install ArcGIS Pro 3.3+
2. Install Esri Deep Learning Frameworks from: https://github.com/Esri/deep-learning-frameworks
3. Open ArcGIS Pro Python Command Prompt (Start > ArcGIS > Python Command Prompt)
4. Clone environment: `conda create --name field-boundary-seg --clone arcgispro-py3`
5. Activate environment: `conda activate field-boundary-seg`
6. Configure Jupyter/VS Code to use the `field-boundary-seg` environment
7. Download SAM model from: https://www.arcgis.com/home/item.html?id=9b67b441f29f4ce6810979f5f0667ebe
8. Save the `SAM.dlpk` file to a known location and update the `sam_model` path in '3a_arcpy_rgb_segmentation.ipynb'


## Troubleshooting
- **Import errors**: Verify environment was cloned correctly and deep learning frameworks installed before cloning
- **Missing SAM model**: Download SAM.dlpk file and update path in segmentation notebook
- **Environment issues**: Ensure ArcGIS Pro is properly licensed and activated
- **File locks**: Close ArcGIS Pro before environment operations to avoid conflicts
- Ensure ArcGIS Pro is closed when creating/modifying environments

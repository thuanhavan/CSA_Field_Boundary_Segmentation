# Automated Field Boundary Extraction Using Sentinel-2 and Segment Anything Model (SAM)

## Overview
<img width="919" alt="image" src="https://github.com/user-attachments/assets/9e82a83b-53c8-450a-a290-50123089f34c" />

Field boundary extraction is a critical task in precision agriculture (PA), enabling site-specific management practices that optimize the use of resources such as land, water, fertilizer, and pesticides. Traditional methods, including manual delineation from high-resolution imagery or semi-automated delineation via farm machinery, are labor-intensive and challenging to scale over large spatial and temporal extents.

This project presents an automated workflow for large-scale field boundary segmentation using the pre-trained Segment Anything Model (SAM) integrated with customized time-series Sentinel-2 satellite imagery. By leveraging Red, Green, and Blue (RGB) bands collected at different phenological stages, the approach enables accurate segmentation of field borders across extensive agricultural regions.

Our case study demonstrates the application over 22 million hectares of Canadian prairies, achieving an Intersection-over-Union (IoU) accuracy of 0.95 (R²). The repository documents the complete workflow including environment setup, data preprocessing, segmentation, post-processing, and accuracy assessment.

![image](https://github.com/user-attachments/assets/f7fcb1d7-ea2e-46d3-8147-3a69981da2e2)

## Features

- Seasonal satellite image collection and preprocessing using **Google Earth Engine** via Python API.
- Large-scale, automatic field boundary segmentation powered by the **Segment Anything Model (SAM)**.
- Post-segmentation feature cleaning compatible with GIS platforms (e.g., ArcGIS Pro).
- Scalable workflow applicable to varying crop types and phenological stages.

## Repository Contents



- **1_Environment_setup/**: Instructions and configuration files for setting up the computational environment.
- **2_RGB_download/**: Scripts for acquiring and preparing Sentinel-2 imagery.
- **3_Segmentation/**: Code integrating SAM for field boundary segmentation.
- **4_Postprocessing/**: Tools and instructions for cleaning segmentation results.
- **5_Accuracy_assessment/**: Data and code for accuracy assessment.
  
## Getting Started

1. Clone the repository.
2. Follow environment setup instructions to install dependencies.
3. Use the preprocessing scripts to acquire and prepare your imagery.
4. Run the segmentation pipeline with SAM on your prepared data.
5. Perform post-processing and cleaning as needed.
6. Evaluate results using the provided accuracy assessment scripts.

## Requirements

- Python 3.8+
- Google Earth Engine Python API
- Enable billing for your GEE Cloud Project (for parallel downloading only)
- PyTorch (for running SAM)
- GIS software (ArcGIS Pro recommended for cleaning)
- Additional dependencies listed in `requirements.txt`


## Citation

If you use this workflow in your research or projects, please cite:

> [Insert your publication or DOI here once published]

## Contact

For questions or contributions, please open an issue or contact the maintainer at [thuan.ha@usask.ca].

---

This project advances precision agriculture by enabling scalable and automated field boundary extraction, supporting better resource management and sustainability.

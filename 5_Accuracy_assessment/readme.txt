
# Accuracy Assessment Workflow

## Description
- Part 5 performs accuracy assessment using Intersection over Union (IoU) calculation between reference and predicted field boundary shapefiles
- Evaluates the performance of the field boundary segmentation results from previous workflow steps
- Generates individual IoU results for each test area and overall summary statistics

## Prerequisites
- Complete environment setup with geopandas package installed
- Ensure you have a Python environment activated (e.g., `rgb_env` or notebook kernel with geopandas)
- **Complete Parts 2-4 workflow:** Have segmentation results available for comparison
- **Test data:** Use provided accuracy assessment data from `6. Data/Accuracy assessment/` folder

## Usage Steps
1. **Prepare test data:**
   - Extract/unzip the accuracy assessment folder from `6. Data/Accuracy assessment.zip`
   - Ensure the folder structure contains reference boundary shapefiles and predicted boundary shapefiles
2. **Set up environment:**
   - Open Anaconda Prompt, Terminal, or VS Code
   - Activate your environment with geopandas support
3. **Configure analysis:**
   - Set working directory: `cd C:\Your\Project\Path\5_Accuracy_assessment`
   - Launch Jupyter: `jupyter lab` or use VS Code with the correct environment
4. **Edit `accuracy_assessment.ipynb`:**
   - Update `root_dir` to point to your target province data folder
   - Example: `"C:\Users\spn733\Work\CSA_Segmentation\CSA_Field_Boundary_Segmentation\6. Data\Accuracy assessment\SK"`
   - Available provinces: AB (Alberta), MB (Manitoba), SK (Saskatchewan)
5. **Run the notebook:**
   - Execute all cells to calculate IoU for each test area
   - Results will be saved to individual `iou_result.txt` files and a combined CSV summary

### File Structure
The accuracy assessment uses the following data structure:
```
6. Data/Accuracy assessment/
├── AB/                                    # Alberta test data
│   ├── iou_summary_ab.csv                # Provincial summary results
│   ├── Box_0/                           # Individual test areas
│   │   ├── boundary_clipped.shp         # Reference shapefile
│   │   ├── AB_*_clipped.shp            # Predicted shapefile
│   │   └── iou_result.txt              # Individual IoU result
│   └── Box_1, Box_2, Box_3.../         # Additional test areas
├── MB/                                   # Manitoba test data (similar structure)
└── SK/                                   # Saskatchewan test data (similar structure)
```

## Output
- **Individual results:** `iou_result.txt` files in each test folder containing IoU score, intersection area, union area, and CRS information
- **Summary CSV:** `iou_summary_[province].csv` with combined results for all test areas
- **Console output:** Progress updates and final mean IoU statistics

## Troubleshooting
- **Missing geopandas**: Install using `conda install geopandas` or `pip install geopandas`
- **CRS projection errors**: The script automatically calculates appropriate UTM zones for accurate area calculations
- **Missing shapefiles**: Ensure each test folder contains both reference (`boundary_clipped.shp`) and predicted shapefiles
- **Invalid geometry**: The script includes geometry validation and will skip invalid areas with error messages
- **Memory issues**: For large datasets, consider processing provinces separately or reducing the number of test areas
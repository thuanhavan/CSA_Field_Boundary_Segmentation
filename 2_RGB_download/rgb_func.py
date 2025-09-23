import time
from pathlib import Path
import os, glob, ee, time
from tqdm import tqdm
from multiprocessing import Pool
import ee


##################

# combine s2 and cloudless s2 collection
# s2 cloud cover filter parameters
CLOUD_FILTER = 5#20
CLD_PRB_THRESH = 5
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 1
BUFFER = 1


##################

def get_s2_sr_cld_col(aoi, start_date, end_date):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.calendarRange(5,10, 'month'))
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))


##################

def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))
# Define a function to add the s2cloudless probability layer and derived cloud mask as bands to an S2 SR image input.

##################

def add_cloud_bands(img):
    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))


##################

def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cld_shdw)


##################


def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)


##################


def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)


##################

# Make an image out of the 'val' attribute
def reduceToImage(featureCollection):
    return featureCollection\
        .filter(ee.Filter.notNull(['val']))\
        .reduceToImage(properties=['val'], reducer=ee.Reducer.first())


##################

# Create a buffer around road features and set 'val' attribute to 1
def bufferAndSetVal(feature):
    return feature.buffer(5).set('val', 1)

##################

def get_aafc_crop_mask(roi):
    """
    Generates a smoothed AAFC crop mask from the AAFC Crop Inventory.
    
    Parameters:
    - roi: ee.Geometry or ee.Feature to clip the output.
    - start_date: start of date filter (default '2015-01-01')
    - end_date: end of date filter (default '2024-12-31')
    
    Returns:
    - ee.Image: Smoothed binary crop mask image.
    """
    # time range
    start_date='2015-01-01'
    end_date='2024-12-31'
    
    # Load AAFC Crop Inventory collection
    crop = ee.ImageCollection('AAFC/ACI').filterDate(start_date, end_date)

    # Define remapping lists
    oldVal = [10, 20, 30, 34, 35, 50, 80, 110, 120, 122, 130, 131, 132, 133, 134, 135, 136, 137,
              138, 139, 140, 141, 142, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156,
              157, 158, 160, 162, 167, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 185, 188,
              189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 210, 220, 230]

    newVal = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 132, 133, 134, 135, 136, 137,
              138, 139, 140, 141, 142, 145, 146, 147, 148, 149, 150, 151, 152, 153,
              154, 155, 156, 157, 158, 160, 162, 167, 174, 1, 1, 1, 1, 1, 1, 1, 1, 1,
              1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    # Define image mapping function
    def map_crop_mask(img):
        mask = img.remap(oldVal, newVal, 0, 'landcover').rename('landcover').toUint32()
        cropMask = mask.gt(1).clip(roi)
        return cropMask

    # Apply remapping and processing
    aafcMask = crop.map(map_crop_mask).sum().focal_mean(radius=3).rename('aafcMask').divide(10)
    return aafcMask.clip(roi)


##################

# Define the combined function
def processCroplandMask(roi,roadMask):
    # Index calculation function
    def index(img):
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndwi = img.normalizedDifference(['B8', 'B11']).rename('ndwi')
        return img.addBands(ndvi).addBands(ndwi) \
            .copyProperties(img, ['system:time_start'])
    
    # Cropland filter function
    def croplandFilter(img):
        minArea = 50000
        maxSize = 200
        filter = img.focal_mean(2, 'square', 'pixels', 1).gt(0.5)
        pixelCount = filter.connectedPixelCount(maxSize)
        minPixelCount = ee.Image(minArea).divide(ee.Image.pixelArea())
        imgFiltered = filter.updateMask(pixelCount.gte(minPixelCount)).unmask()
        return imgFiltered
    
    # S2 collection
    s2 = ee.ImageCollection("COPERNICUS/S2") \
        .filterBounds(roi) \
        .filterDate('2022-04-01', '2023-10-15') \
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 5)) \
        .filter(ee.Filter.calendarRange(4, 9, 'month')) \
        .map(lambda img: img.clip(roi))
    
    # Extract indices
    NDVImax = s2.map(index).filter(ee.Filter.calendarRange(4, 9, 'month')).select('ndvi').max()
    NDVImedian = s2.map(index).filter(ee.Filter.calendarRange(4, 6, 'month')).select('ndvi').median()
    NDVIdiff = NDVImax.subtract(NDVImedian)
    NDWImin = s2.map(index).select('ndwi').min()
    
    # Non-crop index calculation
    nonCrop= NDVIdiff.subtract(NDWImin)
    testaafc = get_aafc_crop_mask(roi)
  
    croplandMask = nonCrop.multiply(testaafc).add(nonCrop).multiply(roadMask) #croplandFilter(nonCrop).clip(roi)
  
    return croplandMask.unmask(0.1)#filteredNonCroplandMask



##################

def get_s2(roi, year, mask,
           s2_collection='COPERNICUS/S2_SR_HARMONIZED',
           csplus_collection='GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED',
           qa_band='cs_cdf',
           clear_threshold=0.55):
    
    # Load collections
    s2 = ee.ImageCollection(s2_collection)
    csPlus = ee.ImageCollection(csplus_collection)

    # Define join function
    def join_cloudscore(s2_col, cs_col):
        join = ee.Join.saveFirst('csplus')
        filter = ee.Filter.equals(leftField='system:index', rightField='system:index')
        return ee.ImageCollection(join.apply(s2_col, cs_col, filter))

    # Define cloud masking function
    def apply_cloud_mask(image):
        cs_img = ee.Image(image.get('csplus')).select(qa_band)
        return image.updateMask(cs_img.gte(clear_threshold))

    # Filter collections
    s2_filtered = s2.filterBounds(roi).filterDate(f'{year}-04-01', f'{year}-10-01')
    cs_filtered = csPlus.filterBounds(roi).filterDate(f'{year}-04-01', f'{year}-10-01')

    # Join and apply cloud mask
    joined = join_cloudscore(s2_filtered, cs_filtered)
    collection = joined.map(apply_cloud_mask)

    # Extract and scale RGB bands
    B4 = (collection.filter(ee.Filter.calendarRange(8, 10, 'month'))
          .select('B4').median().unitScale(100, 3000).multiply(255).toByte().unmask(1).rename('B4'))
    

    B3 = (collection.filter(ee.Filter.calendarRange(6, 8, 'month'))
          .select('B3').median().unitScale(200, 2300).multiply(255).toByte().unmask(1).rename('B3'))

    B2 = (collection.filter(ee.Filter.calendarRange(4, 7, 'month'))
          .select('B2').median().unitScale(150, 1350).multiply(255).toByte().unmask(1).rename('B2'))


    # Combine and mask
    rgb = B4.addBands(B3).addBands(B2)
    rgb_3m = rgb.multiply(mask).toByte().unmask(1).clip(roi)

    return rgb_3m


##################

def parallelize_download(func, argument_list, num_processes):
 
    pool = Pool(processes=num_processes)
 
    jobs = [pool.apply_async(func=func, args=(*argument,)) 
            if isinstance(argument, tuple) 
            else pool.apply_async(func=func, args=(argument,)) 
            for argument in argument_list]
    pool.close()
    result_list_tqdm = []
    for job in tqdm(jobs):
        result_list_tqdm.append(job.get())
        # Add a wait of 1 second
        time.sleep(180)
 
    return result_list_tqdm


def get_raster_from_asset(download_outpath, grid_id, crop_mask, grid_shp):
        
    import ee, os
    ee.Initialize()
    import geemap.geemap as geemap
    from pathlib import Path
    
    # Set output file names
    output_tif = download_outpath + 'grid_' + str(grid_id) + '_1.tif'
    
    # if output csv file exist, skip
    if os.path.exists(output_tif):
        print("Precipitation exists for file ",
              str(Path(output_tif).stem), ", skipping now ...")
    else:
        img = ee.Image(crop_mask).clip(grid_shp)
        geemap.download_ee_image(
            img, output_tif, crs = "EPSG:4326", scale = 10) 





def get_crp_mask_from_asset(download_dir, tile_id, asset_path, tile):
    
    import ee, os
    ee.Initialize()
    import geemap.geemap as geemap
    from pathlib import Path
    
    # Set output file names
    output_tif = str(download_dir) + '/crop_mask_' + str(tile_id) + '_1.tif'
    
    # if output csv file exist, skip
    if os.path.exists(output_tif):
        
        print("Crop mask exists for file ",
              str(Path(output_tif).stem), ", skipping now ...")
        
    else:
        
        # List assets and extract their names
        asset_list = ee.data.listAssets(asset_path)['assets']
        asset_names = list(map(lambda d: d['name'], asset_list))
        
        # Create a list of images from asset names
        list_img = list(map(lambda f: ee.Image(f), asset_names))
        
        # Create an image collection from the list of images and mosaic them
        crop_mask_raster = ee.ImageCollection.fromImages(list_img).mosaic().select([0])
        crop_mask_raster = crop_mask_raster.clip(tile)
        crop_mask_raster = crop_mask_raster.rename('crop_mask')

        geemap.download_ee_image_tiles(
            crop_mask_raster, ee.FeatureCollection(ee.Feature(tile)),
            str(download_dir), prefix = 'crop_mask_' +  str(tile_id) + '_',
            crs = "EPSG:4326", scale = 10)

# ########################### Download Crop Mask RGB


def get_crp_rgb_from_asset(yrList, download_dir, provName, local_idx, asset_path, selectProv, tile_shp):
    
    for yr in yrList:

        import ee, os
        ee.Initialize()
        import geemap.geemap as geemap
        from pathlib import Path
        
        # Set output file names
        output_tif = str(download_dir) + '/rgb_' + provName + '_' + str(yr) + '_' + str(local_idx) + '_1.tif'
        
        # if output csv file exist, skip
        if os.path.exists(output_tif):
            
            print("Crop RGB exists for file ",
                  str(Path(output_tif).stem), ", skipping now ...")
            
        else:

            # Road mask
            road_skshp = ee.FeatureCollection(asset_path).filterBounds(selectProv)
            mask = ee.Image.constant(1).clip(selectProv)
            roadSK = road_skshp.map(bufferAndSetVal)
            roadImg = reduceToImage(roadSK)
            roadMask = mask.multiply(roadImg.add(0.3)).mask(0.1).Not().clip(selectProv)

            # Filter for required year
            start_date =  str(yr) +'-05-15'
            end_date = str(yr)+'-10-15'
            year = str(yr)

            geo = ee.Feature(tile_shp).geometry()

            # MASK from NDVI and ESA
            mask = processCroplandMask(geo, roadMask)# using crop and road
            rgb_3m = get_s2(geo, yr, mask)

            geemap.download_ee_image_tiles(
                rgb_3m, ee.FeatureCollection(ee.Feature(tile_shp)), str(download_dir),
                prefix = 'rgb_' + provName + '_' + str(yr) + '_' + str(local_idx) + '_',
                crs = "EPSG:4326", scale = 10)
            time.sleep(100)



# def compute_otsu(gray_arr):
#     """Return Otsu threshold for 8-bit grayscale numpy array."""
#     hist, bins = np.histogram(gray_arr.flatten(), bins=256, range=(0,256))
#     centers    = (bins[:-1] + bins[1:]) / 2
#     total      = hist.sum()
#     sum_total  = (centers * hist).sum()
#     weight_b = sum_b = max_bt = 0.0
#     thresh   = centers[0]
    
#     for i in range(256):
#         weight_b += hist[i]
#         if weight_b == 0:
#             continue
#         weight_f = total - weight_b
#         if weight_f == 0:
#             break
#         sum_b += centers[i] * hist[i]
#         m_b   = sum_b / weight_b
#         m_f   = (sum_total - sum_b) / weight_f
#         bt    = weight_b * weight_f * (m_b - m_f)**2
#         if bt > max_bt:
#             max_bt, thresh = bt, centers[i]
#     return thresh


# def mask_and_apply(rgb_path, out_dir, minSize):
#     """Create a continuous‐patch mask from RGB and apply it to the RGB."""
#     # 1) Load RGB
#     ras     = arcpy.Raster(rgb_path)
#     arr     = arcpy.RasterToNumPyArray(ras)
#     arr8    = np.clip(arr, 0, 255).astype(np.uint8)
#     gray    = (0.2989*arr8[0] + 0.5870*arr8[1] + 0.1140*arr8[2]).astype(np.uint8)
    
#     # 2) Otsu threshold → binary mask
#     thr     = compute_otsu(gray)
#     print(f"{os.path.basename(rgb_path)} → Otsu = {thr:.1f}")
#     mask1   = (gray >= thr).astype(np.uint8)
    
#     # 3) Grayscale → Raster
#     ll      = arcpy.Point(ras.extent.XMin, ras.extent.YMin)
#     cs      = ras.meanCellWidth
#     mask_r  = arcpy.NumPyArrayToRaster(mask1, ll, cs, cs, value_to_nodata=0)
    
#     # 4) Smooth (5×5 mean) + re-threshold → clean mask
#     mean5   = FocalStatistics(mask_r, NbrRectangle(5,5,"CELL"), "MEAN")
#     smooth  = Con(mean5 >= 0.5, 1)  # false → NoData
    
#     # 5) RegionGroup + Lookup → size raster
#     rg      = RegionGroup(smooth, "EIGHT", "WITHIN", "ADD_LINK", "0")
#     sizes   = Lookup(rg, "COUNT")
    
#     # 6) Continuous mask only (>= minSize pixels)
#     cont_m  = Con(sizes >= minSize, 1)
    
#     # 7) Apply mask to original RGB
#     masked  = ExtractByMask(rgb_path, cont_m)
    
#     # 8) Save result
#     base    = os.path.splitext(os.path.basename(rgb_path))[0]
#     out_tif = os.path.join(out_dir, f"{base}_masked.tif")
#     masked.save(out_tif)
#     print(f"  → Saved: {out_tif}")
    
#     # 9) Clean up in_memory
#     for obj in (mask_r, mean5, smooth, rg, sizes, cont_m):
#         try:
#             arcpy.Delete_management(obj)
#         except:
#             pass












# ## ----------------- MASK FUNCTIONS ------------------#
# import os

# import numpy as np
# import rasterio
# from rasterio.features import shapes
# import geopandas as gpd

# def extract_year(filename):
#     """
#     Extracts a 4‐digit year from filenames like 'rgb_SK_2021_200_1.tif'.
#     Returns the year string (e.g. '2021') or None if not found.
#     """
#     m = re.search(r'_(\d{4})(?=_|\.)', filename)
#     return m.group(1) if m else None

# def strip_year_from_basename(filename):
#     import re
#     """
#     Removes exactly one "_<4‐digit year>" from the end of the base name.
#     E.g. "rgb_SK_2021_200_1.tif" → "rgb_SK_200_1"
#     """
#     name = os.path.splitext(filename)[0]
#     # return re.sub(r'_(\d{4})(?!.*_\d{4})', '', name)
#     return re.sub(r'_(?:19|20)\d{2}(?=_)', '', name, count=1)



# def otsu_threshold(grayscale_array):
#     """
#     Applies Otsu's method to a 2D array (dtype=float, values in [0..255]).
#     Returns the optimal threshold in [0..255]. Zeros and negatives are ignored.
#     """
#     flat = grayscale_array.flatten()
#     flat = flat[flat > 0]
#     if flat.size == 0:
#         return 0

#     hist, _ = np.histogram(flat, bins=256, range=(0, 255))
#     total = flat.size
#     sum_total = np.dot(np.arange(256), hist)

#     sumB = 0.0
#     wB = 0.0
#     max_between = 0.0
#     threshold = 0

#     for i in range(256):
#         wB += hist[i]
#         if wB == 0:
#             continue
#         wF = total - wB
#         if wF == 0:
#             break

#         sumB += i * hist[i]
#         mB = sumB / wB
#         sumF = sum_total - sumB
#         mF = sumF / wF

#         between_var = wB * wF * (mB - mF) ** 2
#         if between_var > max_between:
#             max_between = between_var
#             threshold = i

#     return threshold

# def compute_mean_with_otsu_and_shapefile(raster_paths, output_basename):
#     """
#     Given a list of aligned 3‐band, 8‐bit unsigned GeoTIFFs (`raster_paths`),
#     this function produces:
#       1. A 3‐band "mean_with_otsu" GeoTIFF, where each pixel is the mean only
#          over those pixels that exceeded each image’s Otsu threshold.
#       2. A polygon shapefile of regions where the Otsu mask (computed on the
#          “no_otsu” grayscale composite) is 255.

#     Outputs go into two subdirectories under the parent of `output_basename`:
#       - “rgb/”: contains `{name_no_ext}_with_otsu.tif`
#       - “shp/”: contains `{name_no_ext}_mask.shp`

#     Returns:
#       (with_otsu_fp, mask_shp_fp) – full filepaths to the outputs.
#     """
#     import rasterio
#     if len(raster_paths) == 0:
#         raise ValueError("`raster_paths` is empty.")

#     # 1) Open the first raster to grab metadata, dims, transform, etc.
#     with rasterio.open(raster_paths[0]) as src0:
#         profile = src0.profile.copy()
#         bands = src0.count
#         height = src0.height
#         width = src0.width
#         transform = src0.transform
#         crs = src0.crs

#         if bands != 3 or src0.dtypes[0] != 'uint8':
#             raise RuntimeError(
#                 f"Expected 3‐band uint8 imagery, but first file has {bands} bands of type {src0.dtypes[0]}"
#             )

#         # Prepare accumulators for "with_otsu" mean
#         sum_with_otsu = np.zeros((3, height, width), dtype=np.float64)
#         count_with_otsu = np.zeros((3, height, width), dtype=np.uint32)

#         # Prepare accumulators for computing temporary "no_otsu" grayscale composite
#         sum_no_otsu_gray = np.zeros((height, width), dtype=np.float64)
#         count_no_otsu_gray = np.zeros((height, width), dtype=np.uint32)

#     # 2) Loop over each raster to build accumulators
#     for idx, fp in enumerate(sorted(raster_paths), start=1):
#         with rasterio.open(fp) as src:
#             if src.count != bands or src.height != height or src.width != width:
#                 raise RuntimeError(
#                     f"Raster {os.path.basename(fp)} has different dimensions/bands than the first one."
#                 )

#             data = src.read(masked=True).astype(np.float32)  # shape = (3, H, W)

#             # Compute grayscale for this image (masked‐to‐zero)
#             R = data[0].filled(0)
#             G = data[1].filled(0)
#             B = data[2].filled(0)
#             gray = 0.2989 * R + 0.5870 * G + 0.1140 * B

#             # Accumulate for temporary "no_otsu" grayscale composite
#             valid_gray = (~data[0].mask) & (~data[1].mask) & (~data[2].mask)
#             sum_no_otsu_gray[valid_gray] += gray[valid_gray]
#             count_no_otsu_gray[valid_gray] += 1

#             # Compute this image’s Otsu threshold on its grayscale
#             thr = otsu_threshold(gray)
#             print(f"  [{idx}/{len(raster_paths)}] {os.path.basename(fp)} → Otsu = {thr:.1f}")

#             # Create mask for this image: pixel > thr AND unmasked
#             combined_mask = (gray > thr) & valid_gray

#             # Accumulate sums/counts for pixels that passed Otsu
#             for b in range(3):
#                 band_arr = data[b].filled(0).astype(np.float64)
#                 sum_with_otsu[b][combined_mask] += band_arr[combined_mask]
#                 count_with_otsu[b][combined_mask] += 1

#     # 3) Compute the “with_otsu” mean (3 bands, uint8)
#     mean_with_otsu = np.zeros((3, height, width), dtype=np.uint8)
#     for b in range(3):
#         with np.errstate(divide='ignore', invalid='ignore'):
#             valid = count_with_otsu[b] > 0
#             band_float = sum_with_otsu[b]
#             mean_with_otsu[b][valid] = np.round(band_float[valid] / count_with_otsu[b][valid]).astype(np.uint8)

#     # 4) Compute temporary "no_otsu" grayscale composite
#     mean_no_otsu_gray = np.zeros((height, width), dtype=np.uint8)
#     with np.errstate(divide='ignore', invalid='ignore'):
#         valid_gray = count_no_otsu_gray > 0
#         gray_float = sum_no_otsu_gray
#         mean_no_otsu_gray[valid_gray] = np.round(gray_float[valid_gray] / count_no_otsu_gray[valid_gray]).astype(np.uint8)

#     # 5) Compute Otsu mask on the "no_otsu" grayscale composite
#     thr_mean = otsu_threshold(mean_no_otsu_gray.astype(np.float32))

#     # Build final binary mask array: 255 where mean_no_otsu_gray > thr_mean
#     mask_on_mean = np.zeros((height, width), dtype=np.uint8)
#     mask_on_mean[mean_no_otsu_gray > thr_mean] = 255

#     # 6) Derive output directories and filenames
#     parent_dir = os.path.dirname(output_basename)
#     name_no_ext = os.path.splitext(os.path.basename(output_basename))[0]

#     rgb_dir = os.path.join(parent_dir, "rgb")
#     shp_dir = os.path.join(parent_dir, "shp")
#     os.makedirs(rgb_dir, exist_ok=True)
#     os.makedirs(shp_dir, exist_ok=True)

#     with_otsu_fp = os.path.join(rgb_dir, f"{name_no_ext}_with_otsu.tif")
#     mask_shp_fp = os.path.join(shp_dir, f"{name_no_ext}_mask.shp")

#     # 7) Write out the “with_otsu” 3‐band TIFF into rgb_dir
#     profile_with_otsu = profile.copy()
#     profile_with_otsu.update({
#         'dtype': 'uint8',
#         'count': 3,
#         'nodata': 0,
#         'compress': 'lzw'
#     })
#     with rasterio.open(with_otsu_fp, 'w', **profile_with_otsu) as dst:
#         dst.write(mean_with_otsu)

#     print(f"→ Wrote TIFF: {os.path.relpath(with_otsu_fp, parent_dir)}")

#     # 8) Convert `mask_on_mean` array to polygons and write shapefile into shp_dir
#     # Delete existing shapefile files if present
#     if os.path.exists(mask_shp_fp):
#         base = os.path.splitext(mask_shp_fp)[0]
#         for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
#             fp = base + ext
#             if os.path.exists(fp):
#                 os.remove(fp)

#     # Extract polygons where mask == 255
#     shapes_list = []
#     for geom, value in shapes(mask_on_mean, mask=(mask_on_mean == 255), transform=transform):
#         if int(value) == 255:
#             shapes_list.append({
#                 "geometry": geom,
#                 "properties": {"value": int(value)}
#             })

#     # Build GeoDataFrame
#     if len(shapes_list) == 0:
#         gdf = gpd.GeoDataFrame({"value": []}, geometry=[], crs=crs)
#     else:
#         gdf = gpd.GeoDataFrame.from_features(shapes_list, crs=crs)

#     # Write out shapefile into shp_dir
#     gdf.to_file(mask_shp_fp, driver="ESRI Shapefile")
#     print(f"→ Wrote shapefile: {os.path.relpath(mask_shp_fp, parent_dir)}")

#     return with_otsu_fp, mask_shp_fp






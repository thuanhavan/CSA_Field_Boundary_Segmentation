# FUNCTION TO CLEARN
import arcpy
import os
import math
import shutil

# # 0) skip processed fiels
import os
import shutil
import arcpy

# ————————————————————————————————
# ArcPy environment: let each tool use up to 80% of your cores
arcpy.CheckOutExtension("ImageAnalyst")
arcpy.env.parallelProcessingFactor = "80%"
arcpy.env.overwriteOutput = True

# ————————————————————————————————
def copy_shapefile_set(src_folder, dst_folder, basename):
    """Copy .shp/.shx/.dbf/.prj/.cpg for a given basename."""
    for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
        src = os.path.join(src_folder, basename + ext)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst_folder, basename + ext))

def full_shapefile_exists(folder, basename):
    """Return True if .shp, .shx and .dbf all exist for basename in folder."""
    for ext in ['.shp', '.shx', '.dbf']:
        if not os.path.exists(os.path.join(folder, basename + ext)):
            return False
    return True

def get_unprocessed_files(input_folder, output_folder):
    """Return list of (infile, base_in, base_out) for files needing work."""
    to_process = []
    for infile in os.listdir(input_folder):
        if not infile.lower().endswith('.shp'):
            continue
        base = infile[:-4]  # strip .shp
        # strip "_with_otsu" if present, then add "_clean"
        if base.endswith('_with_otsu'):
            out_base = base[:-10] + '_clean'
        else:
            out_base = base + '_clean'
        if full_shapefile_exists(output_folder, out_base):
            print(f"⚠ Skipping {infile}: {out_base} already in output.")
        else:
            print(f"✅ Queued {infile} → will produce {out_base}.shp")
            to_process.append((infile, base, out_base))
    return to_process

def process_single_file(infile, base_in, base_out, input_folder, output_folder, mask_folder, temp_base):
    temp_dir = os.path.join(temp_base, base_in)
    os.makedirs(temp_dir, exist_ok=True)
    # clear old temp files
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))

    copy_shapefile_set(input_folder, temp_dir, base_in)

    # ← your existing function; unchanged
    process_field_boundaries(
        input_folder=temp_dir,
        output_folder=output_folder,
        mask_folder=mask_folder,
        min_area_sqm=50000,
        compactness_threshold=0.3
    )

    print(f"✅ Done {infile} → {base_out}.shp")
    
    
# function to process a file --------------
def get_suitable_projected_sr(shp_file):
    desc = arcpy.Describe(shp_file)
    sr   = desc.spatialReference
    if sr.type == "Projected":
        return sr
    ext  = desc.extent
    lon  = (ext.XMin + ext.XMax) / 2.0
    lat  = (ext.YMin + ext.YMax) / 2.0
    zone = int((lon + 180)/6) + 1
    epsg = (32600 if lat>=0 else 32700) + zone
    print(f"Auto‐selected UTM zone {zone} (EPSG:{epsg})")
    return arcpy.SpatialReference(epsg)


def add_area_cmp(fc):
    """Adds fields Area (m²) and cmpness (compactness)."""
    # ensure fields
    existing = [f.name for f in arcpy.ListFields(fc)]
    if "Area" not in existing:
        arcpy.AddField_management(fc, "Area", "DOUBLE")
    if "cmpness" not in existing:
        arcpy.AddField_management(fc, "cmpness", "DOUBLE")
    # compute
    with arcpy.da.UpdateCursor(fc, ["SHAPE@", "Area", "cmpness"]) as cur:
        for geom, a, c in cur:
            if geom:
                area = geom.area
                peri = geom.length
                comp = (4 * math.pi * area) / (peri * peri) if peri > 0 else 0
            else:
                area, comp = 0, 0
            cur.updateRow([geom, area, comp])

        
def get_suitable_projected_sr(shp_file):
    desc = arcpy.Describe(shp_file)
    sr   = desc.spatialReference
    if sr.type == "Projected":
        return sr
    ext  = desc.extent
    lon  = (ext.XMin + ext.XMax) / 2.0
    lat  = (ext.YMin + ext.YMax) / 2.0
    zone = int((lon + 180)/6) + 1
    epsg = (32600 if lat>=0 else 32700) + zone
    print(f"Auto‐selected UTM zone {zone} (EPSG:{epsg})")
    return arcpy.SpatialReference(epsg)

def add_area_cmp(fc):
    """Adds fields Area (m²) and cmpness (compactness)."""
    # ensure fields
    existing = [f.name for f in arcpy.ListFields(fc)]
    if "Area" not in existing:
        arcpy.AddField_management(fc, "Area", "DOUBLE")
    if "cmpness" not in existing:
        arcpy.AddField_management(fc, "cmpness", "DOUBLE")
    # compute
    with arcpy.da.UpdateCursor(fc, ["SHAPE@", "Area", "cmpness"]) as cur:
        for geom, a, c in cur:
            if geom:
                area = geom.area
                peri = geom.length
                comp = (4 * math.pi * area) / (peri * peri) if peri > 0 else 0
            else:
                area, comp = 0, 0
            cur.updateRow([geom, area, comp])

def process_field_boundaries(input_folder, output_folder, mask_folder,
                             min_area_sqm=50000, compactness_threshold=0.3):
    """
    1) Project  
    2) Count overlaps  
    3) Multipart→single  
    4) Buffer −20m  
    5) Filter by Area & cmpness  
    6) Buffer +20m → final_fc  
    7) INTERSECT with mask_folder\{base}_mask.shp → temp_intersect  
    8) SELECT from final_fc where INTERSECT → base.shp  
    """
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = input_folder
    os.makedirs(output_folder, exist_ok=True)
    
    

    fcs = arcpy.ListFeatureClasses("*.shp")
    if not fcs:
        print("No shapefiles found."); return

    proj_sr = get_suitable_projected_sr(os.path.join(input_folder, fcs[0]))

    for shp in fcs:
        name     = os.path.splitext(shp)[0]
        # strip off “_with_otsu” or any other suffix if needed:
        base     = name.rsplit("_with_otsu", 1)[0]      
        
        src      = os.path.join(input_folder, shp)
        proj_fc  = os.path.join(output_folder, base + "_temp_proj.shp")

        print(f"\n▶ Processing {shp} → base='{base}'")

        # 1) Project
        arcpy.Project_management(src, proj_fc, proj_sr)

        # 2) Count overlaps
        ovl_fc = os.path.join(output_folder, base + "_temp_ovl.shp")
        arcpy.analysis.CountOverlappingFeatures(proj_fc, ovl_fc, "0", None)
        
        
        # 3) Multipart → singlepart
        sp_fc = os.path.join(output_folder, base + "_temp_single.shp")
        arcpy.management.MultipartToSinglepart(ovl_fc, sp_fc)

        # 4) Buffer −20m
        er_fc = os.path.join(output_folder, base + "_temp_erode.shp")
        arcpy.Buffer_analysis(sp_fc, er_fc, "-20 Meters", line_side="FULL",
                              line_end_type="ROUND", dissolve_option="NONE")

        # 5) Area & compactness + filter
        add_area_cmp(er_fc)
        filt_fc = os.path.join(output_folder, base + "_temp_filt.shp")
        where = f"Area >= {min_area_sqm} AND cmpness >= {compactness_threshold}"
        arcpy.Select_analysis(er_fc, filt_fc, where)
        if int(arcpy.GetCount_management(filt_fc)[0]) == 0:
            print("  ✖ no parts pass area/compactness; skipping.")
            for tmp in (proj_fc, ovl_fc, sp_fc, er_fc, filt_fc):
                if arcpy.Exists(tmp): arcpy.Delete_management(tmp)
            continue

        # 6) Buffer +20m → final_fc
        final_temp = os.path.join(output_folder, base + "_temp_final.shp")
        arcpy.Buffer_analysis(filt_fc, final_temp, "20 Meters", line_side="FULL",
                              line_end_type="ROUND", dissolve_option="NONE",
                              method="GEODESIC")
        

        # ——————————————————————————————————————————————————
        # 7) Intersect with mask
        # ——————————————————————————————————————————————————
        # derive mask name by stripping "Boundary_" prefix if present
        if base.startswith("Boundary_"):
            mask_base = base[len("Boundary_"):]
        else:
            mask_base = base

        mask_fc = os.path.join(mask_folder, f"{mask_base}_mask_final.shp")
        if not arcpy.Exists(mask_fc):
            print(f"  ✖ Mask not found: {mask_fc}. Copying unmasked final.")
            out_fc = os.path.join(output_folder, base + ".shp")
            arcpy.CopyFeatures_management(final_temp, out_fc)
        else:
            # intersect final_temp with the mask
            temp_int = os.path.join(output_folder, f"{base}_temp_intersect.shp")
            arcpy.Intersect_analysis(
                in_features=[final_temp, mask_fc],
                out_feature_class=temp_int,
                join_attributes="ALL",
                output_type="INPUT"
            )
            # select from final_temp those features that intersect the mask
            lyr = "lyr_final"
            arcpy.MakeFeatureLayer_management(final_temp, lyr)
            arcpy.SelectLayerByLocation_management(
                in_layer=lyr,
                overlap_type="INTERSECT",
                select_features=temp_int,
                selection_type="NEW_SELECTION"
            )
            out_fc = os.path.join(output_folder, f"{base}.shp")

            arcpy.CopyFeatures_management(lyr, out_fc)
            arcpy.Delete_management(lyr)
            arcpy.Delete_management(temp_int)

        print(f"  ✔ saved masked final: {out_fc}")
        
 

        # ——————————————————————————————————————————————————
        # 8) Symmetric Difference, shrink, filter by area, and append
        # ——————————————————————————————————————————————————

        # a) compute the symmetric difference between out_fc and the mask
        diff_fc = os.path.join(output_folder, f"{base}_diff.shp")
        arcpy.analysis.SymDiff(
            in_features=out_fc,
            update_features=mask_fc,
            out_feature_class=diff_fc,
            join_attributes="ALL"
        )

        # b) shrink each diff polygon by 20 m
        diff_eroded = os.path.join(output_folder, f"{base}_diff_erode.shp")
        arcpy.Buffer_analysis(
            in_features=diff_fc,
            out_feature_class=diff_eroded,
            buffer_distance_or_field="-20 Meters",
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE"
        )

        # c) explode multipart into singlepart
        diff_eroded_sp = os.path.join(output_folder, f"{base}_diff_erode_sp.shp")
        arcpy.management.MultipartToSinglepart(diff_eroded, diff_eroded_sp)
        # arcpy.management.MultipartToSinglepart(diff_fc, diff_eroded_sp)

        # d) compute area on the eroded singlepart result
        arcpy.AddField_management(diff_eroded_sp, "Area_sqm", "DOUBLE")
        arcpy.CalculateField_management(
            in_table=diff_eroded_sp,
            field="Area_sqm",
            expression="!SHAPE.area@SQUAREMETERS!",
            expression_type="PYTHON3"
        )

        # e) select only those parts large enough (>= 300000 m²)
                # e) select only those eroded parts large enough (>= 300000 m²)
        sel_diff = os.path.join(output_folder, f"{base}_diff_sel.shp")
        area_field = arcpy.AddFieldDelimiters(diff_eroded_sp, "Area_sqm")
        where_diff = f"{area_field} >= 300000"

        # make a layer for the diff features
        lyr_diff = "lyr_diff"
        arcpy.MakeFeatureLayer_management(diff_eroded_sp, lyr_diff)

        # e1) attribute select: area ≥ threshold
        arcpy.SelectLayerByAttribute_management(
            lyr_diff, "NEW_SELECTION", where_diff
        )

        # 2e) spatial filter: remove any that still intersect the main output
        arcpy.SelectLayerByLocation_management(
            in_layer=lyr_diff,
            overlap_type="INTERSECT",
            select_features=out_fc,
            selection_type="REMOVE_FROM_SELECTION"
        )
        

        # 3) write out the remaining large, non‐overlapping diff parts
        # arcpy.CopyFeatures_management(diff_buf, sel_diff)

        # 3) write out the remaining large, non‐overlapping diff parts
        arcpy.CopyFeatures_management(lyr_diff, sel_diff)
        # buffer the selected diff parts by 20 m ?????
        diff_buf = os.path.join(output_folder, f"{base}_diff_buf.shp")
        arcpy.Buffer_analysis(
            in_features=lyr_diff,
            out_feature_class=diff_buf,
            buffer_distance_or_field="20 Meters",
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE"
        )
        
               
        # f) merge the selected large parts back into the main output
        merged_fc = os.path.join(output_folder, f"{base}_clean.shp")
        arcpy.management.Merge(
            # inputs=[out_fc, sel_diff],
            inputs=[out_fc, diff_buf],
            output=merged_fc
        )

        # # g) final intersect with the mask
        # final_shp = os.path.join(output_mask, f"{base}_final_mask.shp")
        # arcpy.Intersect_analysis(
        #     in_features=[merged_fc, mask_fc],
        #     out_feature_class=final_shp,
        #     join_attributes="ALL",
        #     output_type="INPUT")

        # g) cleanup intermediate diff files
        for tmp in (proj_fc, ovl_fc, sp_fc, er_fc, filt_fc,diff_fc,final_temp,final_temp,diff_buf, diff_eroded, diff_eroded_sp,lyr_diff,out_fc,sel_diff):
            arcpy.Delete_management(tmp)
        print(f"  ✔ appended eroded diff parts ≥ 300000 m² into {out_fc}")

    print(f"\n✅ All done – outputs in {output_folder}")
    
    
    
    
    
#3. -------------- accuracy assessment 
import arcpy
import os

def compute_iou_arcpy(predicted_fc, reference_fc):
    """
    Compute Intersection over Union (IoU) between two polygon feature classes.
    
    Arguments:
        predicted_fc -- path to predicted boundaries shapefile
        reference_fc -- path to reference boundaries shapefile
    
    Returns:
        IoU value (float)
    """
    # Use in-memory workspace for speed
    intersect_fc = "in_memory\\intersect"
    union_fc = "in_memory\\union"

    try:
        # Perform intersection
        arcpy.Intersect_analysis([predicted_fc, reference_fc], intersect_fc)
        arcpy.AddField_management(intersect_fc, "Inter_Area", "DOUBLE")
        arcpy.CalculateGeometryAttributes_management(intersect_fc, [["Inter_Area", "AREA"]])

        # Perform union
        arcpy.Union_analysis([predicted_fc, reference_fc], union_fc)
        arcpy.AddField_management(union_fc, "Union_Area", "DOUBLE")
        arcpy.CalculateGeometryAttributes_management(union_fc, [["Union_Area", "AREA"]])

        # Sum total intersection area
        inter_area = sum(row[0] for row in arcpy.da.SearchCursor(intersect_fc, ["Inter_Area"]))

        # Sum total union area
        union_area = sum(row[0] for row in arcpy.da.SearchCursor(union_fc, ["Union_Area"]))

        iou = inter_area / union_area if union_area > 0 else 0

    except Exception as e:
        print(f"Error: {e}")
        iou = None

    finally:
        # Clean up memory
        arcpy.Delete_management(intersect_fc)
        arcpy.Delete_management(union_fc)

    return iou
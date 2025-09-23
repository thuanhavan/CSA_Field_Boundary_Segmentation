import os, glob, re, time
import arcpy
from pathlib import Path
from typing import List

####################################  BOUNDARY CLEANNING FUNCTIONS ####################################
# --- Grouping helpers (strip year tokens like _2021_ or trailing _2021) ---
YEAR_TOKEN = re.compile(r'_(?:19|20)\d{2}(?=_)|_(?:19|20)\d{2}$')
def _group_key_without_year(stem: str) -> str:
    return YEAR_TOKEN.sub('_', stem)

def _clean_stem_for_output(stem: str) -> str:
    s = re.sub(r'[^A-Za-z0-9_]+', '_', stem)
    s = re.sub(r'__+', '_', s)
    return s.strip('_')

def _extract_year(stem: str):
    m = re.search(r'_(\d{4})(?:_|$)', stem)
    try:
        y = int(m.group(1)) if m else None
        return y if (y and 1900 <= y <= 2099) else None
    except Exception:
        return None

# --- Discovery helpers ---
def _list_shapefiles(root: str, recursive: bool = False):
    root = os.path.abspath(root)
    if not recursive:
        return sorted(
            os.path.join(root, f)
            for f in os.listdir(root)
            if f.lower().endswith(".shp")
        )
    shp_list = []
    for d, _, files in os.walk(root):
        shp_list.extend(
            os.path.join(d, f) for f in files if f.lower().endswith(".shp")
        )
    return sorted(shp_list)

def _is_valid_output(out_fc: str) -> bool:
    try:
        if not arcpy.Exists(out_fc):
            return False
        n = int(arcpy.management.GetCount(out_fc)[0])
        return n > 0
    except Exception:
        return False

def get_unprocessed_jobs(input_folder: str, output_folder: str, recursive: bool = False):
    files = _list_shapefiles(input_folder, recursive=recursive)
    if not files:
        print("No shapefiles found in the specified folder.")
        return []
    groups = {}
    for p in files:
        stem = Path(p).stem
        key  = _group_key_without_year(stem)  # group by name with year removed
        groups.setdefault(key, []).append(p)

    jobs = []
    for key, flist in groups.items():
        stems = [Path(f).stem for f in flist]

        # ✅ Remove year from base stem so outputs never include year
        base_stem_no_year = _group_key_without_year(stems[0])
        base_stem = _clean_stem_for_output(base_stem_no_year)

        out_name  = f"{base_stem}_intersect.shp"
        base_out  = os.path.join(output_folder, out_name)

        # Keep year-aware sort for deterministic processing order
        flist_sorted = sorted(
            flist, key=lambda p: ((_extract_year(Path(p).stem) or 0), Path(p).stem)
        )

        jobs.append((flist_sorted, base_stem, base_out))

    print(f"Discovered {len(jobs)} job(s).")
    return jobs


# --- One scratch GDB for the whole run ---
def init_scratch_gdb(prefer_dir=None):
    parent = prefer_dir or arcpy.env.scratchFolder or os.getenv("TEMP") or os.getcwd()
    parent = os.path.abspath(parent)
    os.makedirs(parent, exist_ok=True)
    scratch_root = os.path.join(parent, "scratch_arcpy")
    os.makedirs(scratch_root, exist_ok=True)
    tag = time.strftime("run_%Y%m%d_%H%M%S")
    gdb_path = os.path.join(scratch_root, f"{tag}.gdb")
    if not arcpy.Exists(gdb_path):
        arcpy.management.CreateFileGDB(scratch_root, f"{tag}.gdb")
    arcpy.env.workspace = gdb_path
    arcpy.env.scratchWorkspace = gdb_path
    arcpy.env.overwriteOutput = True
    return gdb_path

# --- Cache inputs in FGDB (speeds up Merge/Buffer) ---
def _cache_inputs_in_fgdb(infiles, cache_gdb, group_tag):
    cached = []
    for i, shp in enumerate(infiles, 1):
        name = _clean_stem_for_output(Path(shp).stem)
        out_fc = os.path.join(cache_gdb, f"{group_tag}_{i:02d}_{name}")
        if not arcpy.Exists(out_fc):
            arcpy.management.CopyFeatures(shp, out_fc)
            try:
                arcpy.management.RepairGeometry(out_fc)
            except Exception:
                pass
            try:
                arcpy.management.AddSpatialIndex(out_fc)
            except Exception:
                pass
        cached.append(out_fc)
    return cached

# --- FAST processor (no overwrite) ---
def process_file_fast(infiles, base_in: str, base_out: str):
    if not infiles:
        print(f"   Skipping {base_in}: no inputs")
        return
    if arcpy.Exists(base_out):
        try:
            n = int(arcpy.management.GetCount(base_out)[0])
        except Exception:
            n = 0
        if n > 0:
            print(f"✓ Already processed: {base_out} ({n} features)")
            return
        else:
            print(f"⚠️ Output exists but is empty: {base_out} (skipping, no overwrite)")
            return

    ws = arcpy.env.workspace
    cache_root = os.path.join(os.path.dirname(ws), "cache_inputs.gdb")
    if not arcpy.Exists(cache_root):
        arcpy.management.CreateFileGDB(os.path.dirname(ws), "cache_inputs.gdb")

    group_tag = _clean_stem_for_output(base_in)
    cached = _cache_inputs_in_fgdb(infiles, cache_root, group_tag)

    def tmp(name: str) -> str: return arcpy.CreateUniqueName(name, ws)
    tmp_merge  = tmp("merged")
    tmp_ovl    = tmp("ovl")
    tmp_bufneg = tmp("bufneg")
    tmp_sel    = tmp("sel")
    tmp_bufpos = tmp("bufpos")

    print(f"→ Processing {base_in} ({len(infiles)} layers) …")
    try:
        arcpy.management.Merge(cached, tmp_merge)
        arcpy.analysis.CountOverlappingFeatures(tmp_merge, tmp_ovl, 1, None)
        arcpy.analysis.PairwiseBuffer(tmp_ovl, tmp_bufneg, NEG_BUFFER, dissolve_option="NONE", method=BUFFER_METHOD)
        if "area_ha" not in [f.name for f in arcpy.ListFields(tmp_bufneg)]:
            arcpy.management.AddField(tmp_bufneg, "area_ha", "DOUBLE")
        arcpy.management.CalculateGeometryAttributes(tmp_bufneg, [["area_ha", "AREA_GEODESIC"]], area_unit="HECTARES")
        where = f'"area_ha" >= {float(MIN_AREA_HA)}'
        arcpy.analysis.Select(tmp_bufneg, tmp_sel, where)
        arcpy.analysis.PairwiseBuffer(tmp_sel, tmp_bufpos, POS_BUFFER, dissolve_option="NONE", method=BUFFER_METHOD)
        os.makedirs(os.path.dirname(base_out), exist_ok=True)
        arcpy.management.CopyFeatures(tmp_bufpos, base_out)
        print(f"   Wrote: {base_out}")

    finally:
        for fc in (tmp_merge, tmp_ovl, tmp_bufneg, tmp_sel, tmp_bufpos):
            try:
                if arcpy.Exists(fc):
                    arcpy.management.Delete(fc)
            except Exception:
                pass

# --- Runner ---
def _run_sequential(jobs):
    processed = skipped = warnings = 0
    for infiles, base_stem, base_out in jobs:
        try:
            if arcpy.Exists(base_out) and _is_valid_output(base_out):
                print(f"✓ Already processed: {base_out}")
                skipped += 1
                continue
            process_file_fast(infiles, base_stem, base_out)
            if arcpy.Exists(base_out) and _is_valid_output(base_out):
                processed += 1
            else:
                warnings += 1
        except Exception as e:
            warnings += 1
            print(f"⚠️ Error processing {base_stem}: {e}")
    print(f"\nSummary → processed: {processed}, skipped(existing): {skipped}, warnings/errors: {warnings}")








####################################  CROP MASK FUNCTIONS ####################################

# Preferred parent folder for scratch GDBs; set to None to auto-pick
SCRATCH_PARENT = r"C:\_arc_scratch"  

# If SCRATCH_PARENT is set, ensure it exists
def init_scratch_gdb(prefer_dir=None):
    import uuid
    # 1) Choose a short, safe parent
    parent_candidates = [
        prefer_dir,
        SCRATCH_PARENT,
        arcpy.env.scratchFolder,
        os.getenv("TEMP"),
        os.getcwd(),
        r"C:\Temp",
        r"C:\_arc_scratch"
    ]
    parent = next(p for p in parent_candidates if p)  # first non-None
    parent = os.path.abspath(parent)
    os.makedirs(parent, exist_ok=True)

    # 2) Stable subfolder to avoid clutter
    scratch_root = os.path.join(parent, "scratch_arcpy")
    os.makedirs(scratch_root, exist_ok=True)

    # 3) Build a short, unique name; avoid dots in out_name
    ts   = time.strftime("%Y%m%d_%H%M%S")
    stem = f"run_{ts}_{uuid.uuid4().hex[:6]}"

    # Some systems choke if out_name ends with .gdb in CreateFileGDB; pass name *without* extension
    out_name  = stem          # no ".gdb" here
    gdb_path  = os.path.join(scratch_root, out_name + ".gdb")

    # 4) If a previous half-made GDB exists, remove it
    if arcpy.Exists(gdb_path) and os.path.isdir(gdb_path):
        try:
            # try deleting leftovers to avoid SystemCatalog lock issues
            arcpy.management.Delete(gdb_path)
        except Exception:
            pass

    # 5) Try to create; if it fails, retry with a shorter name & fallback
    def _try_create(path_parent, name):
        try:
            return arcpy.management.CreateFileGDB(path_parent, name).getOutput(0)
        except Exception as e:
            return None

    created = _try_create(scratch_root, out_name)
    if not created:
        # Retry with an ultra-short name
        short_name = "g" + uuid.uuid4().hex[:8]
        created = _try_create(scratch_root, short_name)

    if not created:
        # Final fallback: use the app's built-in scratchGDB
        if arcpy.env.scratchGDB and arcpy.Exists(arcpy.env.scratchGDB):
            arcpy.env.workspace        = arcpy.env.scratchGDB
            arcpy.env.scratchWorkspace = arcpy.env.scratchGDB
            print(f"⚠️  Falling back to env scratchGDB: {arcpy.env.scratchGDB}")
            return arcpy.env.scratchGDB
        else:
            raise RuntimeError("Failed to create a scratch file geodatabase and no env scratchGDB is available.")

    gdb_path = created  # full path returned by tool
    arcpy.env.workspace        = gdb_path
    arcpy.env.scratchWorkspace = gdb_path


    # Helpful diagnostics
    try:
        plen = len(gdb_path)
        if plen > 200:
            print(f"⚠️  Scratch GDB path is long ({plen} chars). Consider setting SCRATCH_PARENT to a shorter path.")
    except Exception:
        pass

    return gdb_path


# -----------------------------
# HELPERS
# -----------------------------
def _extract_key_from_shp(stem: str) -> str:
    m = re.match(r"^Boundary_[A-Za-z]{2}_(.+?)_\d+_intersect$", stem, re.IGNORECASE)
    if m:
        return m.group(1)
    parts = stem.split("_")
    return parts[2] if len(parts) >= 3 else stem

def _find_rasters_for_key(key: str) -> List[str]:
    pat1 = os.path.join(RASTER_FOLDER, f"Mask_{key}_*.tif")
    hits = glob.glob(pat1, recursive=RECURSIVE)
    if hits:
        return hits
    pat2 = os.path.join(RASTER_FOLDER, f"*{key}*.tif")
    hits = glob.glob(pat2, recursive=RECURSIVE)
    if hits:
        return hits
    if len(key) > 3:
        pat3 = os.path.join(RASTER_FOLDER, f"*{key[1:]}*.tif")
        hits = glob.glob(pat3, recursive=RECURSIVE)
    return hits or []

def _pick_best_raster(paths: List[str]) -> str:
    if len(paths) == 1:
        return paths[0]
    return max(paths, key=lambda p: os.path.getmtime(p))

# -----------------------------
# MAIN PROCESSING FUNCTION
# -----------------------------
def process_one(in_fc, raster_path, out_folder, scratch_gdb, min_mean=None, min_ha=None):
    """
    - Ensures ZONE_FIELD exists on input polygons.
    - ZonalStatisticsAsTable -> join MEAN -> copy to MEAN_FIELD.
    - Buffer 20 m -> CountOverlappingFeatures (ovl_fc).
    - Compute AREA_HA on ovl_fc (not on pre-buffer layer).
    - Select polygons by AREA_HA > min_ha AND MEAN_FIELD IS NOT NULL AND MEAN_FIELD > min_mean.
    - Keep only MEAN_FIELD & AREA_HA (+ required/OID/Geometry).
    """
    base = os.path.splitext(os.path.basename(in_fc))[0]
    out_sel = os.path.join(out_folder, f"{base}_cropland.shp")

    if arcpy.Exists(out_sel) and not OVERWRITE_OUT:
        print(f"SKIP: {out_sel}")
        return out_sel

    # ---- 0) Ensure zone field exists
    zone_field = ZONE_FIELD
    in_fields_upper = {f.name.upper(): f.name for f in arcpy.ListFields(in_fc)}
    if zone_field.upper() not in in_fields_upper:
        oid_name = arcpy.Describe(in_fc).OIDFieldName
        arcpy.management.AddField(in_fc, zone_field, "LONG")
        arcpy.management.CalculateField(in_fc, zone_field, f"!{oid_name}!", "PYTHON3")

    # ---- 1) Zonal stats table (MEAN)
    tmp_tbl = os.path.join(scratch_gdb, f"{arcpy.ValidateTableName(base + '_zstat', scratch_gdb)}")
    if arcpy.Exists(tmp_tbl):
        arcpy.management.Delete(tmp_tbl)

    arcpy.sa.ZonalStatisticsAsTable(
        in_zone_data=in_fc,
        zone_field=zone_field,
        in_value_raster=raster_path,
        out_table=tmp_tbl,
        ignore_nodata=IGNORE_NODATA,
        statistics_type="MEAN"
    )

    # ---- 2) Copy source polygons to scratch & add MEAN_FIELD
    out_fc = os.path.join(scratch_gdb, f"{arcpy.ValidateTableName(base + '_stats', scratch_gdb)}")
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)
    arcpy.management.CopyFeatures(in_fc, out_fc)

    # Add final MEAN_FIELD if missing
    out_fields_upper = {f.name.upper(): f.name for f in arcpy.ListFields(out_fc)}
    if MEAN_FIELD.upper() not in out_fields_upper:
        arcpy.management.AddField(out_fc, MEAN_FIELD, "DOUBLE")

    # Join the MEAN from tmp_tbl, then copy into MEAN_FIELD
    arcpy.management.JoinField(out_fc, zone_field, tmp_tbl, zone_field, ["MEAN"])
    arcpy.management.CalculateField(out_fc, MEAN_FIELD, "float(!MEAN!) if !MEAN! is not None else None", "PYTHON3")
    # Clean up the temporary MEAN field (from join) if present
    try:
        arcpy.management.DeleteField(out_fc, ["MEAN"])
    except Exception:
        pass

    # ---- 3) Buffer + Count overlaps
    buf_fc = os.path.join(scratch_gdb, f"{arcpy.ValidateTableName(base + '_buf20m', scratch_gdb)}")
    ovl_fc = os.path.join(scratch_gdb, f"{arcpy.ValidateTableName(base + '_overlap', scratch_gdb)}")
    for t in (buf_fc, ovl_fc):
        if arcpy.Exists(t):
            arcpy.management.Delete(t)

    try:
        arcpy.analysis.Buffer(out_fc, buf_fc, "20 Meters", "FULL", "ROUND", "NONE", None, "PLANAR")
        arcpy.analysis.CountOverlappingFeatures(buf_fc, ovl_fc)
    except Exception as _e:
        # Overlaps are optional for the selection; continue even if this fails.
        pass

    # ---- 4) Ensure AREA_HA exists on out_fc (this layer retains mean_val)
    out_fields_upper = {f.name.upper(): f.name for f in arcpy.ListFields(out_fc)}
    if "AREA_HA" not in out_fields_upper:
        arcpy.management.AddField(out_fc, "AREA_HA", "DOUBLE")
    arcpy.management.CalculateGeometryAttributes(
        out_fc, [["AREA_HA", "AREA_GEODESIC"]], area_unit="HECTARES"
    )

    # ---- 5) Build WHERE clause against out_fc (HAS mean_val)
    min_mean_val = float(MIN_MEAN_DEFAULT if min_mean is None else min_mean)
    min_ha_val   = float(MIN_HA_DEFAULT   if min_ha   is None else min_ha)

    fld_area = arcpy.AddFieldDelimiters(out_fc, "AREA_HA")
    fld_mean = arcpy.AddFieldDelimiters(out_fc, MEAN_FIELD)
    where = f"({fld_area} > {min_ha_val}) AND ({fld_mean} IS NOT NULL AND {fld_mean} > {min_mean_val})"

    # ---- 6) Select & write output from out_fc (not ovl_fc)
    if arcpy.Exists(out_sel) and OVERWRITE_OUT:
        arcpy.management.Delete(out_sel)
    arcpy.analysis.Select(out_fc, out_sel, where)

    # ---- 7) Drop non-essential fields
    keep_upper = {MEAN_FIELD.upper(), "AREA_HA"}
    drop = [
        f.name for f in arcpy.ListFields(out_sel)
        if (not f.required) and (f.type not in ("OID", "Geometry")) and (f.name.upper() not in keep_upper)
    ]
    if drop:
        try:
            arcpy.management.DeleteField(out_sel, drop)
        except Exception:
            pass

    return out_sel

# -----------------------------
# MAIN DRIVER
# -----------------------------
def main():
    scratch_gdb = init_scratch_gdb()
    pat = "**/*.shp" if RECURSIVE else "*.shp"
    shp_list = sorted(glob.glob(os.path.join(POLY_FOLDER, pat), recursive=RECURSIVE))
    if not shp_list:
        print("No shapefiles found.")
        return

    print(f"Polys : {len(shp_list)}")
    print(f"Raster : {RASTER_FOLDER if RASTER_FOLDER else '(search per key)'}")
    print(f"Output: {OUT_FOLDER}")
    print(f"Scratch GDB: {scratch_gdb}")

    processed = 0
    skipped   = 0
    missing   = 0

    for shp in shp_list:
        stem = os.path.splitext(os.path.basename(shp))[0]

        # --- raster selection ---
        if RASTER_FOLDER:   # use one fixed raster for all polygons
            if not arcpy.Exists(RASTER_FOLDER):
                print(f"❌ Raster path not found: {RASTER_FOLDER}")
                return
            raster_path = RASTER_FOLDER
        else:             # fall back to per-key search
            key = _extract_key_from_shp(stem)
            rasters = _find_rasters_for_key(key)
            if not rasters:
                print(f"❌ No raster found for key '{key}' (from {stem})")
                missing += 1
                continue
            raster_path = _pick_best_raster(rasters)

        # --- process ---
        try:
            print(f"→ {os.path.basename(shp)}  ×  {os.path.basename(raster_path)}")
            process_one(shp, raster_path, OUT_FOLDER, scratch_gdb)
            processed += 1
        except Exception as e:
            print(f"⚠️  Failed on {stem}: {e}")
            skipped += 1

    print(f"Done. Processed={processed}, Skipped={skipped}, NoRaster={missing}")

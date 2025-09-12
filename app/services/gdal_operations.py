# app/services/gdal_operations.py
from __future__ import annotations 
from osgeo import gdal 
from pathlib import Path
from typing import List, Optional 
import os 
import numpy as np

gdal.UseExceptions()          # ← recomendado

# (opcional) valor por defecto para compatibilidad
ALIGNED_FOLDER_DEFAULT = "app/temp_aligned"

def _ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def check_and_align_rasters(input_paths: List[str], aligned_dir: Optional[str] = None) -> List[str]:
    """
    Verifica CRS y dimensiones. Si difieren, genera versiones alineadas
    en `aligned_dir` (si se pasa) o en ALIGNED_FOLDER_DEFAULT.
    Retorna rutas (originales o alineadas).
    """
    if not input_paths:
        return []

    aligned_root = _ensure_dir(aligned_dir or ALIGNED_FOLDER_DEFAULT)

    ref_ds = gdal.Open(input_paths[0])
    if not ref_ds:
        print(f"[X] Error al abrir la capa base: {input_paths[0]}")
        return []

    ref_proj = ref_ds.GetProjection()
    ref_transform = ref_ds.GetGeoTransform()
    ref_width = ref_ds.RasterXSize
    ref_height = ref_ds.RasterYSize

    print(f"[**] Raster base: {input_paths[0]} ({ref_width}x{ref_height})")

    aligned_paths: List[str] = []

    for src in input_paths:
        ds = gdal.Open(src)
        if not ds:
            print(f"[X] Error al abrir {src}")
            continue

        band = ds.GetRasterBand(1)
        array = band.ReadAsArray()
        nodata = band.GetNoDataValue()

        proj = ds.GetProjection()
        width, height = ds.RasterXSize, ds.RasterYSize

        # salida candidata (no pisa el original)
        stem = Path(src).stem
        out_path = aligned_root / f"{stem}_aligned.tif"
        current_path = src
        changed = False

        # 1) reproyección si difiere CRS
        if proj != ref_proj:
            print(f"[!] CRS diferente en {src}. REPROYECTANDO.")
            current_path = reproject_raster(
                current_path, ref_proj, str(out_path), nodata_value=nodata
            )
            changed = True

        # 2) ajuste de dimensiones si difieren
        if (width != ref_width) or (height != ref_height):
            print(f"[!] Dimensiones diferentes en {src}. AJUSTANDO DIMENSIONES")
            # si aún no cambiamos, usar out_path; si ya lo usamos, crear otro nombre
            out_dim = out_path if not changed else aligned_root / f"{stem}_aligned_size.tif"
            current_path = adjust_dimensions_raster(
                current_path, ref_transform, ref_width, ref_height, str(out_dim), nodata_value=nodata
            )
            changed = True

        # si no hubo cambios, usamos el original
        final_path = current_path if changed else src

        if not Path(final_path).exists():
            print(f"[X] ERROR: {final_path} no fue generado correctamente.")
            continue

        aligned_paths.append(str(final_path))

    print("[OK] Finalizó la verificación y alineación de los rásters.")
    return aligned_paths


def reproject_raster(input_path: str, target_crs: str, temp_output: str, nodata_value) -> str:
    dataset = gdal.Open(input_path)
    if not dataset:
        print(f"[X] Error al abrir el ráster al reproyectar, se retorna el original: {input_path}")
        return input_path

    _ensure_dir(Path(temp_output).parent)
    reprojected_ds = gdal.Warp(
        temp_output,
        dataset,
        dstSRS=target_crs,
        resampleAlg=gdal.GRA_NearestNeighbour,  # categorías
        dstNodata=nodata_value
    )
    print(f"[**] Reproyectando {input_path} → {temp_output}")
    if reprojected_ds:
        reprojected_ds = None
        return temp_output
    return input_path


def adjust_dimensions_raster(
    input_path: str, ref_transform: tuple, ref_width: int, ref_height: int,
    temp_output: str, nodata_value
) -> str:
    dataset = gdal.Open(input_path)
    if not dataset:
        return input_path

    xmin, ymax = ref_transform[0], ref_transform[3]
    xmax = xmin + ref_width * ref_transform[1]
    ymin = ymax + ref_height * ref_transform[5]  # píxel Y negativo

    _ensure_dir(Path(temp_output).parent)
    adjusted_ds = gdal.Warp(
        temp_output,
        dataset,
        width=ref_width,
        height=ref_height,
        resampleAlg=gdal.GRA_NearestNeighbour,
        outputBounds=(xmin, ymin, xmax, ymax),
        dstNodata=nodata_value
    )
    print(f"[**] Ajustando dimensiones {input_path} → {temp_output} ({ref_width}x{ref_height})")
    if adjusted_ds:
        adjusted_ds = None
        return temp_output
    return input_path

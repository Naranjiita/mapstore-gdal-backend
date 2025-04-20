from osgeo import gdal
import os
from typing import List
import numpy as np

ALIGNED_FOLDER = "app/temp_aligned"
os.makedirs(ALIGNED_FOLDER, exist_ok=True)

def check_and_align_rasters(input_paths: List[str]) -> List[str]:
    """
    Verifica y alinea los rásters en cuanto a:
    - CRS
    - Dimensiones
    Si hay diferencias, crea nuevas versiones alineadas en `temp_aligned/`.
    """
    if not input_paths:
        print("❌ No se han proporcionado rutas de entrada.")
        return []

    ref_ds = gdal.Open(input_paths[0])
    if not ref_ds:
        print(f"❌ Error al abrir la capa base: {input_paths[0]}")
        return []

    ref_proj = ref_ds.GetProjection()
    ref_transform = ref_ds.GetGeoTransform()
    ref_width = ref_ds.RasterXSize
    ref_height = ref_ds.RasterYSize

    print(f"✅ Raster base: {input_paths[0]} ({ref_width}x{ref_height}, {ref_proj})")

    aligned_paths = []
    for path in input_paths:
        ds = gdal.Open(path)
        if not ds:
            print(f"❌ Error al abrir {path}")
            continue
        # 👇 Agrega aquí la impresión de estadísticas
        band = ds.GetRasterBand(1)
        array = band.ReadAsArray()
        nodata = band.GetNoDataValue()
        print(f"📊 Stats de {path}: min={np.min(array)}, max={np.max(array)}, nodata={nodata}")
        #############
        proj = ds.GetProjection()
        width, height = ds.RasterXSize, ds.RasterYSize

        temp_path = os.path.join(ALIGNED_FOLDER, os.path.basename(path).replace(".tif", "_aligned.tif"))
        aligned_path = path

        if proj != ref_proj:
            print(f"⚠️ CRS diferente en {path}. Reproyectando...")
            aligned_path = reproject_raster(aligned_path, ref_proj, temp_path)

        if width != ref_width or height != ref_height:
            print(f"⚠️ Dimensiones diferentes en {path}. Ajustando...")
            aligned_path = adjust_dimensions_raster(aligned_path, ref_transform, ref_width, ref_height, temp_path)

        if not os.path.exists(aligned_path):
            print(f"❌ ERROR: {aligned_path} no fue generado correctamente.")
            continue

        aligned_paths.append(aligned_path)

    print("✅ Finalizó la verificación y alineación de los rásters.")
    return aligned_paths

def reproject_raster(input_path: str, target_crs: str, temp_output: str) -> str:
    """
    Reproyecta el raster para que coincida con el CRS de referencia.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        return input_path

    reprojected_ds = gdal.Warp(temp_output, dataset, dstSRS=target_crs, resampleAlg=gdal.GRA_NearestNeighbour)
    if reprojected_ds:
        reprojected_ds = None
        return temp_output
    return input_path

def adjust_dimensions_raster(input_path: str, ref_transform: tuple, ref_width: int, ref_height: int, temp_output: str) -> str:
    """
    Ajusta las dimensiones del raster para que coincidan con la capa de referencia.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        return input_path

    xmin, ymax = ref_transform[0], ref_transform[3]
    xmax = xmin + ref_width * ref_transform[1]
    ymin = ymax + ref_height * ref_transform[5]

    # Asegurar que la carpeta de salida existe antes de usarla
    output_directory = os.path.dirname(temp_output)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    adjusted_ds = gdal.Warp(
        temp_output,
        dataset,
        width=ref_width,
        height=ref_height,
        resampleAlg=gdal.GRA_NearestNeighbour,
        outputBounds=(xmin, ymin, xmax, ymax),
        dstNodata=255
    )
    if adjusted_ds:
        adjusted_ds = None
        return temp_output
    return input_path

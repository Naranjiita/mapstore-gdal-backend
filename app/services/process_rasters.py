from osgeo import gdal,osr
import numpy as np
import os
from typing import List
from app.services.gdal_operations import check_and_align_rasters
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

BLOCK_SIZE = 256  # Tamaño de bloque para procesamiento en memoria

RESULT_FOLDER = "app/result"
MIN_VALID_VALUE =  0  # Valor mínimo válido para evitar problemas con NoData


# Defaults para compatibilidad con el flujo actual
UPLOAD_FOLDER_FINAL_DEFAULT = Path("app/temp")
UPLOAD_FOLDER_TEMP_DEFAULT = Path("app/temp_processing")
ALIGNED_DEFAULT = Path("app/temp_aligned")


def process_rasters(
    input_paths: List[str],
    multipliers: List[float],
    output_path: str,
    temp_dir: Optional[str] = None,      # ⬅️ nuevo (opcional)
    aligned_dir: Optional[str] = None    # ⬅️ nuevo (opcional)
) -> str:
    """
    Suma ponderada de rásters (bloque a bloque), escribiendo en `output_path`.
    Usa `temp_dir`/`aligned_dir` si se proveen; si no, usa defaults.
    """

    if len(input_paths) != len(multipliers):
        print("[X]  Error: Listas de archivos y multiplicadores deben tener la misma longitud.")
        return ""

    # Resolver directorios (compatibles con el código actual)
    temp_dir_p = Path(temp_dir) if temp_dir else UPLOAD_FOLDER_TEMP_DEFAULT
    aligned_p  = Path(aligned_dir) if aligned_dir else ALIGNED_DEFAULT
    out_path_p = Path(output_path)

    # Asegurar carpetas que vamos a usar
    temp_dir_p.mkdir(parents=True, exist_ok=True)
    aligned_p.mkdir(parents=True, exist_ok=True)
    out_path_p.parent.mkdir(parents=True, exist_ok=True)

    # 1) Alinear escribiendo en `aligned_p` (ya no carpeta global fija)
    aligned_paths = check_and_align_rasters(input_paths, aligned_dir=str(aligned_p))
    if not aligned_paths:
        print("[X] Error: No se generaron archivos alineados.")
        return ""

    # 2) Dataset base
    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print(" [X] Error: No se pudo abrir la capa base.")
        return ""

    base_crs = base_dataset.GetProjection()
    base_transform = base_dataset.GetGeoTransform()
    base_width = base_dataset.RasterXSize
    base_height = base_dataset.RasterYSize

    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(str(out_path_p), base_width, base_height, 1, gdal.GDT_Float32)
    if output_dataset is None:
        print(" [X] Error: No se pudo crear el archivo vacío de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)

    nodata_base = base_dataset.GetRasterBand(1).GetNoDataValue()
    if nodata_base is None:
        nodata_base = 255.0
    out_band.SetNoDataValue(nodata_base)

    # 3) Cálculo bloque a bloque
    for y in range(0, base_height, BLOCK_SIZE):
        block_height = min(BLOCK_SIZE, base_height - y)
        for x in range(0, base_width, BLOCK_SIZE):
            block_width = min(BLOCK_SIZE, base_width - x)

            sum_block = np.zeros((block_height, block_width), dtype=np.float32)
            valid_mask_global_0_7 = np.ones_like(sum_block, dtype=bool)

            for i, input_path in enumerate(aligned_paths):
                multiplier = multipliers[i]
                dataset = gdal.Open(input_path)
                if not dataset:
                    print(f"[X]  Error al abrir el raster {input_path} para el bloque ({x},{y}).")
                    continue

                band = dataset.GetRasterBand(1)
                nodata = band.GetNoDataValue()
                if nodata is None:
                    nodata = 255.0

                array = band.ReadAsArray(x, y, block_width, block_height)
                if array is None:
                    continue

                array = array.astype(np.float32)
                valid_mask_0_7 = ((array >= 0) & (array <= 7)) & (~np.isnan(array)) & (~np.isinf(array))

                sum_block += np.where(valid_mask_0_7, array * multiplier, 0)
                valid_mask_global_0_7 &= valid_mask_0_7

            # Donde no hay datos válidos, asignar NoData
            sum_block = np.where(valid_mask_global_0_7, sum_block, nodata_base)

            # (opcional) Debug ruidoso: comenta si no quieres spam en logs
            # print(f"- Block ({x},{y}) stats: min={np.nanmin(sum_block)}, max={np.nanmax(sum_block)}")

            out_band.WriteArray(sum_block, x, y)

    out_band.ComputeStatistics(False)
    out_band, output_dataset = None, None

    print(f"[OK] Raster generado en: {out_path_p}")
    return str(out_path_p)


def compute_bbox_4326(file_name: str):

    RESULT_FOLDER = "app/result"
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"[X] error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})

    try:
        ds = gdal.Open(file_path)
        if ds is None:
            return JSONResponse(status_code=500, content={"[X] error": "No se pudo abrir el archivo con GDAL."})

        gt = ds.GetGeoTransform()
        width = ds.RasterXSize
        height = ds.RasterYSize

        # Coordenadas en sistema original
        x_min = gt[0]
        y_max = gt[3]
        x_max = gt[0] + width * gt[1]
        y_min = gt[3] + height * gt[5]

        ring_coords = [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max)
        ]

        # Reproyección a EPSG:4326
        source = osr.SpatialReference()
        source.ImportFromWkt(ds.GetProjection())
        target = osr.SpatialReference()
        target.ImportFromEPSG(4326)

        transform = osr.CoordinateTransformation(source, target)
        reproj_coords = [transform.TransformPoint(x, y) for x, y in ring_coords]

        lons = [p[0] for p in reproj_coords]
        lats = [p[1] for p in reproj_coords]

        bbox_4326 = [min(lons), min(lats), max(lons), max(lats)]

        return JSONResponse(content={
            "file_name": f"{file_name}.tif",
            "bbox_4326": bbox_4326,
            "epsg": 4326
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

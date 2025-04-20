from osgeo import gdal,osr
import numpy as np
import os
from typing import List
from app.services.gdal_operations import check_and_align_rasters
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

BLOCK_SIZE = 256  # Tamaño de bloque para procesamiento en memoria

RESULT_FOLDER = "app/result"

def process_rasters(input_paths: List[str], multipliers: List[float], output_path: str) -> str:
    NODATA_VALUE = 255.0

    if len(input_paths) != len(multipliers):
        print("❌ Error: Listas de archivos y multiplicadores deben tener la misma longitud.")
        return ""

    aligned_paths = check_and_align_rasters(input_paths)
    if not aligned_paths:
        print("❌ Error: No se generaron archivos alineados.")
        return ""

    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print("❌ Error: No se pudo abrir la capa base.")
        return ""

    base_crs = base_dataset.GetProjection()
    base_transform = base_dataset.GetGeoTransform()
    base_width = base_dataset.RasterXSize
    base_height = base_dataset.RasterYSize

    driver = gdal.GetDriverByName('GTiff')
    output_directory = os.path.dirname(output_path)
    os.makedirs(output_directory, exist_ok=True)

    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)
    if output_dataset is None:
        print("❌ Error: No se pudo crear el archivo de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)
    out_band.SetNoDataValue(NODATA_VALUE)

    for y in range(0, base_height, BLOCK_SIZE):
        block_height = min(BLOCK_SIZE, base_height - y)
        for x in range(0, base_width, BLOCK_SIZE):
            block_width = min(BLOCK_SIZE, base_width - x)
            sum_block = np.zeros((block_height, block_width), dtype=np.float32)

            for i, input_path in enumerate(aligned_paths):
                multiplier = multipliers[i]
                dataset = gdal.Open(input_path)
                if not dataset:
                    print(f"❌ Error al abrir {input_path}.")
                    continue

                band = dataset.GetRasterBand(1)
                nodata = band.GetNoDataValue()
                if nodata is None:
                    nodata = NODATA_VALUE

                array = band.ReadAsArray(x, y, block_width, block_height)
                if array is None:
                    continue

                array = array.astype(np.float32)

                # Reemplazar cualquier valor NoData extraño por 255
                array[np.isinf(array)] = NODATA_VALUE
                array[np.isnan(array)] = NODATA_VALUE
                array[array == nodata] = NODATA_VALUE

                # Máscara de valores válidos
                valid_mask = array != NODATA_VALUE

                processed_array = np.full_like(array, NODATA_VALUE)
                processed_array[valid_mask] = array[valid_mask] * multiplier

                sum_block[valid_mask] += processed_array[valid_mask]
                sum_block[~valid_mask] = NODATA_VALUE

            print(f"🧩 Block ({x},{y}) stats: min={np.nanmin(sum_block)}, max={np.nanmax(sum_block)}, unique={np.unique(sum_block)}")
            out_band.WriteArray(sum_block, x, y)

    out_band.ComputeStatistics(False)
    out_band, output_dataset = None, None
    print(f"✅ Raster generado en: {output_path}")
    return output_path


def compute_bbox_4326(file_name: str):

    RESULT_FOLDER = "app/result"
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})

    try:
        ds = gdal.Open(file_path)
        if ds is None:
            return JSONResponse(status_code=500, content={"error": "No se pudo abrir el archivo con GDAL."})

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

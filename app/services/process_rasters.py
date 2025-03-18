from osgeo import gdal
import numpy as np
import os
from typing import List
from app.services.gdal_operations import check_and_align_rasters

BLOCK_SIZE = 256  # Tamaño de bloque para procesamiento en memoria

def process_rasters(input_paths: List[str], multipliers: List[float], output_path: str) -> str:
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
    # Asegurar que la carpeta de salida existe
    output_directory = os.path.dirname(output_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)
    if output_dataset is None:
        print("❌ Error: No se pudo crear el archivo de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)
    out_band.SetNoDataValue(255)

    #  Procesamiento en bloques
    for y in range(0, base_height, BLOCK_SIZE):
        block_height = min(BLOCK_SIZE, base_height - y)  # Evita salir del tamaño real

        for x in range(0, base_width, BLOCK_SIZE):
            block_width = min(BLOCK_SIZE, base_width - x)

            # Crear bloque vacío
            sum_block = np.zeros((block_height, block_width), dtype=np.float32)

            for i, input_path in enumerate(aligned_paths):
                multiplier = multipliers[i]
                dataset = gdal.Open(input_path)
                if not dataset:
                    print(f"❌ Error al abrir {input_path}.")
                    continue

                band = dataset.GetRasterBand(1)
                original_nodata_value = band.GetNoDataValue() or 255

                array = band.ReadAsArray(x, y, block_width, block_height)
                if array is None:
                    continue

                array = array.astype(np.float32)

                # Multiplicamos evitando modificar valores NoData
                processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multiplier)

                # Sumar valores válidos
                sum_block = np.where((sum_block == 255) | (processed_array == 255), 255, sum_block + processed_array)

            # Escribir el bloque en el archivo de salida
            out_band.WriteArray(sum_block, x, y)

    out_band.ComputeStatistics(False)
    out_band, output_dataset = None, None

    print(f"✅ Raster generado en: {output_path}")
    return output_path

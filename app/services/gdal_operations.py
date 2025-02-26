from osgeo import gdal, gdal_array
import numpy as np
import tempfile
import os
from typing import List
from io import BytesIO

def process_rasters(files: List[BytesIO], multipliers: List[float]) -> str:
    if len(files) != len(multipliers):
        raise ValueError("Error: El número de archivos y multiplicadores debe ser el mismo.")

    # Crear archivos temporales para GDAL
    temp_files = []
    for file in files:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".tif")
        temp.write(file.read())
        temp.flush()
        temp.close()
        temp_files.append(temp.name)

    # Cargar la primera capa como referencia
    base_dataset = gdal.Open(temp_files[0])
    if not base_dataset:
        raise RuntimeError("Error: No se pudo abrir el archivo base.")

    base_crs = base_dataset.GetProjection()
    base_transform = base_dataset.GetGeoTransform()
    base_width = base_dataset.RasterXSize
    base_height = base_dataset.RasterYSize

    sum_array = np.zeros((base_height, base_width), dtype=np.float32)

    for i, temp_file in enumerate(temp_files):
        dataset = gdal.Open(temp_file)
        if not dataset:
            print(f"❌ ERROR: No se pudo abrir el archivo raster {temp_file}.")
            continue

        band = dataset.GetRasterBand(1)
        original_nodata_value = band.GetNoDataValue() or 255
        band.SetNoDataValue(original_nodata_value)

        array = band.ReadAsArray().astype(np.float32)
        processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multipliers[i])

        sum_array = np.where(
            (sum_array == 255) | (processed_array == 255),
            255,
            sum_array + processed_array
        )

    # Crear un archivo temporal para la salida
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tif")
    output_path = output_file.name
    output_file.close()

    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)

    if output_dataset is None:
        raise RuntimeError("❌ ERROR: No se pudo crear el archivo de salida.")

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)

    out_band = output_dataset.GetRasterBand(1)
    out_band.WriteArray(sum_array)
    out_band.SetNoDataValue(255)
    out_band.ComputeStatistics(False)

    band, dataset, out_band, output_dataset = None, None, None, None

    # Eliminar archivos temporales de entrada
    for temp_file in temp_files:
        os.remove(temp_file)

    return output_path

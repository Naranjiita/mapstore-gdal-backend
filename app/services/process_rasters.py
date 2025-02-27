from osgeo import gdal
import numpy as np
import os
from typing import List
from app.services.gdal_operations import check_and_align_rasters  # Importamos la validación previa

def process_rasters(input_paths: List[str], multipliers: List[float], output_path: str) -> str:
    """
    Procesa capas ráster alineándolas primero y luego realizando la multiplicación y suma.
    """
    if len(input_paths) != len(multipliers):
        print("❌ Error: Las listas de archivos de entrada y multiplicadores deben tener la misma longitud.")
        return ""

    # **Asegurar que las capas están alineadas y usar las capas corregidas**
    aligned_paths = check_and_align_rasters(input_paths)

    # **Cargar la primera capa como referencia**
    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print("❌ Error: No se pudo abrir el archivo base después de la alineación.")
        return ""

    base_crs = base_dataset.GetProjection()  # CRS de la capa base
    base_transform = base_dataset.GetGeoTransform()  # Geotransform de la capa base
    base_width = base_dataset.RasterXSize  # Dimensión X
    base_height = base_dataset.RasterYSize  # Dimensión Y
    
    # **Crear la capa resultante con ceros**
    sum_array = np.zeros((base_height, base_width), dtype=np.float32)

    # **Procesar cada capa alineada**
    for i in range(len(aligned_paths)):
        input_path = aligned_paths[i]
        multiplier = multipliers[i]

        dataset = gdal.Open(input_path)
        if not dataset:
            print(f"❌ ERROR: No se pudo abrir el archivo raster {input_path}.")
            continue

        # **Leer la banda**
        band = dataset.GetRasterBand(1)
        original_nodata_value = band.GetNoDataValue() or 255
        band.SetNoDataValue(original_nodata_value)

        array = band.ReadAsArray().astype(np.float32)

        # **Multiplicar sin modificar NoData**
        processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multiplier)

        # **Sumar sin modificar NoData**
        sum_array = np.where(
            (sum_array == 255) | (processed_array == 255),
            255,
            sum_array + processed_array
        )

    # **Crear raster final**
    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)

    if output_dataset is None:
        print("❌ ERROR: No se pudo crear el archivo de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)

    out_band = output_dataset.GetRasterBand(1)
    out_band.WriteArray(sum_array)
    out_band.SetNoDataValue(255)

    out_band.ComputeStatistics(False)

    band, dataset, out_band, output_dataset = None, None, None, None

    print(f"✅ Proceso completado. Raster generado en: {output_path}")
    return output_path

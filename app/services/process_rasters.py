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

    for path in aligned_paths:
        if path is None:
            print(f"❌ ERROR: Una de las capas alineadas no se generó correctamente.")
            return ""

    # **Cargar la primera capa como referencia**
    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print("❌ Error: No se pudo abrir el archivo base después de la alineación.")
        return ""

    base_crs = base_dataset.GetProjection()  # CRS de la capa base
    base_transform = base_dataset.GetGeoTransform()  # Geotransform de la capa base
    base_width = base_dataset.RasterXSize  # Dimensión X
    base_height = base_dataset.RasterYSize  # Dimensión Y

    # 📌 Crear el archivo TIFF de salida en disco
    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)

    if output_dataset is None:
        print("❌ ERROR: No se pudo crear el archivo de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)
    out_band.SetNoDataValue(255)

    # 📌 Iterar por cada capa para aplicar multiplicador y sumar
    for i in range(len(aligned_paths)):
        input_path = aligned_paths[i]
        multiplier = multipliers[i]

        if not os.path.exists(input_path):
            print(f"❌ ERROR: El archivo {input_path} no existe.")
            continue
        dataset = gdal.Open(input_path)
        if dataset is None:
            print(f"❌ ERROR: No se pudo abrir el archivo {input_path}. Puede estar corrupto o vacío.")
            continue


        band = dataset.GetRasterBand(1)
        original_nodata_value = band.GetNoDataValue() or 255

        # Leer toda la imagen a la vez en memoria
        array = band.ReadAsArray().astype(np.float32)

        if array is None:
            print(f"❌ Error: No se pudo leer el ráster {input_path}. Omitiendo...")
            continue  # Si no se puede leer el archivo, pasamos al siguiente

        # Multiplicamos evitando modificar valores NoData
        processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multiplier)

        # Leer toda la imagen de salida en memoria
        existing_array = out_band.ReadAsArray()
        if existing_array is None:
            existing_array = np.zeros_like(processed_array)  # Inicializar si es la primera capa

        # Sumar las capas evitando modificar NoData
        sum_array = np.where((existing_array == 255) | (processed_array == 255), 255, existing_array + processed_array)

        # Guardar la imagen procesada completa en el TIFF de salida
        out_band.WriteArray(sum_array)


        dataset = None  # Cerrar archivo GDAL después de procesarlo

    # 📌 Calcular estadísticas finales
    out_band.ComputeStatistics(False)

    # 📌 Cerrar datasets para liberar memoria
    out_band, output_dataset = None, None

    print(f"✅ Proceso completado. Raster generado en: {output_path}")
    return output_path

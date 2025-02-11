from osgeo import gdal
import numpy as np
import os

def process_rasters(input_paths, output_paths, multipliers, base_nodata=255):
    """
    Procesa múltiples archivos raster aplicando una multiplicación a cada uno.
    Se asegura de que todos tengan el mismo CRS, resolución y dimensiones.

    Parámetros:
    - input_paths: Lista de rutas de archivos raster de entrada.
    - output_paths: Lista de rutas de archivos raster de salida.
    - multipliers: Lista de factores de multiplicación para cada raster.
    - base_nodata: Valor NoData a usar (por defecto 255).
    """

    if not (len(input_paths) == len(output_paths) == len(multipliers)):
        print("Error: Listas de entrada, salida y multiplicadores deben tener la misma longitud.")
        return

    # 📌 Cargar la primera capa como referencia
    base_dataset = gdal.Open(input_paths[0])
    if not base_dataset:
        print("Error: No se pudo abrir el archivo base.")
        return

    base_crs = base_dataset.GetProjectionRef()
    base_transform = base_dataset.GetGeoTransform()
    base_width, base_height = base_dataset.RasterXSize, base_dataset.RasterYSize
    base_nodata = base_dataset.GetRasterBand(1).GetNoDataValue()
    if base_nodata is None:
        base_nodata = 255  # Si no tiene NoData definido, se asigna 255

    print(f"📌 CRS base: {base_crs}")
    print(f"📌 Resolución base: {base_transform[1]} x {base_transform[5]}")
    print(f"📌 Dimensiones base: {base_width} x {base_height}")

    for i in range(len(input_paths)):
        input_path = input_paths[i]
        output_path = output_paths[i]
        multiplier = multipliers[i]

        temp_proj = f"{output_path}_proj.tif"
        temp_resample = f"{output_path}_resample.tif"
        temp_resize = f"{output_path}_resize.tif"

        # 📌 Abrir raster de entrada
        dataset = gdal.Open(input_path)
        if not dataset:
            print(f"Error: No se pudo abrir el archivo raster {input_path}.")
            continue

        print(f"📂 Raster cargado: {input_path}")
        print(f"📏 Dimensiones: {dataset.RasterXSize} x {dataset.RasterYSize}")

        # ✅ **1. Reproyectar si el CRS no coincide**
        if dataset.GetProjectionRef() != base_crs:
            print(f"🔄 Reproyectando {input_path} a {base_crs}...")
            dataset = gdal.Warp(temp_proj, dataset, dstSRS=base_crs, resampleAlg=gdal.GRA_NearestNeighbour, dstNodata=base_nodata)
            input_path = temp_proj  # Usar el archivo reproyectado

        # ✅ **2. Ajustar la resolución si es diferente**
        transform = dataset.GetGeoTransform()
        if transform[1] != base_transform[1] or transform[5] != base_transform[5]:
            print(f"🔧 Remuestreando {input_path} para coincidir con la resolución de referencia...")
            dataset = gdal.Warp(temp_resample, dataset, xRes=base_transform[1], yRes=base_transform[5], resampleAlg=gdal.GRA_NearestNeighbour, dstNodata=base_nodata)
            input_path = temp_resample  # Usar el archivo remuestreado

        # ✅ **3. Ajustar dimensiones si son diferentes**
        if dataset.RasterXSize != base_width or dataset.RasterYSize != base_height:
            print(f"⚠️ Ajustando dimensiones de {input_path} a {base_width} x {base_height}...")
            dataset = gdal.Warp(temp_resize, dataset, width=base_width, height=base_height, resampleAlg=gdal.GRA_NearestNeighbour, dstNodata=base_nodata)
            input_path = temp_resize  # Usar el archivo ajustado

        # ✅ **4. Aplicar cálculo matemático**
        band = dataset.GetRasterBand(1)
        original_nodata_value = band.GetNoDataValue()
        if original_nodata_value is None:
            original_nodata_value = base_nodata
        band.SetNoDataValue(original_nodata_value)

        array = band.ReadAsArray().astype(np.float32)
        processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multiplier)

        # ✅ **5. Guardar resultado final**
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)
        output_dataset.SetGeoTransform(base_transform)
        output_dataset.SetProjection(base_crs)

        out_band = output_dataset.GetRasterBand(1)
        out_band.WriteArray(processed_array)
        out_band.SetNoDataValue(original_nodata_value)

        out_band.ComputeStatistics(False)

        # Cerrar archivos
        band, dataset, out_band, output_dataset = None, None, None, None

        # 🔥 **Eliminar archivos temporales**
        for temp_file in [temp_proj, temp_resample, temp_resize]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        print(f"✅ Operación completada. Nuevo raster guardado en: {output_path}")

# 🔹 **Ejemplo de uso**
input_files = [
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_1.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_2.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_3.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_4.tif"
]

output_files = [
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/2v2_1_gdalAPI.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/2v2_2_gdalAPI.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/2v2_3_gdalAPI.tif",
    "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/2v2_4_gdalAPI.tif"
]

multipliers = [0.1905, 0.1540, 0.3690, 0.2864]

process_rasters(input_files, output_files, multipliers)

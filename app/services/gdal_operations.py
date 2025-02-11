from osgeo import gdal
import numpy as np
import os

def process_rasters(input_paths, output_path, multipliers):
    if len(input_paths) != len(multipliers):
        print("Error: Las listas de archivos de entrada y multiplicadores deben tener la misma longitud.")
        return
    
    # Cargar la primera capa como referencia
    base_dataset = gdal.Open(input_paths[0])
    if not base_dataset:
        print("Error: No se pudo abrir el archivo base.")
        return
    
    base_crs = base_dataset.GetProjection()  # CRS de la capa base
    base_transform = base_dataset.GetGeoTransform()  # Geotransform de la capa base
    base_width = base_dataset.RasterXSize  # Dimensión X
    base_height = base_dataset.RasterYSize  # Dimensión Y
    
    # **Crear la capa resultante con ceros**
    sum_array = np.zeros((base_height, base_width), dtype=np.float32)

    # Procesar cada capa
    for i in range(len(input_paths)):
        input_path = input_paths[i]
        multiplier = multipliers[i]

        dataset = gdal.Open(input_path)
        if not dataset:
            print(f"❌ ERROR: No se pudo abrir el archivo raster {input_path}.")
            continue

        temp_path = f"{output_path}_temp_{i}.tif"  # Archivo temporal único para cada capa

        # **Reproyectar si el CRS no coincide**
        if dataset.GetProjection() != base_crs:
            print(f"🔄 Reproyectando {input_path} a {base_crs}...")
            dataset = gdal.Warp(temp_path, dataset, dstSRS=base_crs, resampleAlg=gdal.GRA_NearestNeighbour)

        # **Remuestrear si la resolución es diferente**
        if dataset.GetGeoTransform()[1] != base_transform[1] or dataset.GetGeoTransform()[5] != base_transform[5]:
            print(f"🔧 Remuestreando {input_path} para coincidir con la resolución de referencia...")
            dataset = gdal.Warp(temp_path, dataset, xRes=base_transform[1], yRes=base_transform[5], resampleAlg=gdal.GRA_NearestNeighbour)

        # **Ajustar dimensiones si son diferentes**
        if dataset.RasterXSize != base_width or dataset.RasterYSize != base_height:
            print(f"📏 Ajustando dimensiones de {input_path} a {base_width}x{base_height}...")
            xmin, ymax = base_transform[0], base_transform[3]
            xmax = xmin + base_width * base_transform[1]
            ymin = ymax + base_height * base_transform[5]

            dataset = gdal.Warp(temp_path, dataset, width=base_width, height=base_height,
                                resampleAlg=gdal.GRA_NearestNeighbour, outputBounds=(xmin, ymin, xmax, ymax),
                                dstNodata=255)

        if not dataset:
            print(f"❌ ERROR: No se pudo ajustar {input_path}.")
            continue

        # **Leer la banda**
        band = dataset.GetRasterBand(1)
        original_nodata_value = band.GetNoDataValue() or 255  # Asumimos 255 si no hay NoData
        band.SetNoDataValue(original_nodata_value)

        array = band.ReadAsArray().astype(np.float32)

        # **Multiplicar sin modificar NoData**
        processed_array = np.where(array == original_nodata_value, original_nodata_value, array * multiplier)

        # **Sumar sin modificar NoData**
        sum_array = np.where(
            (sum_array == 255) | (processed_array == 255),  # Si cualquiera es 255, sigue siendo 255
            255,
            sum_array + processed_array  # Suma en los valores válidos
        )

    # **Crear raster final**
    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)

    if output_dataset is None:
        print("❌ ERROR: No se pudo crear el archivo de salida.")
        return

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)

    out_band = output_dataset.GetRasterBand(1)
    out_band.WriteArray(sum_array)
    out_band.SetNoDataValue(255)

    # **Calcular estadísticas para visualizar correctamente**
    out_band.ComputeStatistics(False)

    # **Liberar memoria**
    band, dataset, out_band, output_dataset = None, None, None, None

    # **Eliminar archivos temporales**
    for i in range(len(input_paths)):
        temp_path = f"{output_path}_temp_{i}.tif"
        if os.path.exists(temp_path):
            os.remove(temp_path)

    print(f"✅ Proceso completado. Raster generado en: {output_path}")

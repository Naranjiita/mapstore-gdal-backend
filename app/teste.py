from osgeo import gdal
import numpy as np

def process_raster(input_path, output_path, multiplier):
    # Abrir el raster de entrada
    dataset = gdal.Open(input_path)
    if not dataset:
        print("Error: No se pudo abrir el archivo raster.")
        return

    print(f"Raster cargado: {input_path}")
    print(f"Dimensiones: {dataset.RasterXSize} x {dataset.RasterYSize}")
    print(f"Bandas: {dataset.RasterCount}")

    # Leer la primera banda
    band = dataset.GetRasterBand(1)
    original_nodata_value = band.GetNoDataValue() or 255  # Valor `NoData` inicial (255)
    band.SetNoDataValue(original_nodata_value)
    array = band.ReadAsArray()

    print("Estadísticas de la banda original:")
    print(f"  Min: {np.min(array)}, Max: {np.max(array)}")
    print(f"  Valor NoData original: {original_nodata_value}")

    # Aplicar operación (multiplicación), excluyendo valores `NoData`
    processed_array = np.where(array == original_nodata_value, -3.4028235e+38, array * multiplier)

    # Crear un nuevo archivo raster
    driver = gdal.GetDriverByName('GTiff')
    output_dataset = driver.Create(
        output_path,
        dataset.RasterXSize,
        dataset.RasterYSize,
        1,  # Número de bandas
        gdal.GDT_Float32  # Tipo de datos
    )

    # Configurar las propiedades espaciales
    output_dataset.SetGeoTransform(dataset.GetGeoTransform())
    output_dataset.SetProjection(dataset.GetProjection())

    # Escribir datos procesados en el nuevo raster
    out_band = output_dataset.GetRasterBand(1)
    out_band.WriteArray(processed_array)
    out_band.SetNoDataValue(-3.4028235e+38)  # Actualizar `NoData` al nuevo valor

    # Guardar estadísticas para el nuevo raster
    out_band.ComputeStatistics(False)

    print("Operación completada. Nuevo raster guardado en:", output_path)

# Prueba
input_file = "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_accesibilidad/dis_via.tif"
output_file = "/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_accesibilidad/dis_via_gdalAPI.tif"
process_raster(input_file, output_file, multiplier=0.2633)

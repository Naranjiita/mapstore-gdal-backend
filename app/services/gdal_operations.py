from osgeo import gdal
import numpy as np
import os

def load_raster_as_array(file_path):
    """
    Carga un archivo raster como un array de NumPy y extrae sus metadatos.
    """
    dataset = gdal.Open(file_path)
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray().astype(np.float32)

    metadata = {
        "crs": dataset.GetProjection(),
        "transform": dataset.GetGeoTransform(),
        "nodata_value": band.GetNoDataValue() or 255,
        "dimensions": (dataset.RasterYSize, dataset.RasterXSize)
    }

    return array, metadata

def process_rasters_from_arrays(raster_arrays, multipliers, metadata, output_path):
    """
    Procesa una lista de capas raster representadas como arrays de NumPy y guarda el resultado como GeoTIFF.
    """
    base_height, base_width = metadata["dimensions"]
    nodata_value = metadata["nodata_value"]

    sum_array = np.full((base_height, base_width), nodata_value, dtype=np.float32)

    for i in range(len(raster_arrays)):
        array = raster_arrays[i]
        multiplier = multipliers[i]

        processed_array = np.where(array == nodata_value, nodata_value, array * multiplier)

        sum_array = np.where(
            (sum_array == nodata_value) | (processed_array == nodata_value),
            nodata_value,
            sum_array + processed_array
        )

    driver = gdal.GetDriverByName("GTiff")
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)

    if output_dataset is None:
        raise RuntimeError("❌ ERROR: No se pudo crear el archivo de salida.")

    output_dataset.SetGeoTransform(metadata["transform"])
    output_dataset.SetProjection(metadata["crs"])

    out_band = output_dataset.GetRasterBand(1)
    out_band.WriteArray(sum_array)
    out_band.SetNoDataValue(nodata_value)
    out_band.ComputeStatistics(False)

    out_band, output_dataset = None, None

    return output_path  # Retorna la ruta del archivo generado

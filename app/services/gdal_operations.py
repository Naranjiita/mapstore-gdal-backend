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

def resize_and_reproject_raster(input_path, reference_metadata, output_path):
    """
    Ajusta la capa raster al CRS, resolución y dimensiones de la capa de referencia.
    """
    dataset = gdal.Open(input_path)
    
    # Si el CRS no coincide, reproyectamos
    if dataset.GetProjection() != reference_metadata["crs"]:
        dataset = gdal.Warp(output_path, dataset, dstSRS=reference_metadata["crs"], resampleAlg=gdal.GRA_NearestNeighbour)

    # Si la resolución o el tamaño no coinciden, ajustamos dimensiones
    if dataset.RasterXSize != reference_metadata["dimensions"][1] or dataset.RasterYSize != reference_metadata["dimensions"][0]:
        xmin, ymax = reference_metadata["transform"][0], reference_metadata["transform"][3]
        xmax = xmin + reference_metadata["dimensions"][1] * reference_metadata["transform"][1]
        ymin = ymax + reference_metadata["dimensions"][0] * reference_metadata["transform"][5]

        dataset = gdal.Warp(
            output_path, dataset, width=reference_metadata["dimensions"][1], height=reference_metadata["dimensions"][0],
            outputBounds=(xmin, ymin, xmax, ymax), resampleAlg=gdal.GRA_NearestNeighbour, dstNodata=255
        )
    
    return output_path  # Devolvemos la nueva ruta con el raster ajustado

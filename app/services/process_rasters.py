from osgeo import gdal,osr
import numpy as np
import os
from typing import List
from app.services.gdal_operations import check_and_align_rasters
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

BLOCK_SIZE = 256  # Tamaño de bloque para procesamiento en memoria

RESULT_FOLDER = "app/result"
MIN_VALID_VALUE =  0  # Valor mínimo válido para evitar problemas con NoData


def process_rasters(input_paths: List[str], multipliers: List[float], output_path: str) -> str:
    """
    Procesa una lista de rásters realizando una suma ponderada de sus valores por
    multiplicadores dados, generando un nuevo ráster de salida.

    Parámetros:
    - input_paths: lista de rutas a rásters a procesar.
    - multipliers: lista de coeficientes multiplicadores para cada ráster.
    - output_path: ruta donde se guardará el ráster resultante.

    Retorna:
    - Ruta al ráster resultante si la operación fue exitosa.
    - Cadena vacía en caso de error.
    """
    #Por seguridad hacemos nuevamente la verificación de las listas con respecto a los multiplicadores
    if len(input_paths) != len(multipliers):
        print("[X]  Error: Listas de archivos y multiplicadores deben tener la misma longitud.")
        return ""

    # Alinear rásters (CRS, dimensiones, extensión)
    aligned_paths = check_and_align_rasters(input_paths)
    if not aligned_paths:
        print("[X] Error: No se generaron archivos alineados.")
        return ""

    # Abre el ráster base (De Referencia) para obtener propiedades espaciales
    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print(" [X] Error: No se pudo abrir la capa base.")
        return ""

    base_crs = base_dataset.GetProjection()
    base_transform = base_dataset.GetGeoTransform()
    base_width = base_dataset.RasterXSize
    base_height = base_dataset.RasterYSize

    # Preparar driver para crear ráster de salida
    driver = gdal.GetDriverByName('GTiff')

    # Crear carpeta de salida si no existe
    output_directory = os.path.dirname(output_path)
    os.makedirs(output_directory, exist_ok=True)

    # Crear ráster de salida con una banda, tipo flotante 32 bits
    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)
    if output_dataset is None:
        print(" [X] Error: No se pudo crear el archivo vacío de salida.")
        return ""
    
    # Asignación de propiedades espaciales al ráster salida
    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)

    # Usar el valor NoData de la capa base para la capa resultante
    nodata_base = base_dataset.GetRasterBand(1).GetNoDataValue()
    if nodata_base is None:
        nodata_base = 255.0  # Valor por defecto si no hay definido
    out_band.SetNoDataValue(nodata_base)

    # Procesar ráster bloque por bloque para optimizar el uso de memoria
    for y in range(0, base_height, BLOCK_SIZE): 
        block_height = min(BLOCK_SIZE, base_height - y)

        for x in range(0, base_width, BLOCK_SIZE):
            block_width = min(BLOCK_SIZE, base_width - x)

             # Inicializar acumuladores para suma ponderada y máscaras
            sum_block = np.zeros((block_height, block_width), dtype=np.float32)
            valid_mask_global = np.ones_like(sum_block, dtype=bool)  # inicia todo en True
            valid_mask_global_0_7 = np.ones_like(sum_block, dtype=bool)  # inicia todo en True

            # Iterar por cada ráster alineado y su multiplicador
            for i, input_path in enumerate(aligned_paths):
                multiplier = multipliers[i]
                dataset = gdal.Open(input_path)
                if not dataset:
                    print(f"[X]  Error al abrir el raster {input_path} para el bloque ({x},{y}).")
                    continue
                
                #Establecemos el NoData para el ráster actual
                band = dataset.GetRasterBand(1)
                nodata = band.GetNoDataValue()
                if nodata is None:
                    nodata = 255.0

                # Leer bloque de datos del ráster actual
                array = band.ReadAsArray(x, y, block_width, block_height)
                if array is None:
                    continue

                # Convertimos a float32 para precisión en cálculo
                array = array.astype(np.float32)
                # Creamos la máscara válida (donde hay datos válidos): Es decir, , no es NaN y no es infinito
                valid_mask = ((array >= 1) & (array <= 7) ) & (~np.isnan(array)) & (~np.isinf(array))
                valid_mask_0_7  = ((array >=0) & (array <= 7) ) & (~np.isnan(array)) & (~np.isinf(array))
               
                # Acumulamos solo la suma de los valores válidos
                sum_block += np.where(valid_mask_0_7, array * multiplier, 0)
    
                # Actualizar máscara global válida
                valid_mask_global &= valid_mask # AND: válido solo si todas las capas son válidas
                valid_mask_global_0_7 &= valid_mask_0_7 # AND: válido solo si todas las capas son válidas


            valid_mask_intersection =  valid_mask & valid_mask_global_0_7
            # Donde no hay datos válidos, asignar NoData
            sum_block = np.where(valid_mask_global_0_7, sum_block, nodata_base)

            # Debug: imprimir estadísticas del bloque procesado
            print(f"- Block ({x},{y}) stats: min={np.nanmin(sum_block)}, max={np.nanmax(sum_block)}, unique={np.unique(sum_block)}")

            # Escribir bloque en banda de salida
            out_band.WriteArray(sum_block, x, y)

    out_band.ComputeStatistics(False)
    out_band, output_dataset = None, None

    print(f"[OK] Raster generado en: {output_path}")
    return output_path


def compute_bbox_4326(file_name: str):

    RESULT_FOLDER = "app/result"
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"[X] error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})

    try:
        ds = gdal.Open(file_path)
        if ds is None:
            return JSONResponse(status_code=500, content={"[X] error": "No se pudo abrir el archivo con GDAL."})

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

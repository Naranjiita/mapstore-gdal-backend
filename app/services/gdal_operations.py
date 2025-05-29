from osgeo import gdal
import os
from typing import List
import numpy as np

ALIGNED_FOLDER = "app/temp_aligned"
os.makedirs(ALIGNED_FOLDER, exist_ok=True)

def check_and_align_rasters(input_paths: List[str]) -> List[str]:
    """
    Verifica que los rásters de entrada tengan el mismo sistema de referencia espacial (CRS)
    y las mismas dimensiones (ancho y alto). 

    Si detecta diferencias en CRS o tamaño, genera versiones alineadas de esos rásters
    dentro de la carpeta `temp_aligned/`.

    Parámetros:
    - input_paths: Lista de rutas a archivos ráster a verificar y alinear.

    Retorna:
    - aligned_paths: Lista de rutas a rásters ya alineados (los originales o los reproyectados/ajustados).
    """
    #Abre el primer ráster para obtener la proyección y dimensiones como referencia
    ref_ds = gdal.Open(input_paths[0]) 
    if not ref_ds:
        print(f"[X] Error al abrir la capa base: {input_paths[0]}")
        return []

    # Obtener parámetros espaciales del ráster base:
    # - Sistema de coordenadas (CRS)
    # - Transformación georreferenciada (para ubicar píxeles en coordenadas geográficas)
    # - Dimensiones (ancho y alto en píxeles)
    ref_proj = ref_ds.GetProjection()
    ref_transform = ref_ds.GetGeoTransform()
    ref_width = ref_ds.RasterXSize
    ref_height = ref_ds.RasterYSize

    print(f"[**] Raster base: {input_paths[0]} ({ref_width}x{ref_height})")

    aligned_paths = []
    # Recorrer cada ráster a verificar
    for path in input_paths:
        ds = gdal.Open(path)
        if not ds:
            print(f"[X] Error al abrir {path}")
            continue

        # Leer banda 1 del ráster y calcular estadísticas básicas para debugging
        band = ds.GetRasterBand(1)
        array = band.ReadAsArray()
        nodata = band.GetNoDataValue()
        print(f"[**] Stats del RASTER {path}: min={np.min(array)}, max={np.max(array)}, nodata={nodata}")

        # Obtener CRS y dimensiones del ráster actual
        proj = ds.GetProjection()
        width, height = ds.RasterXSize, ds.RasterYSize
        print(f"[**] Raster: {path} ({width}x{height})")

        # Construir ruta temporal para ráster alineado
        temp_path = os.path.join(ALIGNED_FOLDER, os.path.basename(path).replace(".tif", "_aligned.tif"))
        aligned_path = path

        # Verificar si el CRS es diferente al de referencia
        if proj != ref_proj:
            print(f"[!] CRS diferente en {path}. REPROYECTANDO.")
            aligned_path = reproject_raster(aligned_path, ref_proj, temp_path,nodata)

        # Verificar si las dimensiones (ancho/alto) son diferentes
        if width != ref_width or height != ref_height:
            print(f"[!] Dimensiones diferentes en {path}. AJUSTANDO DIMENSIONES")
            aligned_path = adjust_dimensions_raster(aligned_path, ref_transform, ref_width, ref_height, temp_path,nodata)

        if not os.path.exists(aligned_path):
            print(f"[X] ERROR: {aligned_path} no fue generado correctamente.")
            continue

        aligned_paths.append(aligned_path)

    print("[OK] Finalizó la verificación y alineación de los rásters.")
    return aligned_paths

def reproject_raster(input_path: str, target_crs: str, temp_output: str,nodata_value) -> str:
    """
    Reproyecta un ráster para que coincida con el sistema de referencia espacial (CRS) objetivo.

    Parámetros:
    - input_path: ruta al archivo ráster original a reproyectar.
    - target_crs: cadena con el CRS destino (por ejemplo, un WKT o EPSG:XXXX).
    - temp_output: ruta donde se guardará el ráster reproyectado temporalmente.

    Retorna:
    - Ruta al ráster reproyectado si se creó correctamente.
    - Si falla, retorna la ruta original (input_path).
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        print(f"[X] Error al abrir el ráster al reproyectar, se retorna el original: {input_path}")
        return input_path

    # Reproyectar el ráster usando gdal.Warp
    # - temp_output: destino del archivo reproyectado
    # - dataset: ráster origen
    # - dstSRS: CRS destino (target_crs)
    # - resampleAlg: método de remuestreo (vecino más cercano para preservar valores categóricos)
    reprojected_ds = gdal.Warp(
        temp_output,
        dataset,
        dstSRS=target_crs,
        resampleAlg=gdal.GRA_NearestNeighbour, # Usamos el método de vecino más cercano para preservar valores categóricos
        dstNodata=nodata_value
    )
    print(f"[**] Reproyectando {input_path} a {target_crs} -> {temp_output}")

    if reprojected_ds:
        reprojected_ds = None
        return temp_output
    return input_path

def adjust_dimensions_raster(input_path: str, ref_transform: tuple, ref_width: int, ref_height: int, temp_output: str,nodata_value) -> str:
    """
    Ajusta las dimensiones (ancho y alto) y la extensión espacial de un ráster
    para que coincidan exactamente con las de una capa de referencia.

    Parámetros:
    - input_path: ruta del ráster original a ajustar.
    - ref_transform: GeoTransform del ráster de referencia (tupla de 6 valores).
    - ref_width: ancho (número de columnas) del ráster de referencia.
    - ref_height: alto (número de filas) del ráster de referencia.
    - temp_output: ruta donde se guardará el ráster ajustado temporalmente.

    Retorna:
    - Ruta del ráster ajustado si se genera correctamente.
    - Si falla, retorna la ruta original para no detener el flujo.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        return input_path

    # Extraer la extensión espacial (bounding box) del ráster referencia:
    # xmin, ymax: coordenadas del píxel superior izquierdo
    xmin, ymax = ref_transform[0], ref_transform[3]

    # xmax: coordenada X límite derecho calculada como xmin + ancho * tamaño píxel X
    xmax = xmin + ref_width * ref_transform[1]

    # ymin: coordenada Y límite inferior calculada como ymax + alto * tamaño píxel Y
    # ( el tamaño del píxel Y es negativo, por eso se suma)
    ymin = ymax + ref_height * ref_transform[5]

    # Asegurar que la carpeta de salida existe antes de usarla
    output_directory = os.path.dirname(temp_output)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    # Usar gdal.Warp para ajustar el ráster:
    # - width y height: tamaño en píxeles deseado (igual al ráster referencia)
    # - outputBounds: extensión espacial (xmin, ymin, xmax, ymax) para que coincida con el ráster referencia
    # - resampleAlg: vecino más cercano para preservar valores discretos
    # - dstNodata: valor NoData para los píxeles sin datos en la salida    
    adjusted_ds = gdal.Warp(
        temp_output,
        dataset,
        width=ref_width,
        height=ref_height,
        resampleAlg=gdal.GRA_NearestNeighbour,
        outputBounds=(xmin, ymin, xmax, ymax),
        dstNodata=nodata_value
    )
    print(f"[**] Ajustando dimensiones de {input_path} a {ref_width}x{ref_height} -> {temp_output}")
    if adjusted_ds:
        adjusted_ds = None
        return temp_output
    return input_path

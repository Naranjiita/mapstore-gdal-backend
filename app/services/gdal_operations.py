from osgeo import gdal
import os
from typing import List

def reproject_raster(input_path: str, target_crs: str, temp_output: str) -> str:
    """
    Reproyecta el raster para que coincida con el CRS de referencia.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        print(f"❌ Error al abrir el archivo {input_path} para reproyección.")
        return input_path

    reprojected_ds = gdal.Warp(temp_output, dataset, dstSRS=target_crs, resampleAlg=gdal.GRA_NearestNeighbour)
    if reprojected_ds:
        reprojected_ds = None  # Cierra el dataset
        print(f"✅ Reproyección completada: {temp_output}")
        return temp_output
    else:
        print(f"❌ Error en la reproyección de {input_path}.")
        return input_path

def resample_raster(input_path: str, xRes: float, yRes: float, temp_output: str) -> str:
    """
    Remuestrea el raster para que coincida con la resolución de referencia.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        print(f"❌ Error al abrir el archivo {input_path} para remuestreo.")
        return input_path

    resampled_ds = gdal.Warp(temp_output, dataset, xRes=xRes, yRes=abs(yRes), resampleAlg=gdal.GRA_NearestNeighbour)
    if resampled_ds:
        resampled_ds = None
        print(f"✅ Remuestreo completado: {temp_output}")
        return temp_output
    else:
        print(f"❌ Error en el remuestreo de {input_path}.")
        return input_path

def adjust_dimensions_raster(input_path: str, ref_transform: tuple, ref_width: int, ref_height: int, temp_output: str) -> str:
    """
    Ajusta las dimensiones del raster para que coincidan con la capa de referencia.
    """
    dataset = gdal.Open(input_path)
    if not dataset:
        print(f"❌ Error al abrir el archivo {input_path} para ajustar dimensiones.")
        return input_path

    # Calcular límites de salida basados en la transformación de referencia
    xmin, ymax = ref_transform[0], ref_transform[3]
    xmax = xmin + ref_width * ref_transform[1]
    ymin = ymax + ref_height * ref_transform[5]

    adjusted_ds = gdal.Warp(
        temp_output,
        dataset,
        width=ref_width,
        height=ref_height,
        resampleAlg=gdal.GRA_NearestNeighbour,
        outputBounds=(xmin, ymin, xmax, ymax),
        dstNodata=255
    )
    if adjusted_ds:
        adjusted_ds = None
        print(f"✅ Ajuste de dimensiones completado: {temp_output}")
        return temp_output
    else:
        print(f"❌ Error al ajustar dimensiones de {input_path}.")
        return input_path

def check_and_align_rasters(input_paths: List[str]) -> List[str]:
    """
    Lee la primera capa como referencia e imprime:
      - Dimensiones (width x height)
      - CRS (proyección)
    Luego compara las capas restantes para ver si coinciden en CRS y dimensiones.
    Si no coinciden, las ajusta y devuelve la lista de rutas de los archivos corregidos.
    """
    if not input_paths:
        print("❌ No se han proporcionado rutas de entrada.")
        return []

    # Abrir la primera capa como referencia
    ref_ds = gdal.Open(input_paths[0])
    if not ref_ds:
        print(f"❌ Error al abrir el archivo base: {input_paths[0]}")
        return []

    ref_proj = ref_ds.GetProjection()      # CRS de referencia
    ref_transform = ref_ds.GetGeoTransform()
    ref_width = ref_ds.RasterXSize
    ref_height = ref_ds.RasterYSize

    print(f"✅ Raster base: {input_paths[0]}")
    print(f"   Dimensiones: {ref_width} x {ref_height}")
    print(f"   CRS: {ref_proj}")

    corrected_paths = [input_paths[0]]  # La primera capa ya es la referencia

    # Verificar y ajustar las demás capas
    for path in input_paths[1:]:
        ds = gdal.Open(path)
        if not ds:
            print(f"❌ Error al abrir el archivo {path}")
            continue

        proj = ds.GetProjection()
        width = ds.RasterXSize
        height = ds.RasterYSize

        print(f"🔎 Verificando {path} ...")
        print(f"   Dimensiones: {width} x {height}")
        print(f"   CRS: {proj}")

        # Inicializamos la ruta alineada con la original
        aligned_path = path
        temp_path = f"{path}_aligned.tif"

        # Reproyectar si el CRS difiere
        if proj != ref_proj:
            print(f"⚠️  El CRS de {path} difiere del raster base. Reproyectando...")
            aligned_path = reproject_raster(aligned_path, ref_proj, temp_path)
            ds = gdal.Open(aligned_path)

        # Ajustar dimensiones si son diferentes
        if ds.RasterXSize != ref_width or ds.RasterYSize != ref_height:
            print(f"⚠️  Las dimensiones de {path} difieren del raster base. Ajustando dimensiones...")
            aligned_path = adjust_dimensions_raster(aligned_path, ref_transform, ref_width, ref_height, temp_path)
            ds = gdal.Open(aligned_path)

        print(f"✅ Finalizado ajuste para {path}. Resultado: {aligned_path}")
        corrected_paths.append(aligned_path)

    print("✅ Finalizó la verificación y ajuste de los rásters.")
    return corrected_paths  # Devuelve la lista de rutas alineadas
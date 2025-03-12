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
        print(f"❌ ERROR: No se pudo abrir {input_path} para ajustar dimensiones.")
        return input_path

    xmin, ymax = ref_transform[0], ref_transform[3]
    xmax = xmin + ref_width * ref_transform[1]
    ymin = ymax + ref_height * ref_transform[5]

    print(f"ℹ️ Ajustando dimensiones para {input_path}")
    print(f"   Output Bounds: xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}")

    adjusted_ds = gdal.Warp(
        temp_output,
        dataset,
        width=ref_width,
        height=ref_height,
        resampleAlg=gdal.GRA_NearestNeighbour,
        outputBounds=(xmin, ymin, xmax, ymax),
        dstNodata=255
    )
    if adjusted_ds is None:
        print(f"❌ Error al ajustar dimensiones de {input_path}.")
        return input_path


# 📌 Carpeta temporal para archivos alineados
ALIGNED_FOLDER = "app/temp_aligned"
os.makedirs(ALIGNED_FOLDER, exist_ok=True)  # Asegurar que la carpeta exista al iniciar

def check_and_align_rasters(input_paths: List[str]) -> List[str]:
    """
    📌 Verifica y alinea los rásters en cuanto a:
    - CRS
    - Dimensiones
    Si hay diferencias, crea nuevas versiones alineadas en `temp_aligned/`.
    """

    if not input_paths:
        print("❌ No se han proporcionado rutas de entrada.")
        return []

    ref_ds = gdal.Open(input_paths[0])
    if not ref_ds:
        print(f"❌ Error al abrir el archivo base: {input_paths[0]}")
        return []

    ref_proj = ref_ds.GetProjection()
    ref_transform = ref_ds.GetGeoTransform()
    ref_width = ref_ds.RasterXSize
    ref_height = ref_ds.RasterYSize

    print(f"✅ Raster base: {input_paths[0]}")
    print(f"   Dimensiones: {ref_width} x {ref_height}")
    print(f"   CRS: {ref_proj}")

    aligned_paths = []
    for path in input_paths:
        ds = gdal.Open(path)
        if not ds:
            print(f"❌ Error al abrir el archivo {path}")
            continue

        aligned_path = path  # Se usará el original si no necesita ajustes
        temp_path = os.path.join(ALIGNED_FOLDER, os.path.basename(path).replace(".tif", "_aligned.tif"))

        proj = ds.GetProjection()
        width = ds.RasterXSize
        height = ds.RasterYSize
        current_transform = ds.GetGeoTransform()

        if proj != ref_proj:
            print(f"⚠️  El CRS de {path} difiere. Reproyectando...")
            aligned_path = reproject_raster(aligned_path, ref_proj, temp_path)

        if width != ref_width or height != ref_height:
            print(f"⚠️  Las dimensiones de {path} difieren. Ajustando dimensiones...")
            aligned_path = adjust_dimensions_raster(aligned_path, ref_transform, ref_width, ref_height, temp_path)

        aligned_paths.append(aligned_path)

    print("✅ Finalizó la verificación y alineación de los rásters.")
    return aligned_paths  # Devuelve las rutas finales alineadas

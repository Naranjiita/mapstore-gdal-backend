from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import os
from app.utils.gdal_operations import load_raster_as_array, process_rasters_from_arrays

router = APIRouter()

@router.post("/procesar_rasters/")
async def procesar_rasters(
    files: list[UploadFile] = File(...),
    multipliers: str = Form(...)
):
    output_path = "output_result.tif"
    temp_files = []

    # Guardar archivos temporalmente
    for file in files:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        temp_files.append(temp_path)

    raster_arrays = []
    metadata = None

    # Cargar rasters en memoria
    for i, temp_path in enumerate(temp_files):
        array, meta = load_raster_as_array(temp_path)
        raster_arrays.append(array)

        # Tomar los metadatos de la primera capa
        if i == 0:
            metadata = meta

    # Convertir multiplicadores de string a lista de float
    multipliers = list(map(float, multipliers.split(",")))

    # Procesar las capas raster
    result_path = process_rasters_from_arrays(raster_arrays, multipliers, metadata, output_path)

    # Eliminar archivos temporales
    for temp_file in temp_files:
        os.remove(temp_file)

    return FileResponse(result_path, media_type="image/tiff", filename="resultado.tif")

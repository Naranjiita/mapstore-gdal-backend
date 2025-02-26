from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import os
from app.services.gdal_operations import load_raster_as_array, process_rasters_from_arrays, resize_and_reproject_raster

router = APIRouter()

@router.post("/procesar_rasters/")
async def procesar_rasters(
    files: list[UploadFile] = File(...),
    multipliers: str = Form(...)
):
    output_path = "output_result.tif"
    temp_files = []
    resized_files = []

    try:
        # Guardar archivos temporales
        for file in files:
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(temp_path)

        raster_arrays = []
        metadata = None

        # Cargar rasters en memoria y ajustar tamaño
        for i, temp_path in enumerate(temp_files):
            array, meta = load_raster_as_array(temp_path)

            # La primera capa se toma como referencia
            if i == 0:
                metadata = meta
                resized_files.append(temp_path)  # La capa base no se necesita ajustar
            else:
                # Ajustamos el raster al tamaño y CRS de la primera capa
                resized_path = f"resized_{i}.tif"
                resize_and_reproject_raster(temp_path, metadata, resized_path)
                resized_files.append(resized_path)

        # Cargar nuevamente los archivos ajustados
        raster_arrays = [load_raster_as_array(f)[0] for f in resized_files]

        # Convertir multiplicadores de string a lista de float
        multipliers = list(map(float, multipliers.split(",")))

        # Procesar las capas raster
        result_path = process_rasters_from_arrays(raster_arrays, multipliers, metadata, output_path)

    finally:
        # **Eliminar archivos temporales**
        for temp_file in temp_files + resized_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    return FileResponse(result_path, media_type="image/tiff", filename="resultado.tif")

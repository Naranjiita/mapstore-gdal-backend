from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
import shutil
import os
from app.services.gdal_operations import load_raster_as_array, process_rasters_from_arrays, resize_and_reproject_raster

router = APIRouter()

def remove_file(file_path: str):
    """Elimina un archivo si existe."""
    if os.path.exists(file_path):
        os.remove(file_path)

@router.post("/procesar_rasters/")
async def procesar_rasters(
    files: list[UploadFile] = File(...),
    multipliers: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
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

        # **Reproyectar y ajustar dimensiones antes de cargar**
        for i, temp_path in enumerate(temp_files):
            if i == 0:
                # **Usamos la primera capa como referencia**
                metadata = load_raster_as_array(temp_path)[1]
                resized_files.append(temp_path)  # No necesitamos modificar la base
            else:
                # **Ajustamos las demás capas**
                resized_path = f"resized_{i}.tif"
                resize_and_reproject_raster(temp_path, metadata, resized_path)
                resized_files.append(resized_path)

        # **Cargar nuevamente los archivos ajustados en NumPy**
        raster_arrays = [load_raster_as_array(f)[0] for f in resized_files]

        # **Convertir multiplicadores a float**
        multipliers = list(map(float, multipliers.split(",")))

        # **Procesar las capas raster**
        result_path = process_rasters_from_arrays(raster_arrays, multipliers, metadata, output_path)

    finally:
        # **Eliminar archivos temporales**
        for temp_file in temp_files + resized_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    # **Programar la eliminación del archivo de salida después de enviarlo**
    background_tasks.add_task(remove_file, output_path)

    return FileResponse(result_path, media_type="image/tiff", filename="resultado.tif")

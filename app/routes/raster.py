from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List
import os
from app.services.gdal_operations import process_rasters

router = APIRouter()

UPLOAD_FOLDER = "app/temp"

@router.post("/process_rasters/")
async def process_rasters_api(
    files: List[UploadFile] = File(...),
    multipliers: List[float] = Form(...)
):
    """
    Servicio que recibe capas raster, las multiplica, las suma y devuelve el archivo TIFF resultante.
    """

    if len(files) != len(multipliers):
        return {"error": "El número de archivos y multiplicadores debe ser el mismo"}

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    input_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    output_path = os.path.join(UPLOAD_FOLDER, "result_backendAPi.tif")

    # Procesar los rásteres
    process_rasters(input_paths, output_path, multipliers)

    # Verificar que el archivo realmente se creó antes de devolverlo
    if not os.path.exists(output_path):
        return {"error": "Error al generar el archivo TIFF"}

    # 🔹 **Devolver el archivo resultante**
    return FileResponse(
        path=output_path,
        media_type="image/tiff",
        filename="raster_resultado_MS.tif"
    )

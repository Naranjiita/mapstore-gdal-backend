from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List
import os
from app.services.gdal_operations import process_rasters

router = APIRouter()

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

    file_bytes = [await file.read() for file in files]
    
    # Procesar los rásteres
    output_path = process_rasters([BytesIO(fb) for fb in file_bytes], multipliers)

    # Verificar que el archivo realmente se creó antes de devolverlo
    if not os.path.exists(output_path):
        return {"error": "Error al generar el archivo TIFF"}

    # 🔹 **Devolver el archivo resultante**
    return FileResponse(
        path=output_path,
        media_type="image/tiff",
        filename="raster_resultado_MS.tif"
    )

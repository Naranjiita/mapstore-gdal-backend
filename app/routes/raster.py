from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import os
from app.services.gdal_operations import check_and_align_rasters

router = APIRouter()

UPLOAD_FOLDER = "app/temp"  
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/process_rasters/")
async def process_rasters_api(
    files: List[UploadFile] = File(...),
    multipliers: str = Form(...)
):
    """
    Endpoint que recibe archivos ráster y una cadena de multiplicadores.
    En esta versión simplificada, solo validamos que llegan los archivos,
    verificamos CRS y dimensiones, y respondemos con un mensaje de OK.
    """
    if not files:
        return {"error": "Se requiere al menos un archivo raster."}

    # (Opcional) Si quieres seguir recibiendo 'multipliers', los parseas aquí.
    # Pero en esta versión no los usaremos para el cálculo.
    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    # Guardar los archivos en la carpeta temporal
    input_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    # Llamar a la función que chequea y (opcionalmente) alinea los rásters
    check_and_align_rasters(input_paths)

    # Eliminar archivos temporales si no los necesitas para nada más
    for file_path in input_paths:
        os.remove(file_path)

    return {"status": "ok"}

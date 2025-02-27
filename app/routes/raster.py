from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List
import os
from app.services.process_rasters import process_rasters  # Importamos la nueva función de procesamiento

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
    Asegura que todas las capas sean compatibles antes de operar sobre ellas.
    Luego, realiza la multiplicación y la suma y devuelve el TIFF resultante.
    """
    if not files:
        return {"error": "Se requiere al menos un archivo raster."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    if len(files) != len(multipliers_list):
        return {"error": "El número de archivos y multiplicadores debe ser el mismo."}

    # Guardar los archivos en la carpeta temporal
    input_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    # Definir la ruta para el archivo de salida
    output_path = os.path.join(UPLOAD_FOLDER, "resultado_combinado.tif")

    # Llamar a la función que procesa las capas (alineación + operación matemática)
    result_path = process_rasters(input_paths, multipliers_list, output_path)

    # Eliminar archivos temporales de entrada
    for file_path in input_paths:
        os.remove(file_path)

    if result_path:
        # Devolver el archivo TIFF resultante
        return FileResponse(result_path, media_type="image/tiff", filename="resultado_combinado.tif")
    else:
        return {"error": "Hubo un error al procesar los rásters."}

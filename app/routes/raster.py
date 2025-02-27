from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import os
import shutil
from app.services.process_rasters import process_rasters  # Importamos la nueva función de procesamiento

router = APIRouter()

#  Carpeta donde se guardará el resultado final
UPLOAD_FOLDER_FINAL = "app/temp"

#  Carpeta temporal para almacenar capas de entrada antes del procesamiento
UPLOAD_FOLDER_TEMP = "app/temp_processing"

#  Asegurar que ambas carpetas existen al iniciar el servidor
os.makedirs(UPLOAD_FOLDER_FINAL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)


@router.post("/process_rasters/")
async def process_rasters_api(
    files: List[UploadFile] = File(...),
    multipliers: str = Form(...),
    output_filename: str = Form(...)
):
    """
     Endpoint para procesar rásters.
    
    1️ Recibe archivos ráster y una lista de multiplicadores.
    2️ Guarda temporalmente las capas en `temp_processing/`.
    3️ Asegura que las capas sean compatibles antes de operar sobre ellas.
    4️ Realiza la multiplicación y la suma.
    5️ Guarda el archivo final en `temp/`.
    6️ Elimina automáticamente las capas de entrada después del cálculo.
    """

    if not files:
        return {"error": "Se requiere al menos un archivo raster."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    if len(files) != len(multipliers_list):
        return {"error": "El número de archivos y multiplicadores debe ser el mismo."}

    #  Guardar los archivos en la carpeta `temp_processing/`
    input_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER_TEMP, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    #  Definir la ruta del archivo final en `temp/`
    output_path = os.path.join(UPLOAD_FOLDER_FINAL, output_filename)

    #  Procesar los rásters
    result_path = process_rasters(input_paths, multipliers_list, output_path)

    #  Eliminar archivos temporales de entrada después del procesamiento
    for file_path in input_paths:
        os.remove(file_path)

    #  Eliminar la carpeta `temp_processing/` una vez que se haya usado
    shutil.rmtree(UPLOAD_FOLDER_TEMP)

    #  Devolver el archivo TIFF final que está en `temp/`
    if result_path:
        return FileResponse(result_path, media_type="image/tiff", filename=output_filename)
    else:
        return {"error": "Hubo un error al procesar los rásters."}


@router.delete("/clean_temp/")
async def clean_temp_folder():
    """
     Endpoint para eliminar manualmente los archivos de la carpeta `temp/`.

    Se usa cuando el frontend envía una solicitud para limpiar los archivos generados.
    """
    if os.path.exists(UPLOAD_FOLDER_FINAL):
        shutil.rmtree(UPLOAD_FOLDER_FINAL)  # Borra la carpeta `temp/` y su contenido
        os.makedirs(UPLOAD_FOLDER_FINAL)  # Vuelve a crear la carpeta vacía
        return JSONResponse({"message": "Carpeta temp eliminada con éxito."})
    else:
        return JSONResponse({"error": "La carpeta temp no existe."})

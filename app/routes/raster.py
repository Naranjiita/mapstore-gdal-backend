from fastapi import APIRouter, UploadFile, File, Form, Query
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

    #  Asegurar que la carpeta `temp_processing/` existe ANTES de guardar archivos
    if not os.path.exists(UPLOAD_FOLDER_TEMP):
        os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)

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
    
@router.post("/combine_stored_rasters/")
async def combine_stored_rasters(
    multipliers: str = Form(...),
    output_filename: str = Form(...)
):
    """
    📌 Nueva funcionalidad:
    - Toma automáticamente las 7 capas almacenadas en `temp/`.
    - Recibe un arreglo de 7 números decimales como multiplicadores.
    - Multiplica cada capa por su respectivo número y las suma.
    - Guarda el resultado en `result/`.
    """

    # 📌 Definir carpetas
    TEMP_FOLDER = "app/temp"  # Carpeta donde ya están almacenadas las 7 capas
    RESULT_FOLDER = "app/result"  # Carpeta donde se guardará la capa final
    os.makedirs(RESULT_FOLDER, exist_ok=True)  # Asegurar que exista

    # 📌 Obtener las 7 capas de `temp/`
    raster_files = sorted([os.path.join(TEMP_FOLDER, f) for f in os.listdir(TEMP_FOLDER) if f.endswith(".tif")])

    if len(raster_files) != 7:
        return {"error": f"Se esperaban exactamente 7 capas en {TEMP_FOLDER}, pero se encontraron {len(raster_files)}."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    if len(multipliers_list) != 7:
        return {"error": "El número de multiplicadores debe ser exactamente 7."}

    # 📌 Definir ruta de salida en `result/`
    output_path = os.path.join(RESULT_FOLDER, output_filename)

    # 📌 Procesar rásters
    result_path = process_rasters(raster_files, multipliers_list, output_path)

    if result_path:
        return {"message": "Cálculo completado con éxito.", "file_path": result_path}
    else:
        return {"error": "Hubo un error al procesar las capas almacenadas."}


#  Carpeta donde se guardarán los resultados finales
RESULT_FOLDER = "app/result"

#  Asegurar que la carpeta `result/` existe
os.makedirs(RESULT_FOLDER, exist_ok=True)
@router.get("/download_result/")
async def download_result(file_name: str = Query(..., description="Nombre del archivo a descargar (sin extensión .tif)")):
    """
    📌 Endpoint para descargar un raster resultante desde `result/`.
    - Se espera solo el nombre del archivo sin la extensión `.tif`.
    - El archivo debe estar en la carpeta `result/`.
    """
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})

    return FileResponse(file_path, media_type="image/tiff", filename=f"{file_name}.tif")


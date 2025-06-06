from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import os
import shutil
from app.services.process_rasters import process_rasters, compute_bbox_4326 
from app.services.upload_geonetwork import upload_geonetwork as upload_to_geonetwork_service
import zipfile
import tempfile

router = APIRouter()

#  Carpeta donde se guardará el resultado final
UPLOAD_FOLDER_FINAL = "app/temp"

#  Carpeta temporal para almacenar capas de entrada antes del procesamiento
UPLOAD_FOLDER_TEMP = "app/temp_processing"

RESULT_FOLDER = "app/result"  # Carpeta donde se guardará la capa final
    

#  Asegurar que ambas carpetas existen al iniciar el servidor
os.makedirs(UPLOAD_FOLDER_FINAL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)  # Asegurar que exista


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
        return {"[X] error": "Se requiere al menos un archivo raster."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"[X] error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    if len(files) != len(multipliers_list):
        return {"[X] error": "El número de archivos y multiplicadores debe ser el mismo."}

    #  Asegurar que la carpeta `temp_processing/` existe ANTES de guardar archivos
    if not os.path.exists(UPLOAD_FOLDER_TEMP):
        os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)

    input_paths = []
    #Aquí empieza a guardar los archivos en `temp_processing/`
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER_TEMP, file.filename) 
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    #  Definir la ruta del archivo final en `temp/`
    output_path = os.path.join(UPLOAD_FOLDER_FINAL, output_filename)

    #  Procesar los rásters
    try:
        result_path = process_rasters(input_paths, multipliers_list, output_path)
    except Exception as e:
        print(f"⚠️ Error en el procesamiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

    #  Eliminar archivos temporales de entrada después del procesamiento
    for file_path in input_paths:
        os.remove(file_path)

    # Eliminar la carpeta `temp_processing/` y `temp_aligned/`
    shutil.rmtree(UPLOAD_FOLDER_TEMP)
    shutil.rmtree("app/temp_aligned", ignore_errors=True)

    # Volver a crear las carpetas después de eliminarlas
    os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)
    os.makedirs("app/temp_aligned", exist_ok=True)


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
    
@router.delete("/clean_result/")
async def clean_result_folder():
    """
     Endpoint para eliminar manualmente los archivos de la carpeta `result/`.

    Se usa cuando el frontend envía una solicitud para limpiar los archivos generados.
    """
    if os.path.exists(RESULT_FOLDER):
        shutil.rmtree(RESULT_FOLDER)  # Borra la carpeta `temp/` y su contenido
        os.makedirs(RESULT_FOLDER)  # Vuelve a crear la carpeta vacía
        return JSONResponse({"message": "Carpeta result eliminada con éxito."})
    else:
        return JSONResponse({"error": "La carpeta result no existe."})
    
@router.post("/combine_stored_rasters/")
async def combine_stored_rasters(
    multipliers: str = Form(...),
    output_filename: str = Form(...)
):
    """
    Último Proceso de la metodología:
    - Toma automáticamente las 7 capas almacenadas en `temp/`.
    - Recibe un arreglo de 7 números decimales como multiplicadores.
    - Multiplica cada capa por su respectivo número y las suma.
    - Guarda el resultado en `result/`.
    """

    #  Definir carpetas
    TEMP_FOLDER = "app/temp"  # Carpeta donde ya están almacenadas las 7 capas
  

    #  Obtener las 7 capas de `temp/`
    raster_files = sorted([os.path.join(TEMP_FOLDER, f) for f in os.listdir(TEMP_FOLDER) if f.endswith(".tif")])

    if len(raster_files) != 7:
        return {"error": f"Se esperaban exactamente 7 capas en {TEMP_FOLDER}, pero se encontraron {len(raster_files)}."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los valores de los multiplicadores deben ser números flotantes separados por comas."}

    if len(multipliers_list) != 7:
        return {"error": "El número de multiplicadores debe ser exactamente 7."}

    #  Definir ruta de salida en `result/`
    output_path = os.path.join(RESULT_FOLDER, output_filename)

    #  Procesar rásters
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
    Endpoint para descargar un raster resultante desde `result/`.
    - Se espera solo el nombre del archivo sin la extensión `.tif`.
    - El archivo debe estar en la carpeta `result/`.
    """
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})

    return FileResponse(file_path, media_type="image/tiff", filename=f"{file_name}.tif")



@router.get("/download_all_temp/")
async def download_all_temp():
    """
     Endpoint para comprimir todas las capas en `temp/` y enviarlas en un ZIP.
    """

    TEMP_FOLDER = "app/temp"

    # Verificar que hay archivos en `temp/`
    raster_files = [os.path.join(TEMP_FOLDER, f) for f in os.listdir(TEMP_FOLDER) if f.endswith(".tif")]
    if not raster_files:
        return JSONResponse(status_code=404, content={"error": "No hay archivos en la carpeta temp."})

    # Crear un archivo temporal para el ZIP (en un lugar seguro)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        zip_path = tmp_zip.name

    # Comprimir los archivos uno por uno, evitando usar mucha RAM
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in raster_files:
            zipf.write(file, os.path.basename(file))  # Guardar solo el nombre del archivo en el ZIP

    # Enviar el ZIP generado
    return FileResponse(zip_path, media_type="application/zip", filename="all_rasters.zip")


@router.post("/upload_geonetwork/")
async def upload_geonetwork(xml_file: UploadFile = File(...)):
    """
    Recibe un archivo XML desde el frontend y lo sube a GeoNetwork.
    """
    return await upload_to_geonetwork_service(xml_file)


@router.get("/get_bbox_4326/")
async def get_bbox_4326(file_name: str = Query(..., description="Nombre del archivo sin extensión .tif")):
    """
    📌 Devuelve el bounding box en EPSG:4326 para un archivo .tif guardado en `result/`.
    """
    return  compute_bbox_4326(file_name)


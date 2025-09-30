# app/routes/raster.py
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import os
import shutil
import zipfile
import tempfile

from app.services.process_rasters import process_rasters, compute_bbox_4326
from app.services.gdal_operations import check_and_align_rasters  # para limpieza fina
from app.services.upload_geonetwork import upload_geonetwork as upload_to_geonetwork_service

router = APIRouter()

#  Carpetas “legacy” (compatibles con el frontend actual)
UPLOAD_FOLDER_FINAL = "app/temp"             # donde quedan las 7 capas intermedias
UPLOAD_FOLDER_TEMP = "app/temp_processing"   # donde se suben las capas de entrada
ALIGNED_FOLDER = "app/temp_aligned"          # donde se escriben los *_aligned.tif
RESULT_FOLDER = "app/result"                 # donde se guarda la capa final

#  Asegurar que existan al iniciar
os.makedirs(UPLOAD_FOLDER_FINAL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)
os.makedirs(ALIGNED_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


@router.post("/process_rasters/")
async def process_rasters_api(
    files: List[UploadFile] = File(...),
    multipliers: str = Form(...),
    output_filename: str = Form(...)
):
    """
    1) Recibe rásters y multiplicadores.
    2) Guarda entradas en temp_processing/.
    3) Alinea en temp_aligned/ si hace falta.
    4) Calcula y deja salida en temp/.
    5) Limpia SOLO los archivos de esta request (no borra carpetas globales).
    """
    if not files:
        return {"[X] error": "Se requiere al menos un archivo raster."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"[X] error": "Los multiplicadores deben ser números flotantes separados por comas."}

    if len(files) != len(multipliers_list):
        return {"[X] error": "El número de archivos y multiplicadores debe ser el mismo."}

    os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)
    os.makedirs(ALIGNED_FOLDER, exist_ok=True)

    # 1) Guardar entradas en temp_processing/
    input_paths: List[str] = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER_TEMP, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        input_paths.append(file_path)

    # 2) Salida en temp/
    output_path = os.path.join(UPLOAD_FOLDER_FINAL, output_filename)

    # 3) Procesar
    try:
        result_path = process_rasters(
            input_paths, multipliers_list, output_path,
            temp_dir=UPLOAD_FOLDER_TEMP,
            aligned_dir=ALIGNED_FOLDER
        )
    except Exception as e:
        print(f"⚠️ Error en el procesamiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

    # 4) Limpieza fina (solo lo que generó esta request)
    #    - Entradas subidas
    for fp in input_paths:
        try:
            os.remove(fp)
        except FileNotFoundError:
            pass

    #    - Alineados generados en esta request: buscamos por los nombres base
    try:
        # reconstruimos potenciales nombres alineados
        candidate_aligned = []
        for src in input_paths:
            base = os.path.splitext(os.path.basename(src))[0]
            # Dos patrones posibles que genera gdal_operations:
            candidate_aligned.append(os.path.join(ALIGNED_FOLDER, f"{base}_aligned.tif"))
            candidate_aligned.append(os.path.join(ALIGNED_FOLDER, f"{base}_aligned_size.tif"))
        for ap in candidate_aligned:
            if os.path.exists(ap):
                try:
                    os.remove(ap)
                except FileNotFoundError:
                    pass
    except Exception as e:
        # limpieza best-effort (no debe romper la respuesta)
        print(f"⚠️ Limpieza de alineados con warning: {e}")

    # 5) Responder
    if result_path:
        return FileResponse(result_path, media_type="image/tiff", filename=output_filename)
    else:
        return {"error": "Hubo un error al procesar los rásters."}


@router.delete("/clean_temp/")
async def clean_temp_folder():
    """Limpia manualmente la carpeta `temp/` (capas intermedias)."""
    if os.path.exists(UPLOAD_FOLDER_FINAL):
        shutil.rmtree(UPLOAD_FOLDER_FINAL)
        os.makedirs(UPLOAD_FOLDER_FINAL, exist_ok=True)
        return JSONResponse({"message": "Carpeta temp eliminada con éxito."})
    else:
        return JSONResponse({"error": "La carpeta temp no existe."})


@router.delete("/clean_result/")
async def clean_result_folder():
    """Limpia manualmente la carpeta `result/` (capas finales)."""
    if os.path.exists(RESULT_FOLDER):
        shutil.rmtree(RESULT_FOLDER)
        os.makedirs(RESULT_FOLDER, exist_ok=True)
        return JSONResponse({"message": "Carpeta result eliminada con éxito."})
    else:
        return JSONResponse({"error": "La carpeta result no existe."})


@router.post("/combine_stored_rasters/")
async def combine_stored_rasters(
    multipliers: str = Form(...),
    output_filename: str = Form(...)
):
    """
    Toma las 7 capas en temp/ y genera una final en result/.
    """
    TEMP_FOLDER = UPLOAD_FOLDER_FINAL

    raster_files = sorted(
        os.path.join(TEMP_FOLDER, f)
        for f in os.listdir(TEMP_FOLDER)
        if f.endswith(".tif")
    )

    if len(raster_files) != 7:
        return {"error": f"Se esperaban 7 capas en {TEMP_FOLDER}, se encontraron {len(raster_files)}."}

    try:
        multipliers_list = list(map(float, multipliers.split(",")))
    except ValueError:
        return {"error": "Los multiplicadores deben ser números flotantes separados por comas."}

    if len(multipliers_list) != 7:
        return {"error": "El número de multiplicadores debe ser exactamente 7."}

    output_path = os.path.join(RESULT_FOLDER, output_filename)

    result_path = process_rasters(
        raster_files, multipliers_list, output_path,
        aligned_dir=ALIGNED_FOLDER  # por consistencia
    )

    if result_path:
        return {"message": "Cálculo completado con éxito.", "file_path": result_path}
    else:
        return {"error": "Hubo un error al procesar las capas almacenadas."}


@router.get("/download_result/")
async def download_result(file_name: str = Query(..., description="Nombre del archivo a descargar (sin .tif)")):
    """Descarga un raster final desde `result/`."""
    file_path = os.path.join(RESULT_FOLDER, f"{file_name}.tif")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"El archivo {file_name}.tif no existe en {RESULT_FOLDER}."})
    return FileResponse(file_path, media_type="image/tiff", filename=f"{file_name}.tif")


@router.get("/download_all_temp/")
async def download_all_temp():
    """Comprime todas las capas en `temp/` y las envía en ZIP."""
    TEMP_FOLDER = UPLOAD_FOLDER_FINAL
    raster_files = [
        os.path.join(TEMP_FOLDER, f)
        for f in os.listdir(TEMP_FOLDER)
        if f.endswith(".tif")
    ]
    if not raster_files:
        return JSONResponse(status_code=404, content={"error": "No hay archivos en la carpeta temp."})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        zip_path = tmp_zip.name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in raster_files:
            zipf.write(file, os.path.basename(file))

    return FileResponse(zip_path, media_type="application/zip", filename="all_rasters.zip")


@router.post("/upload_geonetwork/")
async def upload_geonetwork(xml_file: UploadFile = File(...)):
    """Sube un XML a GeoNetwork."""
    return await upload_to_geonetwork_service(xml_file)


@router.get("/get_bbox_4326/")
async def get_bbox_4326(file_name: str = Query(..., description="Nombre del archivo sin extensión .tif")):
    """Devuelve el bounding box EPSG:4326 para un .tif guardado en `result/`."""
    return compute_bbox_4326(file_name)

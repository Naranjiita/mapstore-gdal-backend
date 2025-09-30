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

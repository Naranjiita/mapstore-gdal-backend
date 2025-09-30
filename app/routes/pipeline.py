# app/routers/pipeline.py
from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
from pathlib import Path
from osgeo import gdal

from app.utils.pipeline_utils import (
    new_job_id, ensure_job_dirs, init_manifest, read_manifest, write_manifest,
    save_uploads_chunked, sanitize_filename, job_root, cleanup_job
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# ⚠️ Ajusta estos imports a tus funciones reales
# La idea es: NO usar rutas globales dentro de estas funciones.
# Deben recibir "aligned_dir/final_dir" explícitos.
from app.services.process_rasters import process_rasters
# Donde:
# - process_rasters_stage1(inputs: List[str], multipliers: List[float], output_path: str, aligned_dir: str) -> str
# - process_rasters_stage2(inputs_7: List[str], multipliers: List[float], output_path: str, work_dir: str) -> str

gdal.UseExceptions()  # errores claros

@router.post("/start")
async def pipeline_start(
    files: List[UploadFile] = File(...),
    multipliers: str = Form(...),
    output_filename: str = Form(...),
    job_id: Optional[str] = Form(None),
    user: Optional[str] = Form(None)
):
    """
    Etapa 1: recibe N rasters y multipliers. Genera UNA salida intermedia (por ejemplo, por categoría).
    - Si no viene job_id => crea uno y arranca el pipeline.
    - Si viene job_id => agrega una salida más a stage1/outputs de ese job.
    Devuelve: job_id y lista acumulada de outputs de stage1.
    """
    try:
        multipliers_list = [float(x) for x in multipliers.split(",")]
    except Exception:
        raise HTTPException(400, detail="Multiplicadores inválidos. Usa flotantes separados por coma.")

    job = job_id or new_job_id()
    dirs = ensure_job_dirs(job)

    # manifest
    m = read_manifest(job)
    if not m:
        m = init_manifest(job, user=user)

    # guardar entradas en stage1/inputs
    input_paths = save_uploads_chunked(dirs["stage1_inputs"], files)

    out_name = sanitize_filename(output_filename)
    out_path = str((dirs["stage1_outputs"] / out_name).resolve())

    try:
        result_path = process_rasters(
            input_paths=input_paths,
            multipliers=multipliers_list,
            output_path=out_path,
            aligned_dir=str(dirs["stage1_aligned"]),  # <- usa el aligned del job
        )


    except Exception as e:
        raise HTTPException(500, detail=f"Error en Stage1: {e}")

    # actualizar manifest
    m["status"] = "stage1_partial"
    m.setdefault("stage1", {}).setdefault("outputs", [])
    if result_path not in m["stage1"]["outputs"]:
        m["stage1"]["outputs"].append(result_path)
    write_manifest(job, m)

    return JSONResponse({"job_id": job, "added": result_path, "stage1_outputs": m["stage1"]["outputs"]})


@router.post("/continue")
async def pipeline_continue(
    job_id: str = Form(...),
    multipliers: Optional[str] = Form(None),
    output_filename: Optional[str] = Form("final_result.tif")
):
    """
    Etapa 2: usa las 7 salidas de Stage1 y produce el raster final.
    """
    m = read_manifest(job_id)
    if not m:
        raise HTTPException(404, detail="job_id no encontrado")

    outputs = m.get("stage1", {}).get("outputs") or []
    if len(outputs) < 7:
        raise HTTPException(400, detail=f"Stage1 incompleto. Se esperan 7 capas, hay {len(outputs)}.")

    mults = None
    if multipliers:
        try:
            mults = [float(x) for x in multipliers.split(",")]
        except Exception:
            raise HTTPException(400, detail="Multiplicadores Stage2 inválidos")

    dirs = ensure_job_dirs(job_id)
    out_name = sanitize_filename(output_filename or "final_result.tif")
    final_path = str((dirs["final_dir"] / out_name).resolve())

    try:
        result = process_rasters(
            input_paths=outputs[:7],
            multipliers=mults or [1,1,1,1,1,1,1],
            output_path=final_path,
            aligned_dir=str(dirs["stage2_aligned"]),   
        )

    except Exception as e:
        raise HTTPException(500, detail=f"Error en Stage2: {e}")

    m["status"] = "done"
    m["stage1"]["done"] = True
    m["stage2"] = {"done": True, "output": result}
    write_manifest(job_id, m)

    return {"job_id": job_id, "final": result}


@router.get("/result/{job_id}")
def pipeline_result(job_id: str):
    m = read_manifest(job_id)
    if not m:
        raise HTTPException(404, detail="job_id no encontrado")

    fp = (m.get("stage2") or {}).get("output")
    if not fp or not Path(fp).exists():
        raise HTTPException(404, detail="Resultado final no disponible")
    return FileResponse(fp, media_type="image/tiff", filename=Path(fp).name)


@router.get("/status/{job_id}")
def pipeline_status(job_id: str):
    m = read_manifest(job_id)
    if not m:
        raise HTTPException(404, detail="job_id no encontrado")
    return m


@router.delete("/{job_id}")
def pipeline_delete(job_id: str):
    if not job_root(job_id).exists():
        raise HTTPException(404, detail="job_id no encontrado")
    cleanup_job(job_id)
    return {"ok": True}

    # Alias para cerrar job con POST (compatible con sendBeacon)
@router.post("/close")
def pipeline_close(job_id: str = Form(None)):
    if not job_id:
        #  JSON:
        # data = await request.json(); job_id = data.get("job_id")
        raise HTTPException(400, "job_id requerido")
    if not job_root(job_id).exists():
        return {"ok": True}  # idempotente
    cleanup_job(job_id)
    return {"ok": True}


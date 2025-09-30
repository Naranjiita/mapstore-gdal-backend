# app/utils/pipeline_utils.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid, json, shutil, time, os

BASE_PIPE = Path("app/pipelines")
BASE_PIPE.mkdir(parents=True, exist_ok=True)

def now_ts() -> float:
    return time.time()

def new_job_id() -> str:
    return uuid.uuid4().hex[:8]

def job_root(job_id: str) -> Path:
    return BASE_PIPE / job_id

def ensure_job_dirs(job_id: str) -> Dict[str, Path]:
    root = job_root(job_id)  # Path del job, p.ej. app/pipelines/<job>

    s1_inputs  = root / "stage1" / "inputs"
    s1_outputs = root / "stage1" / "outputs"
    s1_aligned = root / "stage1" / "aligned"   # <- nuevo (por job)
    s2_aligned = root / "stage2" / "aligned"   # <- nuevo (por job)
    s2_work    = root / "stage2" / "work"
    final_dir  = root / "final"

    # Crear todas las carpetas necesarias
    for p in (s1_inputs, s1_outputs, s1_aligned, s2_work, final_dir,s2_aligned):
        p.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "stage1_inputs": s1_inputs,
        "stage1_outputs": s1_outputs,
        "stage1_aligned": s1_aligned,
        "stage2_aligned": s2_aligned,
        "stage2_work": s2_work,
        "final_dir": final_dir,
    }

def manifest_path(job_id: str) -> Path:
    return job_root(job_id) / "manifest.json"

def read_manifest(job_id: str) -> Dict[str, Any]:
    p = manifest_path(job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def write_manifest(job_id: str, data: Dict[str, Any]) -> None:
    p = manifest_path(job_id)
    p.write_text(json.dumps(data, indent=2))

def init_manifest(job_id: str, user: Optional[str] = None) -> Dict[str, Any]:
    data = {
        "job_id": job_id,
        "user": user,
        "created_at": now_ts(),
        "status": "created",
        "stage1": {"done": False, "outputs": []},
        "stage2": {"done": False},
    }
    write_manifest(job_id, data)
    return data

def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "").strip()
    base = base.replace("..", "_").replace("/", "_").replace("\\", "_")
    return base or f"file_{new_job_id()}.tif"

def save_uploads_chunked(dst_dir: Path, files) -> List[str]:
    paths = []
    for uf in files:
        safe = sanitize_filename(getattr(uf, "filename", None) or "input.tif")
        dst = dst_dir / safe
        with open(dst, "wb") as out:
            # leer en chunks para no explotar RAM
            while True:
                chunk = uf.file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        paths.append(str(dst))
    return paths

def cleanup_job(job_id: str) -> None:
    shutil.rmtree(job_root(job_id), ignore_errors=True)

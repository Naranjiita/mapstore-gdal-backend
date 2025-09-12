#app/main.py
from fastapi import FastAPI
from app.routes import raster, pipeline
from fastapi.middleware.cors import CORSMiddleware
from app.config import GEONETWORK_USER, GEONETWORK_PASSWORD

# app/main.py
app = FastAPI(title="MapStore GDAL Backend", debug=True)  # ← temporal

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los encabezados
)
# Se mantienen los endpoints actuales (compatibilidad con el frontend)
app.include_router(raster.router, tags=["Raster Processing"])

# Se montan los endpoints nuevos del pipeline
#    — si en pipeline.py ya definiste `router = APIRouter(prefix="/pipeline", ...)`
#      NO pongas otro prefix aquí.
app.include_router(pipeline.router, tags=["Pipeline"])

@app.get("/")
def root():
    print(f"Conectando con usuario: {GEONETWORK_USER}")
    return {"message": "GDAL API funcionando 🚀"}


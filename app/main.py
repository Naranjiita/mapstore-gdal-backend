from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware
from app.config import GEONETWORK_USER, GEONETWORK_PASSWORD

app = FastAPI(title="MapStore GDAL Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los encabezados
)
app.include_router(raster.router, tags=["Raster Processing"])

@app.get("/")
def root():
    print(f"Conectando con usuario: {GEONETWORK_USER}")
    return {"message": "GDAL API funcionando 🚀"}


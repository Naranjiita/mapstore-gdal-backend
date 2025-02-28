from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware
import signal
import sys

app = FastAPI(title="MapStore GDAL Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes. Puedes cambiarlo por ["http://localhost:8081"]
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los encabezados
)

app.include_router(raster.router, prefix="/api", tags=["Raster Processing"])
def shutdown():
    print("Cerrando servicio GDAL...")
    sys.exit(0)

signal.signal(signal.SIGTERM, lambda s, f: shutdown())

@app.get("/")
def root():
    return {"message": "GDAL API funcionando 🚀"}

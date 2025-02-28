from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware
import signal
import asyncio

app = FastAPI(title="MapStore GDAL Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los encabezados
)

app.include_router(raster.router, prefix="/api", tags=["Raster Processing"])

@app.get("/")
def root():
    return {"message": "GDAL API funcionando 🚀"}

def shutdown():
    print("Cerrando servicio GDAL...")
    loop = asyncio.get_event_loop()
    loop.stop()  # 📌 Detener el bucle de eventos sin generar SystemExit

signal.signal(signal.SIGTERM, lambda s, f: shutdown())

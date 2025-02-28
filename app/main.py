import asyncio
import signal
import sys
from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MapStore GDAL Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(raster.router, prefix="/api", tags=["Raster Processing"])

@app.get("/")
def root():
    return {"message": "GDAL API funcionando 🚀"}

# 🔹 Evento de apagado limpio
@app.on_event("shutdown")
async def shutdown_event():
    print("*** Servidor GDAL FastAPI iniciado. ***")
    print("Cerrando servicio GDAL...")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    try:
        await asyncio.gather(*tasks, return_exceptions=True)  # 🔹 Esperar que todas las tareas terminen
    except asyncio.CancelledError:
        pass  # Ignorar `CancelledError` al cerrar el servicio

    print("--- Todas las tareas han sido canceladas. Servicio cerrado correctamente.")

# 🔹 Capturar señales SIGTERM y SIGINT correctamente sin interrumpir asyncio
def handle_exit(signum, frame):
    print(f"Recibida señal {signum}, cerrando...")
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(shutdown_event())  # Ejecutar el cierre limpio
    except RuntimeError:
        asyncio.run(shutdown_event())

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

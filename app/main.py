import asyncio
import signal
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

# 🔹 Función de apagado mejorada
async def shutdown_event():
    print("*** Servidor GDAL FastAPI iniciado. ***")
    print("Cerrando servicio GDAL...")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)  # 🔹 Esperar que todas las tareas terminen
    except asyncio.CancelledError:
        pass  # Ignoramos `CancelledError` al cerrar el servicio

    print("--- Todas las tareas pendientes han sido canceladas. Servicio cerrado correctamente.")

# 🔹 Manejador de señal para SIGTERM
def handle_exit(*args):
    loop = asyncio.get_event_loop()
    loop.create_task(shutdown_event())  # Asegurar cierre limpio
    loop.stop()  # Detener el loop correctamente

signal.signal(signal.SIGTERM, lambda s, f: handle_exit())


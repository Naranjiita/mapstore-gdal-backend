from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI(title="MapStore GDAL Backend")

#  Manejo del ciclo de vida del servidor
@app.on_event("startup")
async def startup_event():
    print("*** Servidor GDAL FastAPI iniciado. ***")

@app.on_event("shutdown")
async def shutdown_event():
    print("Cerrando servicio GDAL...")

    #  Cancelar tareas pendientes sin cerrar el bucle de eventos abruptamente
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task  # Espera a que terminen las tareas pendientes
        except asyncio.CancelledError:
            pass  # Ignoramos el error si una tarea ya ha sido cancelada

    print("--- Todas las tareas pendientes han sido canceladas. Servicio cerrado correctamente.")

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

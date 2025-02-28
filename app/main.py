from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI(title="MapStore GDAL Backend")

#  Manejo del ciclo de vida de FastAPI
@app.on_event("startup")
async def startup_event():
    print("---Servidor GDAL FastAPI iniciado.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Cerrando servicio GDAL...")
    loop = asyncio.get_event_loop()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]  #  Cancelar todas las tareas pendientes
    await asyncio.gather(*tasks, return_exceptions=True)  #  Esperar que todas se terminen
    loop.stop()  #  Detener el bucle de eventos correctamente

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

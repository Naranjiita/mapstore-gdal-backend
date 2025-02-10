from fastapi import FastAPI
from app.routes import raster

app = FastAPI()

# Registrar las rutas del módulo raster
app.include_router(raster.router, prefix="/api/v1/raster", tags=["Raster Operations"])

@app.get("/")
def root():
    return {"message": "Welcome to MapStore GDAL Backend"}

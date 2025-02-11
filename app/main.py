from fastapi import FastAPI
from app.routes import raster
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MapStore GDAL Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes. Puedes cambiarlo por ["http://localhost:8081"]
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Permitir todos los encabezados
)

app.include_router(raster.router, prefix="/api", tags=["Raster Processing"])

@app.get("/")
def root():
    return {"message": "GDAL API funcionando 🚀"}

from fastapi import APIRouter
from app.services.gdal_operations import perform_raster_operation

router = APIRouter()

@router.post("/process")
def process_raster(input_file: str, operation: str):
    """
    Procesar un archivo raster con una operación matemática.
    """
    result = perform_raster_operation(input_file, operation)
    return {"message": "Raster processed successfully", "result": result}

import os
from osgeo import gdal

def perform_raster_operation(input_file: str, operation: str) -> str:
    """
    Realiza una operación en un archivo raster usando GDAL.
    :param input_file: Ruta al archivo raster de entrada.
    :param operation: Operación matemática a realizar.
    :return: Ruta al archivo de salida.
    """
    # Leer el archivo raster
    dataset = gdal.Open(input_file)
    if not dataset:
        raise FileNotFoundError(f"El archivo {input_file} no se pudo abrir.")

    # Aquí realizarías operaciones usando GDAL
    # Esta es solo una demostración, se necesita implementar la lógica específica
    print(f"Realizando operación '{operation}' en el archivo '{input_file}'...")

    output_file = "output.tif"
    driver = gdal.GetDriverByName("GTiff")
    driver.CreateCopy(output_file, dataset)

    return os.path.abspath(output_file)

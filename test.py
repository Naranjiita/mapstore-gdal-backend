import requests

url = "http://127.0.0.1:8000/api/process_rasters/"

# Lista de archivos a enviar
files = [
    ("files", open("/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_1.tif", "rb")),
    ("files", open("/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_2.tif", "rb")),
    ("files", open("/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_3.tif", "rb")),
    ("files", open("/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/v2_4.tif", "rb")),
]

# Multiplicadores (FastAPI espera listas en `multipart/form-data` enviadas como strings separados)
data = [("multipliers", str(0.1905)), 
        ("multipliers", str(0.1540)), 
        ("multipliers", str(0.3690)), 
        ("multipliers", str(0.2864))]

# Enviar la solicitud a la API
response = requests.post(url, files=files, data=data)

# Cerrar los archivos después de enviarlos
for f in files:
    f[1].close()

# Verificar respuesta
if response.status_code == 200:
    # Guardar el archivo TIFF devuelto por la API
    with open("/home/desarrollo/Documentos/Proyectos_Qgis/Capas_Raster/capa_uso_suelo/resultado_v4.tif", "wb") as f:
        f.write(response.content)
    print("✅ Archivo TIFF guardado en: resultado_v2.tif")
else:
    print("❌ Error:", response.status_code, response.text)

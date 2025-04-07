import requests
import urllib3
from fastapi import UploadFile, File, APIRouter, HTTPException
from fastapi.responses import JSONResponse


async def upload_geonetwork(xml_file: UploadFile = File(...)):
# Desactivar advertencias de certificados (solo si usas verify=False)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Datos del servidor y credenciales
    username = 'adminuc'
    password = 'AdmUc24*'
    server = "https://ide.ucuenca.edu.ec"
    session = requests.Session()

    try:
        # Paso 1: Autenticación
        auth_url = f"{server}/geonetwork/srv/api/me"
        response = session.get(auth_url, auth=(username, password),
                               headers={'Accept': 'application/json'}, verify=False)
        xsrf_token = session.cookies.get('XSRF-TOKEN')

        if not xsrf_token:
            raise HTTPException(status_code=401, detail="No se pudo obtener el token XSRF")

        headers = {
            'X-XSRF-TOKEN': xsrf_token,
            'Accept': 'application/json'
        }

        params = {
            'metadataType': 'METADATA',
            'uuidProcessing': 'GENERATEUUID',
            'publishToAll': 'true',
            'rejectIfInvalid': 'false'
        }

        # Leer contenido del archivo
        file_content = await xml_file.read()

        files = {
            'file': (xml_file.filename, file_content, 'application/xml')
        }

        upload_url = f"{server}/geonetwork/srv/api/records"
        upload_response = session.post(upload_url, headers=headers, params=params, files=files, verify=False)

        return JSONResponse(
            status_code=upload_response.status_code,
            content={
                "status": upload_response.status_code,
                "message": "Carga completada" if upload_response.ok else "Error al subir metadata",
                "details": upload_response.text
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
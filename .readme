# MapStore GDAL Backend

Backend basado en **FastAPI** con integración de **GDAL** para operaciones geoespaciales.  
Este README documenta cómo desplegar el proyecto en un servidor Ubuntu con `systemd`.

---

##  Stack probado

- **Ubuntu Server** 22.04+  
- **Python** 3.11  
- **GDAL** 3.11.3  
- **FastAPI** 0.115.0  
- **Starlette** 0.38.6  
- **NumPy** 1.26.4  

---

##  Instalación en servidor

### 1. Dependencias del sistema

```bash
sudo apt update
sudo apt install -y git software-properties-common curl ca-certificates

# Python 3.11
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-distutils python3.11-dev

# GDAL 3.11.x
sudo add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable
sudo apt update
sudo apt install -y gdal-bin libgdal-dev
gdal-config --version   # debería mostrar 3.11.x
```

### 2. Clonar y crear entorno

```bash
cd ~
git clone <URL_DEL_REPO>.git mapstore-gdal-backend
cd mapstore-gdal-backend

python3.11 -m venv venv311
source venv311/bin/activate
pip install --upgrade pip setuptools wheel
```

### 3. Instalar dependencias

Asegúrate que `requirements.txt` tenga:

```
numpy==1.26.4
GDAL==3.11.3
fastapi==0.115.0
starlette==0.38.6
# ... resto igual
```

Instalación:

```bash
pip install numpy==1.26.4
export GDAL_CONFIG=/usr/bin/gdal-config
pip install GDAL==3.11.3
pip install -r requirements.txt
```

---

## ▶ Ejecución manual (prueba)

```bash
source venv311/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
```

Abrir en navegador:  
`http://<IP-SERVIDOR>:8000/docs`

---

##  Configuración systemd

Crear servicio:

```bash
sudo nano /etc/systemd/system/mapstore-gdal.service
```

Contenido:

```ini
[Unit]
Description=MapStore GDAL Backend (FastAPI)
After=network.target

[Service]
User=<USUARIO>
Group=<USUARIO>
WorkingDirectory=/home/<USUARIO>/mapstore-gdal-backend
Environment="PATH=/home/<USUARIO>/mapstore-gdal-backend/venv311/bin"
EnvironmentFile=-/home/<USUARIO>/mapstore-gdal-backend/.env
ExecStart=/home/<USUARIO>/mapstore-gdal-backend/venv311/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar y arrancar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mapstore-gdal
sudo systemctl start mapstore-gdal
```

Logs:

```bash
systemctl status mapstore-gdal
journalctl -u mapstore-gdal -f
```

---


## Comando de Operación

```bash
# Ver logs
journalctl -u mapstore-gdal -f

# Reiniciar tras un cambio
sudo systemctl restart mapstore-gdal

# Actualizar código
cd ~/mapstore-gdal-backend
git pull
source venv311/bin/activate
pip install -r requirements.txt
sudo systemctl restart mapstore-gdal
```

---

##  Problemas comunes

- `gdal-config: not found` → reinstalar `gdal-bin libgdal-dev`.
- `fatal error: Python.h` → instalar `python3.11-dev`.
- Conflicto FastAPI ↔ Starlette → usar `starlette==0.38.6`.

---

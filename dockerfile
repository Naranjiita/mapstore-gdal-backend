# Usa Python como imagen base
FROM python:3.10

# Instalar dependencias del sistema necesarias para GDAL
RUN apt-get update && apt-get install -y /
    gdal-bin libgdal-dev python3-gdal /
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Verificar la instalación del sistema
RUN gdalinfo --version

# Configurar GDAL en variables de entorno
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_DATA=/usr/share/gdal
ENV PROJ_LIB=/usr/share/proj

# Establecer directorio de trabajo
WORKDIR /app

# Copiar el archivo de dependencias
COPY requirements.txt .

# ❌ **Eliminar GDAL de requirements.txt antes de instalar**
RUN sed -i '/GDAL/d' requirements.txt

# Instalar pip y las dependencias del backend (sin instalar GDAL desde pip)
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Verificar la versión de GDAL instalada en Python
RUN python3 -c "from osgeo import gdal; print(gdal.__version__)"

# Copiar el código fuente
COPY . .

# Especificar el comando para iniciar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

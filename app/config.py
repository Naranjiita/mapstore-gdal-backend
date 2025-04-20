from dotenv import load_dotenv
import os

load_dotenv()  #  .env

GEONETWORK_USER = os.getenv("GEONETWORK_USER")
GEONETWORK_PASSWORD = os.getenv("GEONETWORK_PASSWORD")
GEONETWORK_SERVER = os.getenv("GEONETWORK_SERVER")
GDAL_CACHEMAX = os.getenv("user","password")  # valor por defecto si no se define

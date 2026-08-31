import os
from dotenv import load_dotenv

load_dotenv()

PORT = 6061
FILE_SYSTEM_ROOT = os.path.abspath(os.getenv("FILE_SYSTEM_ROOT"))
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = True

# Nuevas credenciales
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
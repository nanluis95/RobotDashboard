import os
from pathlib import Path

# ============================================================
# CONFIGURACIÓN GENERAL DEL ROBOT
# ============================================================

# URL del iMaster
IMASTER_URL = "https://nce.nb.movistar.com.sv/unisso/login.action?decision=1&service=%2Funisess%2Fv1%2Fauth%3Fservice%3D%252F"

# Credenciales
# Se obtendrán desde las variables de entorno de GitHub
USUARIO = os.environ.get("IMASTER_USUARIO")
CONTRASENA = os.environ.get("IMASTER_CONTRASENA")

# En GitHub Actions trabajaremos sin mostrar el navegador
HEADLESS = True

TIMEOUT = 60000


# =====================================================
# CARPETAS
# =====================================================

BASE_DIR = Path(__file__).parent

CARPETA_DESCARGAS = BASE_DIR / "Descargas"

CARPETA_DESCARGAS.mkdir(exist_ok=True)


# =====================================================
# DESCARGAS WINDOWS
# =====================================================

DOWNLOADS_WINDOWS = Path.home() / "Downloads"
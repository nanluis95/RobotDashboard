import os
import json
import time
import base64
import requests

from urllib.parse import quote
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


# ============================================================
# CONFIGURACION
# ============================================================

BASE_URL = "https://nce.nb.movistar.com.sv"

URL_GOOGLE_SHEETS = (
    "https://script.google.com/macros/s/"
    "AKfycbyIY5PdHTHa7eUidjHWfvbYlCmu9oI2FSPveSuYuCTEQaExo3cheT57-FD52TDSXIku7g/exec"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/154.0.0.0 Safari/537.36"
)

USUARIO = os.getenv("IMASTER_USER", "MON_MOV")
CONTRASENA = os.getenv("IMASTER_PASSWORD", "")
API_KEY = os.getenv("SHEETS_API_KEY", "")

INTERFACES_OBJETIVO = {
    "GigabitEthernet0/0/4": "GigabitEthernet0_0_4",
    "GigabitEthernet0/0/8": "GigabitEthernet0_0_8",
    "XGigabitEthernet0/0/8": "XGigabitEthernet0_0_8",
    "XGigabitEthernet0/0/9": "XGigabitEthernet0_0_9"
}

ESTADOS = {
    1: "UP", 2: "DOWN", 3: "TEST",
    "1": "UP", "2": "DOWN", "3": "TEST"
}


# ============================================================
# FUNCIONES DE AUTENTICACION (probar_login.py)
# ============================================================

def obtener_clave(session):
    respuesta = session.get(f"{BASE_URL}/unisso/pubkey", timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()

    if not datos.get("enableEncrypt"):
        raise Exception("El cifrado de iMaster no está habilitado.")

    clave = serialization.load_pem_public_key(
        datos["pubKey"].encode("utf-8")
    )
    return clave, datos["version"], datos["timeStamp"]


def cifrar_contrasena(contrasena, clave, version):
    texto = quote(contrasena, safe="-_.!~*'()")
    bloques = [texto[i:i + 270] for i in range(0, len(texto), 270)]
    cifrados = []

    for bloque in bloques:
        cifrado = clave.encrypt(
            bloque.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA384()),
                algorithm=hashes.SHA384(),
                label=None
            )
        )
        cifrados.append(base64.b64encode(cifrado).decode("ascii"))

    return "00000001".join(cifrados) + version


def iniciar_sesion_automatica(session):
    print("\n1. AUTENTICANDO EN iMASTER...")

    if not USUARIO or not CONTRASENA:
        raise Exception(
            "Faltan las credenciales IMASTER_USER o IMASTER_PASSWORD."
        )

    clave, version, timestamp = obtener_clave(session)
    password_cifrada = cifrar_contrasena(CONTRASENA, clave, version)

    nonce = "".join(format(byte, "x") for byte in os.urandom(16))

    parametros = {
        "decision": "1",

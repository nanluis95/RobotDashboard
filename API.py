
import os
import json
import base64
import requests

from urllib.parse import quote
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_der_public_key


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_URL = "https://nce.nb.movistar.com.sv"

URL_GOOGLE_SHEETS = (
    "https://script.google.com/macros/s/"
    "AKfycbyIY5PdHTHa7eUidjHWfvbYlCmu9oI2FSPveSuYuCTEQaExo3cheT57-FD52TDSXIku7g/exec"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

USUARIO = os.getenv("IMASTER_USER", "MON_MOV")
CONTRASENA = os.getenv("IMASTER_PASSWORD", "")
API_KEY = os.getenv("SHEETS_API_KEY", "")

INTERFACES_OBJETIVO = {
    "GigabitEthernet0/0/4": "GigabitEthernet0_0_4",
    "GigabitEthernet0/0/8": "GigabitEthernet0_0_8",
    "XGigabitEthernet0/0/8": "XGigabitEthernet0_0_8",
    "XGigabitEthernet0/0/9": "XGigabitEthernet0_0_9",
}

ESTADOS = {
    1: "UP",
    2: "DOWN",
    3: "TEST",
}



def obtener_clave(session):

    url = f"{BASE_URL}/unisess/v1/auth/publickey"

    respuesta = session.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        timeout=30
    )

    print("\n--- DIAGNÓSTICO DE CLAVE PÚBLICA ---")
    print("Código HTTP:", respuesta.status_code)
    print("Content-Type:", respuesta.headers.get("Content-Type"))
    print("URL final:", respuesta.url)
    print("Respuesta:", respuesta.text[:500])
    print("-----------------------------------")

    respuesta.raise_for_status()

    try:
        datos = respuesta.json()

    except ValueError:

        raise Exception(
            "iMaster no devolvió JSON al solicitar la clave pública. "
            "Revisar el diagnóstico anterior."
        )

    clave_publica = (
        datos.get("data", {}).get("publicKey")
        or datos.get("publicKey")
    )

    if not clave_publica:

        raise Exception(
            "No se encontró publicKey en la respuesta de iMaster."
        )

    return clave_publica



# ============================================================
# CIFRAR CONTRASEÑA
# ============================================================

def cifrar_contrasena(contrasena, clave_publica):

    clave_bytes = base64.b64decode(clave_publica)

    clave = load_der_public_key(clave_bytes)

    contrasena_cifrada = clave.encrypt(
        contrasena.encode("utf-8"),
        padding.PKCS1v15()
    )

    return base64.b64encode(
        contrasena_cifrada
    ).decode("utf-8")


# ============================================================
# INICIAR SESIÓN EN IMASTER
# ============================================================

def iniciar_sesion(session):

    print("Iniciando sesión en iMaster...")

    if not USUARIO:
        raise Exception(
            "No está configurado IMASTER_USER."
        )

    if not CONTRASENA:
        raise Exception(
            "No está configurado IMASTER_PASSWORD."
        )

    clave_publica = obtener_clave(session)

    password_cifrado = cifrar_contrasena(
        CONTRASENA,
        clave_publica
    )

    url = f"{BASE_URL}/unisess/v1/auth/validateUser.action"

    parametros = {
        "userName": USUARIO,
        "password": password_cifrado,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    respuesta = session.post(
        url,
        json=parametros,
        headers=headers,
        timeout=30,
        allow_redirects=False
    )

    if respuesta.status_code not in (200, 302):

        raise Exception(
            f"Error de autenticación iMaster: "
            f"HTTP {respuesta.status_code} - {respuesta.text[:500]}"
        )

    if respuesta.status_code == 302:

        redirect_url = respuesta.headers.get("Location", "")

        if not redirect_url:
            raise Exception(
                "iMaster respondió con redirección sin URL."
            )

        if "login" in redirect_url.lower():
            raise Exception(
                "iMaster rechazó las credenciales."
            )

    if not session.cookies:

        raise Exception(
            "No se recibió ninguna cookie de sesión de iMaster."
        )

    print("Sesión iniciada correctamente.")

    return True


# ============================================================
# PREPARAR SESIÓN DEL PORTAL Y OBTENER TOKEN CSRF
# ============================================================

def preparar_sesion_portal(session, ruta):

    url = f"{BASE_URL}{ruta}"

    respuesta = session.get(
        url,
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=30
    )

    respuesta.raise_for_status()

    cookies = session.cookies.get_dict()

    if "bspsession" not in cookies:

        raise Exception(
            "No se encontró la cookie bspsession."
        )

    url_csrf = f"{BASE_URL}/unisess/v1/auth/session"

    respuesta_csrf = session.get(
        url_csrf,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        timeout=30
    )

    respuesta_csrf.raise_for_status()

    datos = respuesta_csrf.json()

    csrf_token = (
        datos.get("data", {}).get("csrfToken")
        or datos.get("csrfToken")
    )

    if not csrf_token:

        raise Exception(
            "No se pudo obtener el token CSRF."
        )

    print("Token CSRF obtenido correctamente.")

    return csrf_token


# ============================================================
# CONSULTAR ROUTER POR SITE ID
# ============================================================

def consultar_router(session, identificador, csrf_token):

    url = (
        f"{BASE_URL}/controller/campus/v2/devices/list"
        "?sortField=status&pageIndex=1&pageSize=5"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRF-TOKEN": csrf_token,
    }

    parametros = {
        "keyWord": identificador,
        "searchFields": ["name"],
    }

    respuesta = session.post(
        url,
        json=parametros,
        headers=headers,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    registros = (
        datos.get("data", {}).get("list")
        or datos.get("data", {}).get("records")
        or datos.get("list")
        or []
    )

    router_encontrado = None

    for router in registros:

        nombre = (
            router.get("name")
            or router.get("deviceName")
            or ""
        )

        if nombre.strip().upper() == identificador.strip().upper():

            router_encontrado = router
            break

    if not router_encontrado:

        raise Exception(
            f"No se encontró el router {identificador} en iMaster."
        )

    id_router = (
        router_encontrado.get("id")
        or router_encontrado.get("deviceId")
    )

    device_ip = router_encontrado.get("deviceIp")

    if not id_router:

        raise Exception(
            f"No se encontró el ID interno del router {identificador}."
        )

    if not device_ip:

        raise Exception(
            f"No se encontró la IP del router {identificador}."
        )

    print(
        f"Router encontrado: {identificador} | IP: {device_ip}"
    )

    return id_router, device_ip


# ============================================================
# CONSULTAR INTERFACES Y VPN DEL ROUTER
# ============================================================

def consultar_interfaces(session, id_router, csrf_token):

    url = (
        f"{BASE_URL}/controller/campus/v2/"
        f"deviceDiagnose/{id_router}/port"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "X-CSRF-TOKEN": csrf_token,
    }

    respuesta = session.get(
        url,
        headers=headers,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    registros = (
        datos.get("data", {}).get("list")
        or datos.get("data", {}).get("ports")
        or datos.get("data")
        or []
    )

    if isinstance(registros, dict):

        registros = (
            registros.get("list")
            or registros.get("ports")
            or []
        )

    interfaces = {}

    for puerto in registros:

        nombre = (
            puerto.get("name")
            or puerto.get("portName")
            or puerto.get("interfaceName")
            or ""
        )

        if nombre not in INTERFACES_OBJETIVO:
            continue

        nombre_destino = INTERFACES_OBJETIVO[nombre]

        estado = puerto.get("runStatus")

        try:
            estado = int(estado)
        except (TypeError, ValueError):
            estado = None

        interfaces[nombre_destino] = ESTADOS.get(
            estado,
            "DESCONOCIDO"
        )

    vpn = ""

    datos_vpn = datos.get("data", {}).get("vpn")

    if isinstance(datos_vpn, dict):

        vpn = datos_vpn.get("underlay_1", "")

    elif isinstance(datos_vpn, list):

        for elemento in datos_vpn:

            if elemento.get("name") == "underlay_1":

                vpn = elemento.get("value", "")
                break

    print(
        f"Interfaces consultadas: {len(interfaces)}"
    )

    return interfaces, vpn


# ============================================================
# ENVIAR INFORMACIÓN A GOOGLE SHEETS
# ============================================================

def enviar_a_google_sheets(
    identificador,
    device_ip,
    interfaces,
    vpn,
    api_key
):

    if not api_key:

        raise Exception(
            "No está configurada SHEETS_API_KEY."
        )

    parametros = {
        "apiKey": api_key,
        "identificador": identificador,
        "deviceIp": device_ip,
        "vpn": vpn,
        "interfaces": interfaces,
    }

    respuesta = requests.post(
        URL_GOOGLE_SHEETS,
        json=parametros,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        timeout=45
    )

    respuesta.raise_for_status()

    try:

        resultado = respuesta.json()

    except ValueError:

        raise Exception(
            "Google Sheets no devolvió una respuesta JSON válida: "
            + respuesta.text[:500]
        )

    if not resultado.get("ok"):

        raise Exception(
            "Google Sheets rechazó la actualización: "
            + str(resultado)
        )

    print(
        f"Información enviada correctamente para {identificador}."
    )

    return True


# ============================================================
# OBTENER SITE IDS DESDE GITHUB ACTIONS
# ============================================================

def obtener_site_ids():

    site_ids_json = os.getenv("SITE_IDS_JSON", "")

    if not site_ids_json:

        raise Exception(
            "No se recibió SITE_IDS_JSON desde GitHub Actions."
        )

    try:

        site_ids = json.loads(site_ids_json)

    except json.JSONDecodeError as error:

        raise Exception(
            f"SITE_IDS_JSON no contiene un JSON válido: {error}"
        )

    if not isinstance(site_ids, list):

        raise Exception(
            "SITE_IDS_JSON debe contener una lista de SITE ID."
        )

    resultado = []

    for identificador in site_ids:

        if identificador is None:
            continue

        identificador = str(identificador).strip()

        if identificador and identificador not in resultado:

            resultado.append(identificador)

    if not resultado:

        raise Exception(
            "La lista de SITE ID está vacía."
        )

    return resultado


# ============================================================
# PROCESAR UN SITE ID
# ============================================================

def procesar_site(session, csrf_token, identificador):

    print(f"\nProcesando SITE ID: {identificador}")

    try:

        # 1. Buscar router en iMaster

        id_router, device_ip = consultar_router(
            session,
            identificador,
            csrf_token
        )

        # 2. Consultar interfaces y VPN

        interfaces, vpn = consultar_interfaces(
            session,
            id_router,
            csrf_token
        )

        # 3. Enviar información a Google Sheets

        enviar_a_google_sheets(
            identificador,
            device_ip,
            interfaces,
            vpn,
            API_KEY
        )

        print(
            f"RESULTADO EXITOSO: {identificador}"
        )

        return True

    except Exception as error:

        print(
            f"ERROR procesando {identificador}: {error}"
        )

        return False


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("INICIO DE VALIDACIÓN DE ROUTERS")
    print("=" * 60)

    if not API_KEY:

        raise Exception(
            "No está configurada SHEETS_API_KEY."
        )

    site_ids = obtener_site_ids()

    print(
        f"Total de SITE ID recibidos: {len(site_ids)}"
    )

    session = requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    exitosos = 0
    fallidos = 0

    try:

        # 1. Autenticación en iMaster

        iniciar_sesion(session)

        # 2. Preparar sesión y obtener CSRF

        csrf_token = preparar_sesion_portal(
            session,
            "/"
        )

        # 3. Procesar cada SITE ID

        for identificador in site_ids:

            resultado = procesar_site(
                session,
                csrf_token,
                identificador
            )

            if resultado:

                exitosos += 1

            else:

                fallidos += 1

        # 4. Resumen final

        print("\n" + "=" * 60)
        print("RESUMEN DE VALIDACIÓN")
        print("=" * 60)

        print(f"Total procesados: {len(site_ids)}")
        print(f"Exitosos: {exitosos}")
        print(f"Fallidos: {fallidos}")

        print("=" * 60)

        # Si al menos un SITE ID falla,
        # GitHub Actions marcará la ejecución como fallida.

        if fallidos > 0:

            raise Exception(
                f"Validación finalizada con {fallidos} SITE ID fallidos."
            )

        print("PROCESO FINALIZADO CORRECTAMENTE.")

    finally:

        session.close()


# ============================================================
# EJECUCIÓN DEL PROGRAMA
# ============================================================

if __name__ == "__main__":

    main()



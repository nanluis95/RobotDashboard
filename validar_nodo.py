
import os
import json
import time
import requests

from probar_login import (
    BASE_URL,
    obtener_clave,
    cifrar_contrasena
)

from probar_router import (
    USER_AGENT,
    INTERFACES_OBJETIVO,
    ESTADOS,
    preparar_sesion_portal,
    consultar_router,
    enviar_a_google_sheets
)


USUARIO = os.getenv("IMASTER_USER", "MON_MOV")
CONTRASENA = os.getenv("IMASTER_PASSWORD", "")
API_KEY = os.getenv("SHEETS_API_KEY", "")


def obtener_sites_recibidos():
    contenido = os.getenv("SITE_IDS_JSON", "")

    if not contenido:
        raise Exception("No se recibieron los SITE ID.")

    sites = json.loads(contenido)

    if not isinstance(sites, list) or not sites:
        raise Exception("La lista de SITE ID está vacía o no es válida.")

    resultado = []

    for site in sites:
        if isinstance(site, str):
            site_id = site.strip()
            codigo = ""
        elif isinstance(site, dict):
            site_id = str(site.get("siteId", "")).strip()
            codigo = str(site.get("codigo", "")).strip()
        else:
            continue

        if site_id:
            resultado.append({
                "siteId": site_id,
                "codigo": codigo
            })

    if not resultado:
        raise Exception("No se encontraron SITE ID válidos.")

    # Evitar consultas duplicadas
    unicos = {}
    for site in resultado:
        unicos[site["siteId"].upper()] = site

    return list(unicos.values())


def iniciar_sesion_automatica(session):
    print("\nAUTENTICANDO EN iMASTER...")

    if not USUARIO or not CONTRASENA:
        raise Exception("Faltan las credenciales de iMaster.")

    clave, version, timestamp = obtener_clave(session)

    password_cifrada = cifrar_contrasena(
        CONTRASENA,
        clave,
        version
    )

    nonce = "".join(
        format(byte, "x") for byte in os.urandom(16)
    )

    parametros = {
        "decision": "1",
        "service": "/unisess/v1/auth?service=%2F",
        "timeStamp": timestamp,
        "nonce": nonce
    }

    payload = {
        "multiRegionName": "",
        "organizationName": "",
        "username": USUARIO,
        "password": password_cifrada,
        "verifycode": ""
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/",
        "User-Agent": USER_AGENT
    }

    respuesta = session.post(
        f"{BASE_URL}/unisso/v3/validateUser.action",
        params=parametros,
        json=payload,
        headers=headers,
        timeout=45
    )

    respuesta.raise_for_status()
    datos = respuesta.json()

    if datos.get("errorCode") is not None:
        raise Exception(
            "Autenticación rechazada: "
            + str(datos.get("errorMsg"))
        )

    if datos.get("verifyCodeCreate"):
        raise Exception("iMaster solicita CAPTCHA.")

    ruta = datos.get("redirectURL")

    if not ruta or not ruta.startswith("/"):
        raise Exception("No se recibió una ruta válida de iMaster.")

    print("Autenticación correcta.")

    return ruta


def consultar_interfaces_detalladas(
    session,
    id_router,
    csrf_token
):
    url = (
        f"{BASE_URL}/controller/campus/v2/"
        f"deviceDiagnose/{id_router}/port"
    )

    headers = {
        "Accept": "application/json",
        "Referer": BASE_URL + "/",
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
        "http_x_requested_with": "XMLHttpRequest",
        "x-uni-crsf-token": csrf_token,
        "roarand": csrf_token
    }

    respuesta = session.get(
        url,
        headers=headers,
        timeout=45
    )

    respuesta.raise_for_status()

    datos = respuesta.json()
    lista = datos.get("data", [])

    if not isinstance(lista, list):
        raise Exception("Formato de interfaces no válido.")

    resultados = {}
    filas = []
    interfaz_underlay = None

    for nombre, clave in INTERFACES_OBJETIVO.items():

        interfaz = next(
            (
                item for item in lista
                if item.get("name") == nombre
            ),
            None
        )

        if interfaz is None:
            estado = "SIN DATOS"
            ip = ""
            vpn = ""
        else:
            codigo_estado = interfaz.get("runStatus")
            estado = ESTADOS.get(codigo_estado, "DESCONOCIDO")
            ip = interfaz.get("ipAddr") or ""
            vpn = interfaz.get("vpnInstanceName") or ""

            if vpn == "underlay_1":
                interfaz_underlay = interfaz

            if estado == "UP":
                filas.append({
                    "interfaz": nombre,
                    "estado": estado,
                    "ip": ip,
                    "vpn": vpn
                })

        resultados[clave] = estado

    vpn_general = ""

    if interfaz_underlay:
        vpn_general = (
            interfaz_underlay.get("vpnInstanceName") or ""
        )

    return resultados, vpn_general, filas


def procesar_site(session, csrf_token, site):
    site_id = site["siteId"]
    codigo = site["codigo"]

    print("\nCONSULTANDO SITE ID:", site_id)

    id_router, device_ip = consultar_router(
        session,
        site_id,
        csrf_token
    )

    interfaces, vpn_general, filas_up = (
        consultar_interfaces_detalladas(
            session,
            id_router,
            csrf_token
        )
    )

    # Actualizar la hoja con los resultados
    enviar_a_google_sheets(
        site_id,
        device_ip,
        interfaces,
        vpn_general,
        API_KEY
    )

    # Una fila por cada interfaz UP
    if filas_up:
        filas = []

        for interfaz in filas_up:
            filas.append({
                "siteId": site_id,
                "codigo": codigo,
                "interfaz": interfaz["interfaz"],
                "estado": interfaz["estado"],
                "ip": interfaz["ip"] or device_ip,
                "vpn": interfaz["vpn"] or vpn_general
            })

        return filas

    # Si no hay ninguna interfaz UP, conservar el equipo
    return [{
        "siteId": site_id,
        "codigo": codigo,
        "interfaz": "SIN INTERFAZ UP",
        "estado": "SIN INTERFAZ UP",
        "ip": device_ip,
        "vpn": vpn_general
    }]


def main():
    if not API_KEY:
        raise Exception("Falta SHEETS_API_KEY.")

    sites = obtener_sites_recibidos()

    session = requests.Session()

    resultados = []
    fallidos = []

    try:
        print("=" * 55)
        print("VALIDACION DE NODO - iMASTER")
        print("=" * 55)

        print("SITE ID recibidos:", len(sites))

        ruta = iniciar_sesion_automatica(session)

        csrf_token = preparar_sesion_portal(
            session,
            ruta
        )

        for numero, site in enumerate(sites, start=1):

            print("\nPROGRESO:", numero, "DE", len(sites))

            try:
                filas = procesar_site(
                    session,
                    csrf_token,
                    site
                )

                resultados.extend(filas)

            except Exception as error:
                fallidos.append({
                    "siteId": site["siteId"],
                    "error": str(error)
                })

                print(
                    "ERROR EN SITE ID:",
                    site["siteId"],
                    str(error)
                )

            time.sleep(1)

        salida = {
            "ok": len(fallidos) == 0,
            "totalSites": len(sites),
            "sitesFallidos": len(fallidos),
            "resultados": resultados,
            "fallidos": fallidos
        }

        print("\n========== RESULTADO JSON ==========")
        print("RESULTADO_JSON=" + json.dumps(
            salida,
            ensure_ascii=False
        ))

        print("\nVALIDACION FINALIZADA.")

        if fallidos:
            raise Exception(
                "Algunos SITE ID no pudieron consultarse."
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()

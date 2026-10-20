            continue

        if site_id:
            resultado.append({"siteId": site_id, "codigo": codigo})

    if not resultado:
        raise Exception("No se encontraron SITE ID válidos.")

    # Eliminar duplicados sin alterar el orden recibido.
    unicos = {}
    for site in resultado:
        clave = site["siteId"].upper()
        if clave not in unicos:
            unicos[clave] = site

    return list(unicos.values())


# ============================================================
# PROCESAR UN SITE ID
# ============================================================

def procesar_site(session, csrf_token, site):
    site_id = site["siteId"]
    codigo = site["codigo"]

    print("\nCONSULTANDO SITE ID:", site_id)

    id_router, device_ip = consultar_router(
        session, site_id, csrf_token
    )

    interfaces, vpn_general, filas_up = (
        consultar_interfaces_detalladas(
            session, id_router, csrf_token
        )
    )

    # Actualiza en Sheets los estados de las cuatro interfaces.
    enviar_a_google_sheets(
        site_id, device_ip, interfaces, vpn_general, API_KEY
    )

    # Devuelve una fila por cada interfaz UP.
    if filas_up:
        return [
            {
                "siteId": site_id,
                "codigo": codigo,
                "interfaz": interfaz["interfaz"],
                "estado": interfaz["estado"],
                "ip": interfaz["ip"] or device_ip,
                "vpn": interfaz["vpn"] or vpn_general
            }
            for interfaz in filas_up
        ]

    return [{
        "siteId": site_id,
        "codigo": codigo,
        "interfaz": "SIN INTERFAZ UP",
        "estado": "SIN INTERFAZ UP",
        "ip": device_ip,
        "vpn": vpn_general
    }]


# ============================================================
# EJECUCION PRINCIPAL
# ============================================================

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
        csrf_token = preparar_sesion_portal(session, ruta)

        for numero, site in enumerate(sites, start=1):
            print("\nPROGRESO:", numero, "DE", len(sites))

            try:
                filas = procesar_site(session, csrf_token, site)
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
        print(
            "RESULTADO_JSON="
            + json.dumps(salida, ensure_ascii=False)
        )
        print("\nVALIDACION FINALIZADA.")

        if fallidos:
            raise Exception(
                "Algunos SITE ID no pudieron consultarse."
            )

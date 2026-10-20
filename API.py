    print('Token CSRF obtenido correctamente.')
    return csrf_token

def consultar_router(session, identificador, csrf_token):
    print('\n3. CONSULTANDO ROUTER:', identificador)
    url = f'{BASE_URL}/controller/campus/v2/devices/list?sortField=status&pageIndex=1&pageSize=5'
    payload = {'keyWord': identificador, 'status': [0, 1, 2, 3], 'deviceGrpTypeList': ['AC', 'AP', 'AR', 'FW', 'LSW'], 'deviceRoles': [], 'managementMode': [0], 'screenNo': 'device', 'searchFields': ['name'], 'tenantIdList': [], 'tenantType': 'none'}
    headers = {'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json', 'Origin': BASE_URL, 'Referer': BASE_URL + '/', 'User-Agent': USER_AGENT, 'Accept-Language': 'es-ES', 'X-Requested-With': 'XMLHttpRequest', 'http_x_requested_with': 'XMLHttpRequest', 'x-uni-crsf-token': csrf_token, 'roarand': csrf_token, 'x-non-renewal-session': 'true'}
    respuesta = session.post(url, json=payload, headers=headers, timeout=45)
    print('HTTP de consulta:', respuesta.status_code)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not datos.get('data'):
        raise Exception('No se encontró el router: ' + identificador)
    router = next((item for item in datos['data'] if str(item.get('name', '')).strip().upper() == identificador.upper()), None)
    if router is None:
        raise Exception('iMaster no devolvió una coincidencia exacta para: ' + identificador)
    id_router = router.get('id')
    if not id_router:
        raise Exception('No se encontró el identificador interno del router.')
    device_ip = router.get('deviceIp') or ''
    print('Router encontrado:', router.get('name'))
    print('IP del dispositivo:', device_ip)
    return (id_router, device_ip)

def consultar_interfaces(session, id_router, csrf_token):
    print('\n4. CONSULTANDO INTERFACES...')
    url = f'{BASE_URL}/controller/campus/v2/deviceDiagnose/{id_router}/port'
    headers = {'Accept': 'application/json', 'Referer': BASE_URL + '/', 'User-Agent': USER_AGENT, 'X-Requested-With': 'XMLHttpRequest', 'http_x_requested_with': 'XMLHttpRequest', 'x-uni-crsf-token': csrf_token, 'roarand': csrf_token}
    respuesta = session.get(url, headers=headers, timeout=45)
    print('HTTP consulta de puertos:', respuesta.status_code)
    respuesta.raise_for_status()
    datos = respuesta.json()
    lista_interfaces = datos.get('data', [])
    if not isinstance(lista_interfaces, list):
        raise Exception('La respuesta de interfaces no tiene el formato esperado.')
    resultados = {}
    interfaz_underlay = None
    for nombre, clave in INTERFACES_OBJETIVO.items():
        interfaz = next((item for item in lista_interfaces if item.get('name') == nombre), None)
        if interfaz is None:
            estado = 'SIN DATOS'
            ip = ''
            vpn = ''
        else:
            codigo_estado = interfaz.get('runStatus')
            estado = ESTADOS.get(codigo_estado, 'DESCONOCIDO')
            ip = interfaz.get('ipAddr') or ''
            vpn = interfaz.get('vpnInstanceName') or ''
            if vpn == 'underlay_1':
                interfaz_underlay = interfaz
        resultados[clave] = estado
        print(nombre, ':', estado)
    vpn_general = ''
    if interfaz_underlay:
        vpn_general = interfaz_underlay.get('vpnInstanceName') or ''
    print('VPN general:', vpn_general or 'SIN VPN')
    return (resultados, vpn_general)

def enviar_a_google_sheets(identificador, device_ip, interfaces, vpn, api_key):
    print('\n5. ENVIANDO INFORMACION A GOOGLE SHEETS...')
    datos = {'apiKey': api_key, 'identificador': identificador, 'deviceIp': device_ip, 'vpn': vpn, 'interfaces': interfaces}
    respuesta = requests.post(URL_GOOGLE_SHEETS, json=datos, timeout=45)
    respuesta.raise_for_status()
    resultado = respuesta.json()
    print('\nRESPUESTA DE GOOGLE SHEETS:')
    print(resultado)
    if not resultado.get('ok'):
        raise Exception('Google Sheets rechazó la actualización: ' + str(resultado.get('mensaje')))
    print('\nACTUALIZACION COMPLETADA CORRECTAMENTE.')

def obtener_site_ids():
    valor = os.getenv("SITE_IDS_JSON", "").strip()
    if not valor:
        raise Exception("No se recibió SITE_IDS_JSON desde GitHub Actions.")
    try:
        ids = json.loads(valor)
    except json.JSONDecodeError as error:
        raise Exception(f"SITE_IDS_JSON no contiene JSON válido: {error}")
    if not isinstance(ids, list) or not ids:
        raise Exception("SITE_IDS_JSON debe ser una lista no vacía.")

    normalizados = []
    for item in ids:
        site_id = str(item).strip()
        if site_id and site_id not in normalizados:
            normalizados.append(site_id)
    if not normalizados:
        raise Exception("No hay SITE ID válidos para procesar.")
    return normalizados


def procesar_site(session, csrf_token, identificador):
    print("\\n" + "=" * 60)
    print("PROCESANDO SITE ID:", identificador)
    print("=" * 60)
    id_router, device_ip = consultar_router(session, identificador, csrf_token)
    interfaces, vpn = consultar_interfaces(session, id_router, csrf_token)
    enviar_a_google_sheets(identificador, device_ip, interfaces, vpn, API_KEY)


def main():
    if not API_KEY:
        raise Exception("Falta el secreto SHEETS_API_KEY.")
    site_ids = obtener_site_ids()
    print("SITE ID recibidos:", len(site_ids))
    print("Usuario iMaster:", USUARIO)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        ruta = iniciar_sesion(session)
        csrf_token = preparar_sesion_portal(session, ruta)
        exitosos, fallidos = [], []

        for identificador in site_ids:
            try:
                procesar_site(session, csrf_token, identificador)
                exitosos.append(identificador)
            except Exception as error:
                print(f"ERROR procesando {identificador}: {error}")
                fallidos.append({"site_id": identificador, "error": str(error)})

        print("\\nRESUMEN DE VALIDACIÓN")
        print("Correctos:", len(exitosos), exitosos)
        print("Fallidos:", len(fallidos), fallidos)
        if fallidos:
            raise Exception(f"Proceso finalizado con {len(fallidos)} SITE ID fallidos.")

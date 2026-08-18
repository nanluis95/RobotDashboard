from datetime import datetime
import base64
import requests
URL_API = "https://script.google.com/macros/s/AKfycbzZbj4K1CPhsLSsgVIULMc_t_0A-tC_lDCWgMyz-S8sTHJzGdvW3r6Uos5NoGk66ZOP/exec"

from playwright.sync_api import TimeoutError

from config import CARPETA_DESCARGAS

def subir_excel_a_drive(ruta_archivo):

    print("====================================")
    print("GUARDANDO EXCEL ORIGINAL EN DRIVE")
    print("====================================")

    ruta_archivo = str(ruta_archivo)

    print(f"Archivo a subir: {ruta_archivo}")

    # Leer archivo Excel
    with open(ruta_archivo, "rb") as archivo:

        contenido = archivo.read()

    # Convertir a Base64
    archivo_base64 = base64.b64encode(
        contenido
    ).decode("utf-8")

    # Nombre original del archivo
    nombre_archivo = ruta_archivo.split("/")[-1]

    datos = {

        "tipo": "excel",

        "nombre": nombre_archivo,

        "archivo": archivo_base64

    }

    print("Enviando archivo a Google Drive...")

    respuesta = requests.post(

        URL_API,

        json=datos,

        timeout=180

    )

    print(
        "Código respuesta Apps Script:",
        respuesta.status_code
    )

    print(
        "Respuesta Apps Script:",
        respuesta.text
    )

    if respuesta.status_code != 200:

        raise Exception(
            "No fue posible guardar el Excel en Drive."
        )

    resultado = respuesta.json()

    if not resultado.get("ok"):

        raise Exception(
            "Apps Script rechazó el archivo: " +
            str(resultado)
        )

    print("Excel guardado correctamente en Drive.")

    print(
        "Archivo:",
        resultado.get("nombre")
    )

    print(
        "URL:",
        resultado.get("url")
    )

    print("====================================")

    return resultado

def abrir_reporte_online(page):

    print("====================================")
    print("REPORTE ONLINE")
    print("====================================")

    print("Abriendo Monitoring...")
    page.get_by_text("Monitoring", exact=True).click()
    page.wait_for_load_state("networkidle")

    print("Abriendo Agile Report...")
    page.get_by_role(
        "link",
        name="Agile Report Add to Favorites"
    ).click()

    page.wait_for_load_state("networkidle")

    print("Abriendo Online Puertos...")

    page.get_by_text(
    "Online puertos",
    exact=True
    ).first.click()

    page.wait_for_timeout(2000)

    print("Actualizando reporte...")
    page.locator("#navbar_refresh > svg").click()

    print("Esperando 10 segundos...")
    page.wait_for_timeout(10000)

    ruta = exportar_reporte(page)

    print("====================================")
    print("DESCARGA COMPLETADA")
    print(ruta)
    print("====================================")

    return ruta


def exportar_reporte(page):

    print("Abriendo menú Export...")

    page.locator("#navbar_export > svg").click()

    try:

        with page.expect_download(timeout=180000) as download_info:

            print("Presionando Export...")

            page.get_by_role(
                "button",
                name="Export"
            ).click()

        print("Descarga detectada.")

        download = download_info.value

        nombre = datetime.now().strftime("%d%m %H%M") + ".xlsx"

        destino = CARPETA_DESCARGAS / nombre

        print(f"Guardando en: {destino}")

        download.save_as(destino)

print("Archivo guardado correctamente.")

# =====================================================
# GUARDAR COPIA DEL EXCEL ORIGINAL EN GOOGLE DRIVE
# =====================================================

subir_excel_a_drive(destino)

        # Intentar cerrar la ventana de confirmación
        try:

            print("Cerrando ventana de confirmación...")

            page.locator("#eui_icon_10008 #rectangle").click(timeout=3000)

            page.wait_for_timeout(1000)

        except Exception as e:

            print("No fue posible cerrar la ventana:", e)

        return destino

    except Exception as e:

        print("ERROR DURANTE LA EXPORTACIÓN")
        print(e)

        raise

from datetime import datetime

from playwright.sync_api import TimeoutError

from config import CARPETA_DESCARGAS


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
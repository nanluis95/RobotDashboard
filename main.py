from login import iniciar_navegador
from online import abrir_reporte_online
from procesar_online import procesar_excel
from sheets import enviar_google_sheet


def main():

    playwright, browser, context, page = iniciar_navegador()

    try:

        # Descargar reporte
        archivo_descargado = abrir_reporte_online(page)

        # Procesar reporte
        archivo_filtrado = procesar_excel(archivo_descargado)

        # Actualizar Google Sheet
        enviar_google_sheet(archivo_filtrado)

        print("")
        print("====================================")
        print("PROCESO FINALIZADO CORRECTAMENTE")
        print("====================================")

    except Exception as e:

        print("")
        print("====================================")
        print("ERROR EN LA EJECUCIÓN")
        print("====================================")
        print(e)

        raise

    finally:

        context.close()
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    main()
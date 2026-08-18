import pandas as pd
import requests


# URL de la Web App
URL_API = "https://script.google.com/macros/s/AKfycbzZbj4K1CPhsLSsgVIULMc_t_0A-tC_lDCWgMyz-S8sTHJzGdvW3r6Uos5NoGk66ZOP/exec"


def enviar_google_sheet(archivo_filtrado):

    print("====================================")
    print("ACTUALIZANDO GOOGLE SHEET")
    print("====================================")

    # Asegurarse de trabajar con el archivo que acaba
    # de generar procesar_online.py
    archivo_filtrado = str(archivo_filtrado)

    print(f"Archivo recibido: {archivo_filtrado}")

    # Leer el archivo filtrado recién generado
    df = pd.read_excel(archivo_filtrado)

    if "Sitio" not in df.columns:
        raise Exception("No existe la columna 'Sitio'.")

    # Obtener únicamente los códigos únicos
    codigos = (
        df["Sitio"]
        .dropna()
        .astype(int)
        .astype(str)
        .unique()
        .tolist()
    )

    print(f"Escuelas Online encontradas: {len(codigos)}")

    datos = {
        "codigos": codigos
    }

    respuesta = requests.post(
        URL_API,
        json=datos,
        timeout=120
    )

    print("====================================")
    print("RESPUESTA APPS SCRIPT")
    print("====================================")
    print(respuesta.text)
    print("====================================")

    return respuesta.text
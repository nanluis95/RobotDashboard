import requests

URL_API = "https://script.google.com/macros/s/AKfycbzZbj4K1CPhsLSsgVIULMc_t_0A-tC_lDCWgMyz-S8sTHJzGdvW3r6Uos5NoGk66ZOP/exec"


def probar_api():

    datos = {
        "mensaje": "Hola desde Python",
        "robot": "Dashboard Escuelas",
        "version": "1.0"
    }

    try:

        respuesta = requests.post(URL_API, json=datos, timeout=30)

        print("====================================")
        print("RESPUESTA DEL SERVIDOR")
        print("====================================")
        print(respuesta.text)
        print("====================================")

    except Exception as e:

        print("ERROR AL CONECTAR")
        print(e)


if __name__ == "__main__":
    probar_api()
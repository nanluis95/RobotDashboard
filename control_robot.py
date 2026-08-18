import subprocess
import os
import time
import requests


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL_API = "https://script.google.com/macros/s/AKfycbzZbj4K1CPhsLSsgVIULMc_t_0A-tC_lDCWgMyz-S8sTHJzGdvW3r6Uos5NoGk66ZOP/exec"

RUTA_ROBOT = r"C:\RobotDashboard\ejecutar_robot.bat"

INTERVALO = 5


# ============================================================
# CONSULTAR CONTROL DEL ROBOT
# ============================================================

def consultar_control():

    try:

        respuesta = requests.get(
            URL_API,
            timeout=30
        )

        respuesta.raise_for_status()

        return respuesta.json()

    except Exception as e:

        print("ERROR consultando CONTROL_ROBOT:")
        print(e)

        return None


# ============================================================
# CAMBIAR ESTADO DEL ROBOT
# ============================================================

def cambiar_estado(accion):

    try:

        respuesta = requests.get(
            URL_API,
            params={
                "accion": accion
            },
            timeout=30
        )

        respuesta.raise_for_status()

        print("Estado actualizado:", accion)

        return True

    except Exception as e:

        print("ERROR actualizando estado:")
        print(e)

        return False


# ============================================================
# EJECUTAR ROBOT
# ============================================================

def ejecutar_robot():

    if not os.path.exists(RUTA_ROBOT):

        print("ERROR: No se encontró ejecutar_robot.bat")

        return False

    try:

        print("====================================")
        print("INICIANDO ROBOT")
        print("====================================")

        proceso = subprocess.Popen(
            [RUTA_ROBOT],
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        print("Robot iniciado correctamente.")

        return proceso

    except Exception as e:

        print("ERROR al iniciar el robot:")
        print(e)

        return False


# ============================================================
# CONTROL PRINCIPAL
# ============================================================

def main():

    print("====================================")
    print(" CONTROLADOR DEL ROBOT")
    print("====================================")

    print("Esperando solicitudes desde el Dashboard...")
    print("")

    while True:

        datos = consultar_control()

        if datos:

            estado = datos.get("estado", "")
            solicitud = datos.get("solicitud", "")

            print(
                f"Estado: {estado} | "
                f"Solicitud: {solicitud}"
            )

            # --------------------------------------------
            # EL DASHBOARD SOLICITÓ EJECUTAR EL ROBOT
            # --------------------------------------------

            if solicitud.upper() == "EJECUTAR":

                print("")
                print("Solicitud recibida desde el Dashboard.")

                # Marcar como ejecutando
                cambiar_estado("ejecutando")

                # Ejecutar robot
                proceso = ejecutar_robot()

                if proceso:

                    print("Esperando finalización del robot...")

                    proceso.wait()

                    if proceso.returncode == 0:

                        print("")
                        print("====================================")
                        print("ROBOT FINALIZADO CORRECTAMENTE")
                        print("====================================")

                        cambiar_estado("finalizado")

                    else:

                        print("")
                        print("====================================")
                        print("ROBOT FINALIZÓ CON ERROR")
                        print("====================================")

                        cambiar_estado("error")

                else:

                    cambiar_estado("error")

        time.sleep(INTERVALO)


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":
    main()
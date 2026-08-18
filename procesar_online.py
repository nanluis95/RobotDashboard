import pandas as pd
from pathlib import Path


def procesar_excel(ruta_archivo):

    print("====================================")
    print("PROCESANDO REPORTE ONLINE")
    print("====================================")

    print(f"Leyendo: {ruta_archivo}")

    # Leer encabezados desde la fila 10
    df = pd.read_excel(
        ruta_archivo,
        header=9
    )

    print(f"Registros originales: {len(df)}")

    # Interfaces válidas
    interfaces = [
        "GigabitEthernet0/0/4",
        "GigabitEthernet0/0/8"
    ]

    # Filtrar únicamente las interfaces requeridas
    df = df[df["interface name"].isin(interfaces)].copy()

    print(f"Registros después del filtro: {len(df)}")

    # =====================================================
    # Crear columna Sitio
    # =====================================================

    df["Sitio"] = (
        df["device name"]
        .astype(str)
        .str.extract(r"^(\d+)", expand=False)
    )

    registros_antes = len(df)

    # Eliminar registros sin código numérico
    df = df[df["Sitio"].notna()].copy()

    registros_despues = len(df)

    print(
        f"Registros eliminados por no tener código de sitio: "
        f"{registros_antes - registros_despues}"
    )

    # Convertir la columna Sitio a número
    df["Sitio"] = df["Sitio"].astype(int)

    # =====================================================
    # Reordenar columnas
    # =====================================================

    df = df[
        [
            "Date time",
            "site name",
            "device name",
            "interface name",
            "interface sending rate(bps)",
            "interface receiving rate(bps)",
            "Sitio"
        ]
    ]

    # =====================================================
    # Guardar archivo
    # =====================================================

    ruta_archivo = Path(ruta_archivo)

    ruta_salida = (
        ruta_archivo.parent /
        f"{ruta_archivo.stem}_filtrado.xlsx"
    )

    df.to_excel(
        ruta_salida,
        index=False
    )

    print("")
    print("Archivo generado correctamente:")
    print(ruta_salida)

    # Devolver la ruta del archivo filtrado
    return ruta_salida
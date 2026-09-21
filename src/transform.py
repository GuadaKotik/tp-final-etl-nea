"""
TRANSFORM — De datos crudos a un dataset analítico
====================================================

Este es el corazón del TP. El Extract ya trae los datos y el Load ya
sabe guardarlos: lo que hace este módulo es convertir lo crudo en algo
analizable.

El recorrido es:

    formato ANCHO (como llega de la API)
        fecha        China   Brasil   ...   __TOTAL__
        1993-01-01    12.3     45.6   ...      120.0

              |  ancho_a_largo()
              v

    formato LARGO / "tidy" (una fila por observación)
        anio  provincia  destino  valor_musd  total_provincia_musd
        1993  Chaco      China          12.3                 120.0
        1993  Chaco      Brasil         45.6                 120.0

              |  + columnas derivadas
              |  + join con rubros
              v

    dataset final de 13 columnas
"""

import logging

import config

# Nombre reservado que usa extract.py para la serie del total provincial
CLAVE_TOTAL = "__TOTAL__"

# Orden final de las columnas del CSV. Es un contrato: el Load lo respeta
# y la consigna del TP lo exige. NO se modifica.
COLUMNAS = [
    "anio",
    "provincia",
    "destino",
    "region_destino",
    "valor_musd",
    "total_provincia_musd",
    "participacion_pct",
    "var_interanual_pct",
    "decada",
    "ranking_destino",
    "es_top3",
    "rubro_principal",
    "pp_participacion_pct",
]


# ======================================================================
# 1) ANCHO -> LARGO
# ======================================================================
def extraer_anio(fecha_texto):
    """Convierte '1993-01-01' en el entero 1993."""
    return int(fecha_texto[:4])


def ancho_a_largo(paquetes_destino):
    """CONTRATO: recibe los paquetes crudos de destino; devuelve una lista
    de dicts con una fila por (año, provincia, destino).

    Cada dict debe tener exactamente estas 5 claves:
        anio                  (int)
        provincia             (str)
        destino               (str)
        valor_musd            (float, redondeado a 2 decimales)
        total_provincia_musd  (float, redondeado a 2 decimales)
    """
    filas = []

    for paquete in paquetes_destino:
        provincia = paquete["provincia"]
        columnas = paquete["orden_columnas"]
        posicion_total = columnas.index(CLAVE_TOTAL)

        for fila_cruda in paquete["data"]:
            fecha = fila_cruda[0]
            valores = fila_cruda[1:]
            anio = extraer_anio(fecha)
            total = valores[posicion_total]

            for posicion, nombre in enumerate(columnas):
                if nombre == CLAVE_TOTAL:
                    continue  # el total no es un destino, no genera fila

                valor = valores[posicion]
                if valor is None or total is None:
                    continue  # dato faltante: se saltea la observación

                filas.append({
                    "anio": anio,
                    "provincia": provincia,
                    "destino": nombre,
                    "valor_musd": round(valor, 2),
                    "total_provincia_musd": round(total, 2),
                })

    logging.info("  ancho_a_largo: %s filas", len(filas))
    return filas


# ======================================================================
# 2) COLUMNAS DERIVADAS SIMPLES
# ======================================================================
def clasificar_region(destino):
    """Devuelve la región geoeconómica de un país de destino.

    Ejemplos:  'Brasil' -> 'Mercosur'   |   'China' -> 'Asia'

    Si el país no está mapeado en config.REGIONES, devuelve
    config.REGION_POR_DEFECTO en lugar de romper.
    """
    return config.REGIONES.get(destino, config.REGION_POR_DEFECTO)


def calcular_decada(anio):
    """Devuelve la década de un año como texto.

    Ejemplos:  1993 -> '1990s'   |   2024 -> '2020s'
    """
    inicio_decada = (anio // 10) * 10
    return f"{inicio_decada}s"


def calcular_participacion(valor, total):
    """Qué porcentaje del total exportado representa este destino.

    Ejemplo:  valor=110.93, total=401.74  ->  27.61

    Devuelve None si el total es cero o None: dividir por cero rompe el
    programa, y un dato ausente es más honesto que un cero inventado.
    """
    if total is None or total == 0:
        return None
    return round(valor / total * 100, 2)


def agregar_derivadas_simples(filas):
    """Agrega region_destino, decada y participacion_pct a cada fila.

    CONTRATO: modifica y devuelve la misma lista de filas.
    """
    for fila in filas:
        fila["region_destino"] = clasificar_region(fila["destino"])
        fila["decada"] = calcular_decada(fila["anio"])
        fila["participacion_pct"] = calcular_participacion(
            fila["valor_musd"], fila["total_provincia_musd"]
        )
    return filas


# ======================================================================
# 3) VARIACIÓN INTERANUAL
# ======================================================================
def calcular_variacion(actual, anterior):
    """Variación porcentual entre dos valores.

    Fórmula:  (actual - anterior) / anterior * 100
    Ejemplo:  actual=110.93, anterior=75.79  ->  46.36

    Devuelve None si 'anterior' es None o cero.
    """
    if anterior is None or anterior == 0:
        return None
    return round((actual - anterior) / anterior * 100, 2)


def agregar_variacion_interanual(filas):
    """Agrega var_interanual_pct comparando cada fila con el año previo
    del MISMO destino y la MISMA provincia.

    CONTRATO: modifica y devuelve la misma lista de filas. La primera
    observación de cada serie queda con None (no hay año anterior).
    """
    # 1) Índice de búsqueda: (provincia, destino, anio) -> valor_musd
    indice = {
        (fila["provincia"], fila["destino"], fila["anio"]): fila["valor_musd"]
        for fila in filas
    }

    # 2) Para cada fila, buscamos el valor del año anterior en el índice
    for fila in filas:
        clave_anterior = (fila["provincia"], fila["destino"], fila["anio"] - 1)
        valor_anterior = indice.get(clave_anterior)
        fila["var_interanual_pct"] = calcular_variacion(
            fila["valor_musd"], valor_anterior
        )

    return filas


# ======================================================================
# 4) RANKING DE DESTINOS
# ======================================================================
def agregar_ranking(filas, top_n=None):
    """Agrega ranking_destino (1 = el que más exportó) y es_top3 (bool).

    El ranking se calcula DENTRO de cada grupo (provincia, año): ser el
    destino #1 de Chaco en 2024 no dice nada sobre Misiones en 1998.

    CONTRATO: modifica y devuelve la misma lista de filas.
    """
    if top_n is None:
        top_n = config.TOP_N

    # 1) Agrupar las filas por (provincia, anio)
    grupos = {}
    for fila in filas:
        clave = (fila["provincia"], fila["anio"])
        grupos.setdefault(clave, []).append(fila)

    # 2) Ordenar cada grupo de mayor a menor valor_musd y asignar ranking
    for grupo in grupos.values():
        grupo_ordenado = sorted(grupo, key=lambda f: f["valor_musd"], reverse=True)
        for posicion, fila in enumerate(grupo_ordenado, start=1):
            fila["ranking_destino"] = posicion
            fila["es_top3"] = posicion <= top_n

    return filas


# ======================================================================
# 5) JOIN CON LOS RUBROS
# ======================================================================
def construir_indice_rubros(paquetes_rubro):
    """CONTRATO: recibe los paquetes crudos de rubro; devuelve un índice

        {(provincia, anio): {"rubro_principal": str,
                             "pp_participacion_pct": float}}

    Para cada (provincia, año):
      - rubro_principal      = el rubro con MAYOR valor ese año.
      - pp_participacion_pct = qué % del total de ese año representan los
                               'Productos primarios', redondeado a 2 dec.
    """
    indice = {}

    for paquete in paquetes_rubro:
        provincia = paquete["provincia"]
        columnas = paquete["orden_columnas"]

        for fila_cruda in paquete["data"]:
            fecha = fila_cruda[0]
            valores = fila_cruda[1:]
            anio = extraer_anio(fecha)

            # Diccionario {nombre_rubro: valor} para este (provincia, año),
            # descartando los rubros sin dato.
            valores_por_rubro = {
                nombre: valor
                for nombre, valor in zip(columnas, valores)
                if valor is not None
            }
            if not valores_por_rubro:
                continue

            rubro_principal = max(valores_por_rubro, key=valores_por_rubro.get)
            total_anio = sum(valores_por_rubro.values())
            valor_pp = valores_por_rubro.get("Productos primarios", 0)

            pp_participacion_pct = (
                round(valor_pp / total_anio * 100, 2) if total_anio else None
            )

            indice[(provincia, anio)] = {
                "rubro_principal": rubro_principal,
                "pp_participacion_pct": pp_participacion_pct,
            }

    logging.info("  índice de rubros: %s claves (provincia, año)", len(indice))
    return indice


def unir_con_rubros(filas, indice_rubros):
    """Join por clave compuesta (provincia, anio).

    Es un LEFT JOIN: si una combinación no está en el índice, las dos
    columnas quedan en None, pero LA FILA NO SE PIERDE.

    CONTRATO: modifica y devuelve la misma lista de filas.
    """
    for fila in filas:
        clave = (fila["provincia"], fila["anio"])
        datos_rubro = indice_rubros.get(clave)

        if datos_rubro is None:
            fila["rubro_principal"] = None
            fila["pp_participacion_pct"] = None
        else:
            fila["rubro_principal"] = datos_rubro["rubro_principal"]
            fila["pp_participacion_pct"] = datos_rubro["pp_participacion_pct"]

    return filas


# ======================================================================
# ORQUESTACIÓN DEL TRANSFORM
# ======================================================================
def ordenar_columnas(filas):
    """Devuelve las filas con las claves en el orden definido por COLUMNAS."""
    return [{columna: fila.get(columna) for columna in COLUMNAS} for fila in filas]


def transformar(datos_crudos):
    """CONTRATO: recibe {'destino': [...], 'rubro': [...]} crudos;
    devuelve la lista de filas finales, ordenadas y con las 13 columnas.
    """
    logging.info("TRANSFORM: iniciando")

    filas = ancho_a_largo(datos_crudos["destino"])
    filas = agregar_derivadas_simples(filas)
    filas = agregar_variacion_interanual(filas)
    filas = agregar_ranking(filas)

    indice = construir_indice_rubros(datos_crudos["rubro"])
    filas = unir_con_rubros(filas, indice)

    filas.sort(key=lambda f: (f["provincia"], f["anio"], f["ranking_destino"]))
    filas = ordenar_columnas(filas)

    logging.info("TRANSFORM OK: %s filas x %s columnas", len(filas), len(COLUMNAS))
    return filas

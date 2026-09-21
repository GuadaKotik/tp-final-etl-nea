"""
LOAD — Quality checks y persistencia
=====================================

Dos responsabilidades, en este orden:

  1. CHEQUEAR: validar el dataset antes de publicarlo. Si algo crítico
     falla, cortamos: mejor no entregar nada que entregar un reporte roto.
  2. GUARDAR: escribir el CSV (para personas), el resumen JSON (para
     programas) y el log (para auditar).

Idempotencia: el CSV y el JSON van en modo "w", así que correr el pipeline
dos veces deja el mismo resultado. El log va en modo "a" porque un log ES
un historial: ahí sí queremos que crezca.
"""

import csv
import json
import logging
import os
from datetime import datetime

import config
from transform import COLUMNAS


# ======================================================================
# QUALITY CHECKS
# ======================================================================
def chequear_cantidad(filas, minimo=None):
    """¿Tenemos todas las filas que esperábamos?  [RESUELTO — de ejemplo]

    Fijate el patrón: devuelve una tupla (bool, mensaje). Todos los
    checks tienen que devolver lo mismo para que validar() los trate igual.
    """
    if minimo is None:
        minimo = config.MINIMO_FILAS_ESPERADAS
    ok = len(filas) >= minimo
    return ok, f"cantidad: {len(filas)} filas (mínimo esperado {minimo})"


def chequear_columnas(filas):
    """¿Todas las filas tienen exactamente las columnas del contrato?
    [RESUELTO — de ejemplo]
    """
    esperadas = set(COLUMNAS)
    for fila in filas:
        if set(fila.keys()) != esperadas:
            faltan = esperadas - set(fila.keys())
            return False, f"columnas: una fila no cumple el esquema (faltan {faltan})"
    return True, f"columnas: las {len(COLUMNAS)} del contrato en todas las filas"


def chequear_unicidad(filas):
    """¿Hay duplicados? La clave del dataset es (provincia, anio, destino).

    Devuelve (bool, mensaje), igual que los checks de arriba.
    """
    claves = [(fila["provincia"], fila["anio"], fila["destino"]) for fila in filas]
    ok = len(claves) == len(set(claves))
    duplicados = len(claves) - len(set(claves))
    return ok, f"unicidad: {duplicados} claves (provincia, anio, destino) duplicadas"


def chequear_rangos(filas):
    """¿Los valores son plausibles?

    Un valor negativo o mayor a config.VALOR_MAXIMO_RAZONABLE es
    sospechoso: no existen exportaciones negativas.
    """
    fuera_de_rango = [
        fila
        for fila in filas
        if fila["valor_musd"] < 0 or fila["valor_musd"] > config.VALOR_MAXIMO_RAZONABLE
    ]
    ok = len(fuera_de_rango) == 0
    return ok, f"rangos: {len(fuera_de_rango)} filas con valor_musd fuera de rango"


def chequear_cobertura(filas):
    """Advertencia (no crítica): ¿cuántos nulos quedaron en las derivadas?
    [RESUELTO]
    """
    sin_variacion = sum(1 for f in filas if f["var_interanual_pct"] is None)
    sin_rubro = sum(1 for f in filas if f["rubro_principal"] is None)
    ok = sin_rubro == 0
    return ok, (f"cobertura: {sin_variacion} filas sin variación interanual "
                f"(esperable en el primer año), {sin_rubro} sin rubro")


def validar(filas):
    """Corre todos los checks.  [RESUELTO]

    Los CRÍTICOS cortan el pipeline lanzando una excepción ("fallar
    temprano y ruidosamente"). La cobertura solo deja una advertencia.

    Retorna una lista de dicts con el detalle, para el resumen JSON.
    """
    criticos = [
        chequear_cantidad(filas),
        chequear_columnas(filas),
        chequear_unicidad(filas),
        chequear_rangos(filas),
    ]

    detalle = []
    for ok, mensaje in criticos:
        detalle.append({"check": mensaje, "estado": "OK" if ok else "FALLO"})
        if ok:
            logging.info("  check OK    | %s", mensaje)
        else:
            logging.error("  check FALLO | %s", mensaje)
            raise ValueError(f"Quality check crítico falló -> {mensaje}")

    ok, mensaje = chequear_cobertura(filas)
    detalle.append({"check": mensaje, "estado": "OK" if ok else "AVISO"})
    if ok:
        logging.info("  check OK    | %s", mensaje)
    else:
        logging.warning("  check AVISO | %s", mensaje)

    return detalle


# ======================================================================
# PERSISTENCIA
# ======================================================================
def guardar_csv(filas, carpeta=None, nombre=None):
    """Escribe el dataset final. Modo 'w': cada corrida lo reemplaza.
    [RESUELTO — usalo de modelo para el resto]
    """
    carpeta = carpeta or config.DIR_PROCESSED
    nombre = nombre or config.ARCHIVO_SALIDA_CSV
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)

    logging.info("  CSV: %s (%s filas)", ruta, len(filas))
    return ruta


def construir_resumen(filas, detalle_checks):
    """Arma el resumen del proceso: metadatos + estadísticas descriptivas.

    Este JSON es la "ficha técnica" del dataset: quien lo reciba tiene que
    poder saber de dónde salió, cuándo y qué contiene, SIN abrir el CSV.
    """
    valores = [fila["valor_musd"] for fila in filas]
    anios = [fila["anio"] for fila in filas]
    provincias = sorted({fila["provincia"] for fila in filas})

    resumen = {
        "dataset": "Exportaciones del NEA por país de destino",
        "fuente": (
            "INDEC, vía la API de Series de Tiempo de datos.gob.ar "
            "(datasets 357.1 y 350.1)"
        ),
        "unidad": "millones de dólares FOB",
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filas": len(filas),
        "columnas": len(COLUMNAS),
        "periodo": {"desde": min(anios), "hasta": max(anios)},
        "provincias": provincias,
        "valor_musd": {
            "minimo": min(valores),
            "maximo": max(valores),
            "promedio": round(sum(valores) / len(valores), 2),
        },
        "quality_checks": detalle_checks,
    }
    return resumen


def guardar_resumen(resumen, carpeta=None, nombre=None):
    """Escribe el resumen en JSON, legible por humanos y por programas."""
    carpeta = carpeta or config.DIR_PROCESSED
    nombre = nombre or config.ARCHIVO_SALIDA_JSON
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    logging.info("  JSON: %s", ruta)
    return ruta


def escribir_log_corrida(resumen, carpeta=None, nombre=None):
    """Agrega UNA línea al historial del pipeline.

    Modo "a" (append): nunca borra lo anterior. Cada corrida deja su rastro.
    """
    carpeta = carpeta or config.DIR_LOGS
    nombre = nombre or config.ARCHIVO_LOG
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)

    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M")
    periodo = resumen["periodo"]
    linea = (
        f"{marca_tiempo} | OK | {resumen['filas']} filas | "
        f"{periodo['desde']}-{periodo['hasta']}\n"
    )

    with open(ruta, "a", encoding="utf-8") as f:
        f.write(linea)

    logging.info("  LOG: %s", ruta)
    return ruta


def cargar(filas):
    """CONTRATO: recibe las filas finales; valida y persiste las 3 salidas.
    [RESUELTO]
    """
    logging.info("LOAD: validando")
    detalle = validar(filas)

    logging.info("LOAD: guardando")
    guardar_csv(filas)
    resumen = construir_resumen(filas, detalle)
    guardar_resumen(resumen)
    escribir_log_corrida(resumen)

    logging.info("LOAD OK")
    return resumen

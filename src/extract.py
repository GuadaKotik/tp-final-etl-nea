"""
EXTRACT — Descarga de datos desde la API de Series de Tiempo
============================================================

Responsabilidad única: traer los datos crudos y guardarlos tal como llegan.
No limpia, no calcula, no transforma. Eso es trabajo del Transform.

La API devuelve los datos en formato ANCHO: una fila por año y
una columna por serie pedida, en el mismo orden en que se pidieron.

    {"data": [["1993-01-01", 12.3, 45.6], ...], "meta": [...]}

Por eso guardamos también 'orden_columnas': sin ese dato no sabríamos
qué destino corresponde a cada número.
"""

import json
import logging
import os
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

import config


def construir_url(ids, formato="json"):
    """CONTRATO: recibe una lista de IDs de series; devuelve la URL completa.

    Parámetros:
        ids: lista de str con los identificadores de serie.
        formato: 'json' o 'csv'.
    Retorna:
        str con la URL lista para pedir.
    """
    parametros = {"ids": ",".join(ids), "format": formato}
    return f"{config.API_BASE}?{urlencode(parametros)}"


def pedir_a_la_api(url):
    """CONTRATO: recibe una URL; devuelve la respuesta parseada como dict.

    Lanza una excepción si la descarga falla. Quien llama decide qué hacer:
    acá no decidimos por el resto del programa.
    """
    # Some servers block requests without a browser-like User-Agent.
    req = Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
        )
    })
    with urlopen(req, timeout=config.TIMEOUT_SEGUNDOS) as respuesta:
        crudo = respuesta.read().decode("utf-8")
    return json.loads(crudo)


def descargar_grupo(nombre_grupo, provincia, series):
    """Descarga un grupo de series de una provincia.

    Parámetros:
        nombre_grupo: 'destino' o 'rubro' (para nombrar el archivo).
        provincia: str, nombre de la provincia.
        series: dict {nombre_legible: id_de_serie}.
    Retorna:
        dict con la respuesta y el orden de las columnas, o None si falló.
    """
    nombres = list(series.keys())
    ids = [series[n] for n in nombres]
    url = construir_url(ids)

    try:
        respuesta = pedir_a_la_api(url)
    except (URLError, HTTPError, ValueError) as error:
        logging.error("No pude descargar %s de %s: %s", nombre_grupo, provincia, error)
        return None

    filas = len(respuesta.get("data", []))
    logging.info("  %s / %s: %s series, %s años", provincia, nombre_grupo, len(ids), filas)

    return {
        "provincia": provincia,
        "grupo": nombre_grupo,
        "orden_columnas": nombres,   # posición i de 'data' -> nombres[i]
        "ids": ids,
        "data": respuesta.get("data", []),
    }


def guardar_crudo(paquete, carpeta):
    """Persiste el paquete crudo en data/raw/ como JSON."""
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"{paquete['grupo']}_{paquete['provincia'].lower()}.json"
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(paquete, f, ensure_ascii=False, indent=2)
    return ruta


def extraer(provincias=None, carpeta_raw=None):
    """Orquesta la extracción completa.

    Hace 2 llamadas por provincia (destinos y rubros). Con las 4 provincias
    del NEA son 8 llamadas en total.

    Retorna:
        dict con dos listas de paquetes: {'destino': [...], 'rubro': [...]}
    """
    if provincias is None:
        provincias = list(config.SERIES_DESTINO.keys())
    if carpeta_raw is None:
        carpeta_raw = config.DIR_RAW

    logging.info("EXTRACT: %s provincias", len(provincias))
    resultado = {"destino": [], "rubro": []}

    for provincia in provincias:
        # 1) destinos + total (el total se pide junto para no hacer otra llamada)
        series_destino = dict(config.SERIES_DESTINO[provincia])
        series_destino["__TOTAL__"] = config.SERIES_TOTAL[provincia]
        paquete = descargar_grupo("destino", provincia, series_destino)
        if paquete is not None:
            guardar_crudo(paquete, carpeta_raw)
            resultado["destino"].append(paquete)

        # 2) rubros
        paquete = descargar_grupo("rubro", provincia, config.SERIES_RUBRO[provincia])
        if paquete is not None:
            guardar_crudo(paquete, carpeta_raw)
            resultado["rubro"].append(paquete)

    total_ok = len(resultado["destino"]) + len(resultado["rubro"])
    logging.info("EXTRACT OK: %s de %s descargas", total_ok, len(provincias) * 2)

    if total_ok == 0:
        raise RuntimeError(
            "No se pudo descargar ninguna serie. ¿Tenés conexión a internet? "
            "Si el problema persiste, revisá que los IDs de config.py sigan vigentes."
        )
    return resultado


def cargar_desde_disco(carpeta_raw=None):
    """Vuelve a leer los JSON ya descargados, sin tocar la red.

    Útil para trabajar sin internet o para no re-descargar mientras
    desarrollás el Transform.
    """
    if carpeta_raw is None:
        carpeta_raw = config.DIR_RAW

    resultado = {"destino": [], "rubro": []}
    if not os.path.isdir(carpeta_raw):
        return resultado

    for nombre in sorted(os.listdir(carpeta_raw)):
        if not nombre.endswith(".json"):
            continue
        with open(os.path.join(carpeta_raw, nombre), encoding="utf-8") as f:
            paquete = json.load(f)
        resultado[paquete["grupo"]].append(paquete)

    logging.info("Cargados desde disco: %s destino, %s rubro",
                 len(resultado["destino"]), len(resultado["rubro"]))
    return resultado

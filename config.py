"""
CONFIGURACIÓN del pipeline — TP Final, Unidad II
=================================================

El código dice CÓMO se hace; este archivo dice CON QUÉ.
Separar la configuración del código permite cambiar el comportamiento
del pipeline sin tocar una sola línea de lógica.

Fuente de datos: API de Series de Tiempo de datos.gob.ar
  - Dataset 357.1: Exportaciones por provincia y por país de destino
  - Dataset 350.1: Exportaciones por provincia y rubro
  Origen: INDEC. Unidad: millones de dólares. Período: 1993–2024.
  Documentación: https://apis.datos.gob.ar/series/api/

IDs verificados contra la API el 2026-08-02.
"""

# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
API_BASE = "https://apis.datos.gob.ar/series/api/series"
TIMEOUT_SEGUNDOS = 20

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
DIR_RAW = "data/raw"
DIR_PROCESSED = "data/processed"
DIR_LOGS = "logs"

ARCHIVO_SALIDA_CSV = "exportaciones_nea.csv"
ARCHIVO_SALIDA_JSON = "resumen.json"
ARCHIVO_LOG = "pipeline.log"

# ----------------------------------------------------------------------
# SERIES POR PROVINCIA — exportaciones por PAÍS DE DESTINO (dataset 357.1)
# Estructura: {provincia: {destino_legible: id_de_serie}}
# ----------------------------------------------------------------------
SERIES_DESTINO = {
    "Chaco": {
        "China":          "357.1_CHACO_CHININA__11",
        "Brasil":         "357.1_CHACO_BRASSIL__12",
        "Italia":         "357.1_CHACO_ITALLIA__12",
        "Chile":          "357.1_CHACO_CHILILE__11",
        "México":         "357.1_CHACO_MEXIICO__12",
        "Estados Unidos": "357.1_CHACO_ESTADOS__20",
        "Indonesia":      "357.1_CHACO_INDOSIA__15",
        "España":         "357.1_CHACO_ESPANIA__13",
        "Egipto":         "357.1_CHACO_EGIPPTO__12",
        "Colombia":       "357.1_CHACO_COLOBIA__14",
        "Resto":          "357.1_CHACO_RESTSTO__11",
    },
    "Corrientes": {
        "Brasil":         "357.1_CORRIENTESSIL__17",
        "Estados Unidos": "357.1_CORRIENTESDOS__25",
        "Chile":          "357.1_CORRIENTESILE__16",
        "Países Bajos":   "357.1_CORRIENTESJOS__23",
        "Iraq":           "357.1_CORRIENTESRAQ__15",
        "Rusia":          "357.1_CORRIENTESSIA__16",
        "España":         "357.1_CORRIENTESNIA__18",
        "Italia":         "357.1_CORRIENTESLIA__17",
        "Venezuela":      "357.1_CORRIENTESELA__20",
        "Reino Unido":    "357.1_CORRIENTESIDO__22",
        "Resto":          "357.1_CORRIENTESSTO__16",
    },
    "Formosa": {
        "Brasil":         "357.1_FORMOSA_BRSIL__14",
        "Estados Unidos": "357.1_FORMOSA_ESDOS__22",
        "Chile":          "357.1_FORMOSA_CHILE__13",
        "China":          "357.1_FORMOSA_CHINA__13",
        "Paraguay":       "357.1_FORMOSA_PAUAY__16",
        "Italia":         "357.1_FORMOSA_ITLIA__14",
        "Iraq":           "357.1_FORMOSA_IRRAQ__12",
        "México":         "357.1_FORMOSA_MEICO__14",
        "Perú":           "357.1_FORMOSA_PEERU__12",
        "España":         "357.1_FORMOSA_ESNIA__15",
        "Resto":          "357.1_FORMOSA_RESTO__13",
    },
    "Misiones": {
        "Brasil":         "357.1_MISIONES_BSIL__15",
        "Estados Unidos": "357.1_MISIONES_EDOS__23",
        "Bélgica":        "357.1_MISIONES_BICA__16",
        "Siria":          "357.1_MISIONES_SRIA__14",
        "China":          "357.1_MISIONES_CINA__14",
        "Francia":        "357.1_MISIONES_FCIA__16",
        "Chile":          "357.1_MISIONES_CILE__14",
        "Sudáfrica":      "357.1_MISIONES_SICA__18",
        "Alemania":       "357.1_MISIONES_ANIA__17",
        "Países Bajos":   "357.1_MISIONES_PJOS__21",
        "Resto":          "357.1_MISIONES_RSTO__14",
    },
}

# Serie del TOTAL exportado por provincia (mismo dataset 357.1)
SERIES_TOTAL = {
    "Chaco":      "357.1_CHACO_TOTAACO__17",
    "Corrientes": "357.1_CORRIENTESTES__27",
    "Formosa":    "357.1_FORMOSA_TOOSA__21",
    "Misiones":   "357.1_MISIONES_TNES__23",
}

# ----------------------------------------------------------------------
# SERIES POR PROVINCIA — exportaciones por RUBRO (dataset 350.1)
# PP  = Productos primarios
# MOA = Manufacturas de Origen Agropecuario
# MOI = Manufacturas de Origen Industrial
# CyE = Combustibles y Energía
# ----------------------------------------------------------------------
SERIES_RUBRO = {
    "Chaco": {
        "Productos primarios": "350.1_CHACO_PP_PP__8",
        "MOA":                 "350.1_CHACO_MOAMOA__9",
        "MOI":                 "350.1_CHACO_MOIMOI__9",
        "CyE":                 "350.1_CHACO_CYECYE__9",
    },
    "Corrientes": {
        "Productos primarios": "350.1_CORRIENTES_PP__13",
        "MOA":                 "350.1_CORRIENTESMOA__14",
        "MOI":                 "350.1_CORRIENTESMOI__14",
        "CyE":                 "350.1_CORRIENTESCYE__14",
    },
    "Formosa": {
        "Productos primarios": "350.1_FORMOSA_PP_PP__10",
        "MOA":                 "350.1_FORMOSA_MOMOA__11",
        "MOI":                 "350.1_FORMOSA_MOMOI__11",
        "CyE":                 "350.1_FORMOSA_CYCYE__11",
    },
    "Misiones": {
        "Productos primarios": "350.1_MISIONES_P_PP__11",
        "MOA":                 "350.1_MISIONES_MMOA__12",
        "MOI":                 "350.1_MISIONES_MMOI__12",
        "CyE":                 "350.1_MISIONES_CCYE__12",
    },
}

# ----------------------------------------------------------------------
# MAPEO de país de destino -> región geoeconómica
# Se usa para crear la columna derivada 'region_destino'.
# ----------------------------------------------------------------------
REGIONES = {
    "Brasil": "Mercosur",
    "Paraguay": "Mercosur",
    "Estados Unidos": "América del Norte",
    "México": "América Latina",
    "Chile": "América Latina",
    "Colombia": "América Latina",
    "Perú": "América Latina",
    "Venezuela": "América Latina",
    "Italia": "Europa",
    "España": "Europa",
    "Países Bajos": "Europa",
    "Bélgica": "Europa",
    "Francia": "Europa",
    "Alemania": "Europa",
    "Reino Unido": "Europa",
    "Rusia": "Europa",
    "China": "Asia",
    "Indonesia": "Asia",
    "Iraq": "Asia",
    "Siria": "Asia",
    "Egipto": "África",
    "Sudáfrica": "África",
    "Resto": "Otros",
}
REGION_POR_DEFECTO = "Otros"

# ----------------------------------------------------------------------
# PARÁMETROS DE NEGOCIO
# ----------------------------------------------------------------------
TOP_N = 3          # cuántos destinos se marcan como 'es_top3'
ANIO_MINIMO = 1993
ANIO_MAXIMO = 2024

# ----------------------------------------------------------------------
# QUALITY CHECKS
# ----------------------------------------------------------------------
MINIMO_FILAS_ESPERADAS = 1000   # 4 provincias x 11 destinos x 32 años = 1408
VALOR_MAXIMO_RAZONABLE = 10000  # millones de USD: un valor mayor es sospechoso

"""
MAIN — Orquestación del pipeline
=================================

Esta es la función "directora": no calcula nada, solo llama a las otras
en el orden correcto. Es un mini-DAG — cada etapa depende de la anterior,
y si una falla, las siguientes no corren.

    EXTRAER  ->  TRANSFORMAR  ->  CHEQUEAR + GUARDAR

Uso:
    python src/main.py                # descarga de la API y procesa
    python src/main.py --sin-internet # reutiliza lo que ya está en data/raw/
"""

import json
import logging
import os
import sys

# Permite ejecutar el script desde la raíz del proyecto (python src/main.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import extract
import load
import transform


def configurar_logging():
    """Consola + archivo. Cuando esto falle, el log va a contar la historia."""
    os.makedirs(config.DIR_LOGS, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(config.DIR_LOGS, "ejecucion.log"), encoding="utf-8"
            ),
        ],
    )


def main(sin_internet=False):
    configurar_logging()
    logging.info("=" * 62)
    logging.info("PIPELINE EXPORTACIONES NEA — inicio")
    logging.info("=" * 62)

    # 1) EXTRACT
    if sin_internet:
        logging.info("Modo sin internet: leyendo data/raw/")
        crudos = extract.cargar_desde_disco()
        if not crudos["destino"]:
            raise RuntimeError(
                "No hay datos en data/raw/. Corré el pipeline con internet "
                "al menos una vez antes de usar --sin-internet."
            )
    else:
        crudos = extract.extraer()

    # 2) TRANSFORM  (depende de 1)
    filas = transform.transformar(crudos)

    # 3) CHEQUEAR + GUARDAR  (depende de 2)
    resumen = load.cargar(filas)

    logging.info("=" * 62)
    logging.info("PIPELINE EXPORTACIONES NEA — fin OK")
    logging.info("=" * 62)

    print("\nResumen de la corrida:")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return resumen


if __name__ == "__main__":
    main(sin_internet="--sin-internet" in sys.argv)

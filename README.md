# Pipeline ETL — Exportaciones del NEA (1993–2024)

Trabajo Práctico Integrador — Unidad II
Diplomatura Universitaria en Data Analytics e Inteligencia Artificial Aplicada (UNNE)

## Qué hace este pipeline

Se conecta a la **API de Series de Tiempo** de datos.gob.ar (datos del INDEC),
descarga las exportaciones de **Chaco, Corrientes, Formosa y Misiones** por
país de destino y por rubro entre 1993 y 2024, y las transforma en un único
dataset analítico:

```
API datos.gob.ar          data/raw/\*.json         data/processed/
(INDEC, 8 llamadas)  -->  (crudo, sin tocar) -->  exportaciones\_nea.csv
                                                   resumen.json
     EXTRACT                  TRANSFORM              CHEQUEAR + LOAD
```

El resultado es `data/processed/exportaciones\_nea.csv`, con **1.408 filas
(4 provincias × 11 destinos × 32 años) y 13 columnas**: valor exportado,
participación sobre el total provincial, variación interanual, década,
ranking del destino ese año, y el rubro más exportado (cruzado desde el
dataset de rubros).

Cada corrida además produce:

* `data/processed/resumen.json`: ficha técnica del dataset (fuente, período,
estadísticas de `valor\_musd`, resultado de los quality checks).
* `logs/pipeline.log`: una línea por corrida (se agrega, nunca se borra).

## Cómo instalarlo y ejecutarlo

Requiere **Python 3.8+**. No usa librerías externas: solo la biblioteca
estándar (`urllib`, `json`, `csv`, `logging`, `datetime`).

```bash
python --version              # verificar 3.8+
python src/main.py            # corre el pipeline completo (necesita internet)
```

La primera corrida descarga los datos de la API y los guarda en
`data/raw/`. Después se puede trabajar sin conexión reutilizando lo ya
descargado:

```bash
python src/main.py --sin-internet
```

Para correr los tests:

```bash
python tests/test\_transform.py
```

## De dónde salen los datos

**Fuente:** INDEC, vía la [API de Series de Tiempo](https://apis.datos.gob.ar/series/api/)
del portal de datos abiertos del Estado argentino (datos.gob.ar). Es una
API pública, sin necesidad de credenciales.

* **Dataset 357.1** — Exportaciones por provincia y país de destino.
* **Dataset 350.1** — Exportaciones por provincia y rubro.
* **Unidad:** millones de dólares FOB.
* **Período:** 1993–2024.

Los identificadores de cada serie (uno por provincia × destino, y uno por
provincia × rubro) están centralizados en `config.py`, separados del
código: si algún ID cambia en la API, se actualiza ahí y no en la lógica.

## Estructura del proyecto

```
├── config.py               Configuración: IDs de series, rutas, mapeos
├── src/
│   ├── extract.py          Descarga de la API -> data/raw/
│   ├── transform.py        Limpieza, tipado, columnas derivadas y join
│   ├── load.py             Quality checks + guardado de CSV/JSON/log
│   └── main.py             Orquesta extract -> transform -> load
├── tests/
│   └── test\_transform.py   19 pruebas de transformaciones
├── data/
│   ├── raw/                 JSON crudos tal como llegan de la API
│   └── processed/           CSV y resumen.json finales
└── logs/                    Historial de corridas (pipeline.log)
```

## Decisiones de diseño

* **Manejo de errores:** si el INDEC publicó un valor nulo para algún año o
destino, esa observación puntual se saltea (no rompe el resto del
pipeline). Las divisiones (participación, variación interanual) devuelven
`None` en vez de romper cuando el denominador es cero o inexistente.
* **Quality checks críticos** (cortan el pipeline si fallan): cantidad
mínima de filas, las 13 columnas del contrato en todas las filas,
ausencia de duplicados por `(provincia, anio, destino)`, y valores de
`valor\_musd` dentro de un rango razonable. Además hay un check de
cobertura (no crítico) que solo deja una advertencia.
* **Idempotencia:** el CSV y el resumen.json se sobrescriben en cada ejecución. Con los mismos datos de entrada, el CSV mantiene el mismo contenido; el JSON actualiza su campo “generado” con la fecha y hora de la corrida. El log se abre en modo “a” y agrega una línea por ejecución. Verifiqué dos ejecuciones consecutivas: el CSV quedó idéntico y el log registró dos líneas.

## Un hallazgo en los datos

Al analizar Corrientes en 2024, observé que Estados Unidos fue el principal país de destino entre los identificados individualmente en el dataset, con 49,57 millones de dólares FOB, equivalentes al 19,23 % del total provincial. Sin embargo, el valor exportado a ese país cayó un 10,09 % respecto de 2023. La categoría “Resto” ocupó el primer puesto del ranking con el 42,71 %, pero agrupa varios destinos y no representa un único país. Esto muestra la importancia de distinguir países individuales de categorías agrupadas al interpretar el ranking.


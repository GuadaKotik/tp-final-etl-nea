"""
TESTS del Transform
====================

Probamos las funciones puras: mismas entradas -> misma salida, sin red
ni archivos. Por eso el Transform se testea fácil y el Extract no.

Para correrlos:
    python tests/test_transform.py
    (o bien:  pytest tests/  si tenés pytest instalado)
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "src"))

import transform


class TestDerivadasSimples(unittest.TestCase):

    def test_extraer_anio(self):
        self.assertEqual(transform.extraer_anio("1993-01-01"), 1993)
        self.assertEqual(transform.extraer_anio("2024-01-01"), 2024)

    def test_calcular_decada(self):
        self.assertEqual(transform.calcular_decada(1993), "1990s")
        self.assertEqual(transform.calcular_decada(2000), "2000s")
        self.assertEqual(transform.calcular_decada(2024), "2020s")

    def test_clasificar_region_conocida(self):
        self.assertEqual(transform.clasificar_region("Brasil"), "Mercosur")
        self.assertEqual(transform.clasificar_region("China"), "Asia")

    def test_clasificar_region_desconocida(self):
        # Un país no mapeado no debe romper el pipeline
        self.assertEqual(transform.clasificar_region("Atlantida"), "Otros")

    def test_participacion(self):
        self.assertEqual(transform.calcular_participacion(110.93, 401.74), 27.61)

    def test_participacion_total_cero(self):
        # Dividir por cero rompería: esperamos None, no una excepción
        self.assertIsNone(transform.calcular_participacion(10.0, 0))
        self.assertIsNone(transform.calcular_participacion(10.0, None))


class TestVariacion(unittest.TestCase):

    def test_variacion_positiva(self):
        # Chaco -> China: 75.79 (2023) a 110.93 (2024) = +46.36 %
        self.assertEqual(transform.calcular_variacion(110.93, 75.79), 46.36)

    def test_variacion_negativa(self):
        self.assertEqual(transform.calcular_variacion(50.0, 100.0), -50.0)

    def test_variacion_sin_anio_anterior(self):
        self.assertIsNone(transform.calcular_variacion(100.0, None))
        self.assertIsNone(transform.calcular_variacion(100.0, 0))


class TestAnchoALargo(unittest.TestCase):

    def paquete_minimo(self):
        return [{
            "provincia": "Chaco",
            "grupo": "destino",
            "orden_columnas": ["China", "Brasil", "__TOTAL__"],
            "data": [
                ["2023-01-01", 75.79, 13.89, 303.09],
                ["2024-01-01", 110.93, 18.12, 401.74],
            ],
        }]

    def test_cantidad_de_filas(self):
        # 2 años x 2 destinos (el total NO es un destino) = 4 filas
        filas = transform.ancho_a_largo(self.paquete_minimo())
        self.assertEqual(len(filas), 4)

    def test_el_total_no_es_un_destino(self):
        filas = transform.ancho_a_largo(self.paquete_minimo())
        self.assertNotIn("__TOTAL__", [f["destino"] for f in filas])

    def test_total_se_guarda_en_cada_fila(self):
        filas = transform.ancho_a_largo(self.paquete_minimo())
        de_2024 = [f for f in filas if f["anio"] == 2024]
        for fila in de_2024:
            self.assertEqual(fila["total_provincia_musd"], 401.74)

    def test_saltea_faltantes(self):
        paquete = self.paquete_minimo()
        paquete[0]["data"][0][1] = None      # China 2023 sin dato
        filas = transform.ancho_a_largo(paquete)
        self.assertEqual(len(filas), 3)


class TestRanking(unittest.TestCase):

    def test_ranking_por_provincia_y_anio(self):
        filas = [
            {"provincia": "Chaco", "anio": 2024, "destino": "China", "valor_musd": 110.9},
            {"provincia": "Chaco", "anio": 2024, "destino": "Brasil", "valor_musd": 18.1},
            {"provincia": "Chaco", "anio": 2024, "destino": "Italia", "valor_musd": 50.0},
        ]
        transform.agregar_ranking(filas, top_n=2)
        por_destino = {f["destino"]: f for f in filas}
        self.assertEqual(por_destino["China"]["ranking_destino"], 1)
        self.assertEqual(por_destino["Italia"]["ranking_destino"], 2)
        self.assertEqual(por_destino["Brasil"]["ranking_destino"], 3)
        self.assertTrue(por_destino["China"]["es_top3"])
        self.assertFalse(por_destino["Brasil"]["es_top3"])


class TestJoinRubros(unittest.TestCase):

    def indice(self):
        paquetes = [{
            "provincia": "Chaco",
            "grupo": "rubro",
            "orden_columnas": ["Productos primarios", "MOA", "MOI", "CyE"],
            "data": [["2024-01-01", 326.61, 70.37, 4.74, 0.0]],
        }]
        return transform.construir_indice_rubros(paquetes)

    def test_rubro_principal(self):
        indice = self.indice()
        self.assertEqual(indice[("Chaco", 2024)]["rubro_principal"], "Productos primarios")

    def test_participacion_primarios(self):
        indice = self.indice()
        self.assertEqual(indice[("Chaco", 2024)]["pp_participacion_pct"], 81.3)

    def test_join_conserva_filas_sin_match(self):
        filas = [{"provincia": "Chaco", "anio": 1990, "destino": "China"}]
        transform.unir_con_rubros(filas, self.indice())
        self.assertEqual(len(filas), 1)              # LEFT JOIN: no se pierde
        self.assertIsNone(filas[0]["rubro_principal"])


# ======================================================================
# TODO 13 (BONUS) — tests propios
# ======================================================================
class TestPropios(unittest.TestCase):
    """Casos propios, sumados al bonus del TP.

    - ¿Qué pasa si 'paquetes_destino' viene vacío? ancho_a_largo()
      debería devolver [] y no romper.
    - ¿El ranking asigna bien cuando hay empate en valor_musd?
    """

    def test_lista_vacia(self):
        # Un input vacío no debe romper el pipeline: se espera lista vacía.
        filas = transform.ancho_a_largo([])
        self.assertEqual(filas, [])

    def test_ranking_con_empate(self):
        # Con empate, sorted() es estable: el orden de desempate es el de
        # entrada. Lo que sí debe cumplirse siempre es que el ranking sea
        # una secuencia 1..N sin huecos ni repetidos, y que top_n se
        # respete igual.
        filas = [
            {"provincia": "Misiones", "anio": 2020, "destino": "Brasil", "valor_musd": 30.0},
            {"provincia": "Misiones", "anio": 2020, "destino": "China", "valor_musd": 30.0},
            {"provincia": "Misiones", "anio": 2020, "destino": "Chile", "valor_musd": 10.0},
        ]
        transform.agregar_ranking(filas, top_n=2)
        rankings = sorted(f["ranking_destino"] for f in filas)
        self.assertEqual(rankings, [1, 2, 3])
        por_destino = {f["destino"]: f for f in filas}
        self.assertEqual(por_destino["Chile"]["ranking_destino"], 3)
        self.assertFalse(por_destino["Chile"]["es_top3"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

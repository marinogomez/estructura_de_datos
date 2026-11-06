"""
test.py
Pruebas unitarias del Quadtree K-dimensional y verificación visual de:
  - la estructura del árbol sobre los 10.000 puntos de entrega,
  - la búsqueda dentro de un radio de 500 m,
  - los vecinos más cercanos.

Ejecución:
    python test.py            -> corre las pruebas y genera las gráficas en graficas/
    python -m unittest test   -> solo las pruebas
"""

import os
import random
import unittest

from sistema_entregas_lab4.Quadtree import (LAT_REFERENCIA, LON_REFERENCIA, Caja, FuerzaBruta, Quadtree,
                                            cargar_puntos_entrega, construir_quadtree,
                                            generar_puntos_aleatorios, latlon_a_metros, metros_a_latlon)

CARPETA_GRAFICAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")


def ids(resultados):
    """Conjunto de datos (ids) de una lista de resultados (distancia, punto, dato)."""
    return {dato for _, _, dato in resultados}


def distancias(resultados):
    return [d for d, _, _ in resultados]


# ---------------------------------------------------------------------------
# Pruebas unitarias
# ---------------------------------------------------------------------------

class TestCaja(unittest.TestCase):

    def test_distancia_minima_dentro_y_fuera(self):
        caja = Caja((0, 0), (10, 10))
        self.assertEqual(caja.distancia_minima((5, 5)), 0)
        self.assertEqual(caja.distancia_minima((13, 5)), 3)
        self.assertEqual(caja.distancia_minima((13, 14)), 5)   # 3-4-5: hasta la esquina

    def test_subdividir_genera_2_a_la_k_hijas(self):
        for k in (1, 2, 3, 4):
            caja = Caja([0] * k, [8] * k)
            self.assertEqual(len(caja.subdividir()), 2 ** k)

    def test_todo_punto_cae_en_alguna_hija(self):
        caja = Caja((0, 0, 0), (8, 8, 8))
        hijas = caja.subdividir()
        for punto in generar_puntos_aleatorios(200, 3, 8, semilla=1):
            self.assertTrue(any(hija.contiene(punto) for hija in hijas))

    def test_limites_invalidos(self):
        with self.assertRaises(ValueError):
            Caja((10, 0), (0, 10))


class TestQuadtree2D(unittest.TestCase):

    def setUp(self):
        self.puntos = generar_puntos_aleatorios(2000, 2, 10000, semilla=7)
        self.arbol = Quadtree((0, 0), (10000, 10000), capacidad=4)
        for i, p in enumerate(self.puntos):
            self.arbol.insertar(p, i)
        self.bruta = FuerzaBruta(self.puntos)
        self.consultas = generar_puntos_aleatorios(100, 2, 10000, semilla=8)

    def test_tamano_y_subdivision(self):
        self.assertEqual(len(self.arbol), 2000)
        self.assertFalse(self.arbol.raiz.es_hoja())
        hojas = [n for n in self.arbol.nodos() if n.es_hoja()]
        self.assertEqual(sum(len(h.puntos) for h in hojas), 2000)
        self.assertTrue(all(len(h.puntos) <= 4 for h in hojas))

    def test_cada_punto_esta_en_la_caja_de_su_hoja(self):
        for nodo in self.arbol.nodos():
            for punto, _ in nodo.puntos:
                self.assertTrue(nodo.caja.contiene(punto))

    def test_radio_igual_a_fuerza_bruta(self):
        for consulta in self.consultas:
            for radio in (0, 100, 500, 2000):
                esperado = self.bruta.vecinos_en_radio(consulta, radio)
                obtenido = self.arbol.vecinos_en_radio(consulta, radio)
                self.assertEqual(ids(obtenido), ids(esperado))

    def test_radio_ordenado_por_distancia(self):
        resultado = self.arbol.vecinos_en_radio((5000, 5000), 1000)
        self.assertEqual(distancias(resultado), sorted(distancias(resultado)))
        self.assertTrue(all(d <= 1000 for d in distancias(resultado)))

    def test_radio_poda_nodos(self):
        self.arbol.vecinos_en_radio((5000, 5000), 300)
        self.assertLess(self.arbol.nodos_visitados, self.arbol.cantidad_nodos())

    def test_vecino_mas_cercano_igual_a_fuerza_bruta(self):
        for consulta in self.consultas:
            self.assertAlmostEqual(self.arbol.vecino_mas_cercano(consulta)[0],
                                   self.bruta.vecino_mas_cercano(consulta)[0])

    def test_k_vecinos_igual_a_fuerza_bruta(self):
        for consulta in self.consultas:
            for k in (1, 5, 20):
                esperado = distancias(self.bruta.k_vecinos_mas_cercanos(consulta, k))
                obtenido = distancias(self.arbol.k_vecinos_mas_cercanos(consulta, k))
                self.assertEqual(len(obtenido), k)
                for a, b in zip(obtenido, esperado):
                    self.assertAlmostEqual(a, b)

    def test_consulta_fuera_de_los_limites(self):
        # La ubicación consultada puede estar fuera del área de los puntos.
        consulta = (-3000, 15000)
        self.assertAlmostEqual(self.arbol.vecino_mas_cercano(consulta)[0],
                               self.bruta.vecino_mas_cercano(consulta)[0])

    def test_k_mayor_que_n(self):
        arbol = construir_quadtree([(0, 0), (1, 1), (2, 2)])
        self.assertEqual(len(arbol.k_vecinos_mas_cercanos((0, 0), 10)), 3)

    def test_insertar_fuera_de_limites_o_dimension_incorrecta(self):
        with self.assertRaises(ValueError):
            self.arbol.insertar((-1, 5))
        with self.assertRaises(ValueError):
            self.arbol.insertar((1, 2, 3))

    def test_puntos_en_el_borde(self):
        arbol = Quadtree((0, 0), (10, 10), capacidad=1)
        bordes = [(0, 0), (10, 10), (0, 10), (10, 0), (5, 5), (5, 0)]
        for i, p in enumerate(bordes):
            arbol.insertar(p, i)
        self.assertEqual(len(arbol.vecinos_en_radio((5, 5), 100)), len(bordes))
        self.assertEqual(arbol.vecino_mas_cercano((10, 10))[0], 0)

    def test_arbol_vacio(self):
        arbol = Quadtree((0, 0), (10, 10))
        self.assertEqual(arbol.vecinos_en_radio((5, 5), 100), [])
        self.assertIsNone(arbol.vecino_mas_cercano((5, 5)))

    def test_puntos_duplicados_no_causan_recursion_infinita(self):
        arbol = Quadtree((0, 0), (10, 10), capacidad=2, profundidad_maxima=10)
        for i in range(500):
            arbol.insertar((3, 3), i)
        self.assertEqual(len(arbol), 500)
        self.assertLessEqual(arbol.profundidad(), 10)
        self.assertEqual(len(arbol.vecinos_en_radio((3, 3), 0)), 500)


class TestQuadtreeKDimensiones(unittest.TestCase):

    def comparar_con_fuerza_bruta(self, dimension):
        puntos = generar_puntos_aleatorios(1500, dimension, 1000, semilla=dimension)
        arbol = construir_quadtree(puntos, capacidad=6)
        bruta = FuerzaBruta(puntos)
        self.assertEqual(len(arbol.raiz.caja.subdividir()), 2 ** dimension)
        for consulta in generar_puntos_aleatorios(40, dimension, 1000, semilla=99):
            self.assertEqual(ids(arbol.vecinos_en_radio(consulta, 150)),
                             ids(bruta.vecinos_en_radio(consulta, 150)))
            obtenido = distancias(arbol.k_vecinos_mas_cercanos(consulta, 7))
            esperado = distancias(bruta.k_vecinos_mas_cercanos(consulta, 7))
            for a, b in zip(obtenido, esperado):
                self.assertAlmostEqual(a, b)

    def test_1d(self):
        self.comparar_con_fuerza_bruta(1)

    def test_3d_octree(self):
        self.comparar_con_fuerza_bruta(3)

    def test_4d(self):
        self.comparar_con_fuerza_bruta(4)

    def test_5d(self):
        self.comparar_con_fuerza_bruta(5)


class TestUnidadesYDatos(unittest.TestCase):

    def test_un_grado_de_latitud_son_111_km(self):
        _, y = latlon_a_metros(LAT_REFERENCIA + 1, LON_REFERENCIA)
        self.assertAlmostEqual(y, 111195, delta=5)

    def test_ida_y_vuelta_latlon_metros(self):
        lat, lon = metros_a_latlon(*latlon_a_metros(6.2675, -75.5689))
        self.assertAlmostEqual(lat, 6.2675, places=9)
        self.assertAlmostEqual(lon, -75.5689, places=9)

    def test_radio_500_m_en_coordenadas_reales(self):
        # Dos puntos separados ~0.0045° de latitud (~500 m) en Medellín.
        a = latlon_a_metros(6.2500, -75.5700)
        b = latlon_a_metros(6.2545, -75.5700)
        arbol = construir_quadtree([a, b])
        self.assertEqual(len(arbol.vecinos_en_radio(a, 501)), 2)
        self.assertEqual(len(arbol.vecinos_en_radio(a, 499)), 1)

    def test_dataset_estatico_de_10000_puntos(self):
        registros = cargar_puntos_entrega()
        self.assertEqual(len(registros), 10000)
        self.assertEqual(len({r[0] for r in registros}), 10000)
        self.assertEqual(registros, cargar_puntos_entrega())


# ---------------------------------------------------------------------------
# Verificación visual
# ---------------------------------------------------------------------------

def generar_visualizaciones():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    os.makedirs(CARPETA_GRAFICAS, exist_ok=True)
    registros = cargar_puntos_entrega()
    puntos = [(x, y) for _, _, _, x, y in registros]
    arbol = construir_quadtree(puntos, [r[0] for r in registros], capacidad=8)
    bruta = FuerzaBruta(puntos, [r[0] for r in registros])
    xs = [p[0] / 1000 for p in puntos]
    ys = [p[1] / 1000 for p in puntos]

    def rectangulo(caja, **estilo):
        (x0, y0), (x1, y1) = caja.minimo, caja.maximo
        return Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000,
                         fill=False, **estilo)

    # 1. Estructura del Quadtree ------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 11))
    for nodo in arbol.nodos():
        if nodo.es_hoja():
            ax.add_patch(rectangulo(nodo.caja, edgecolor="#4a7ab5", linewidth=0.4))
    ax.scatter(xs, ys, s=1, color="#222222")
    ax.set_title("Quadtree sobre %d puntos de entrega (capacidad=%d)\n%d nodos, profundidad %d"
                 % (len(arbol), arbol.capacidad, arbol.cantidad_nodos(), arbol.profundidad()))
    ax.set_xlabel("x (km, hacia el este)")
    ax.set_ylabel("y (km, hacia el norte)")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_GRAFICAS, "estructura_quadtree.png"), dpi=150)
    plt.close(fig)

    # 2. Búsqueda dentro de un radio de 500 m -----------------------------------
    nombre, (lat, lon) = "Universidad de Antioquia", (6.2675, -75.5689)
    centro = latlon_a_metros(lat, lon)
    radio = 500
    resultado = arbol.vecinos_en_radio(centro, radio)
    esperado = bruta.vecinos_en_radio(centro, radio)
    coinciden = ids(resultado) == ids(esperado)
    # Hojas que realmente se revisaron (las que no fueron podadas).
    hojas_revisadas = [n for n in arbol.nodos()
                       if n.es_hoja() and n.caja.distancia_minima(centro) <= radio]

    fig, ax = plt.subplots(figsize=(9, 9))
    margen = 1.6
    for nodo in hojas_revisadas:
        ax.add_patch(rectangulo(nodo.caja, edgecolor="#e39b2d", linewidth=1.0))
    ax.scatter(xs, ys, s=4, color="#b8b8b8", label="Puntos de entrega")
    ax.scatter([p[0] / 1000 for _, p, _ in resultado], [p[1] / 1000 for _, p, _ in resultado],
               s=10, color="#2a7a3b", label="Dentro del radio (Quadtree): %d" % len(resultado))
    ax.add_patch(Circle((centro[0] / 1000, centro[1] / 1000), radio / 1000, fill=False,
                        edgecolor="#c0392b", linewidth=2, label="Radio de %d m" % radio))
    ax.scatter([centro[0] / 1000], [centro[1] / 1000], marker="*", s=250, color="#c0392b",
               zorder=5, label=nombre)
    ax.plot([], [], color="#e39b2d", label="Hojas revisadas: %d" % len(hojas_revisadas))
    ax.set_xlim(centro[0] / 1000 - margen, centro[0] / 1000 + margen)
    ax.set_ylim(centro[1] / 1000 - margen, centro[1] / 1000 + margen)
    ax.set_aspect("equal")
    ax.set_title("Búsqueda por radio (%d m) — fuerza bruta encuentra %d puntos: %s"
                 % (radio, len(esperado), "COINCIDE" if coinciden else "NO COINCIDE"))
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_GRAFICAS, "busqueda_radio.png"), dpi=150)
    plt.close(fig)

    # 3. Vecinos más cercanos ---------------------------------------------------
    rng = random.Random(3)
    ubicaciones = [("Universidad de Antioquia", centro)] + [
        ("Ubicación aleatoria %d" % (i + 1), (rng.uniform(-5000, 3000), rng.uniform(-7000, 3000)))
        for i in range(3)]
    k = 10
    fig, ejes = plt.subplots(2, 2, figsize=(12, 12))
    for ax, (nombre, consulta) in zip(ejes.flat, ubicaciones):
        vecinos = arbol.k_vecinos_mas_cercanos(consulta, k)
        visitados = arbol.nodos_visitados
        esperado = bruta.k_vecinos_mas_cercanos(consulta, k)
        coinciden = all(abs(a - b) < 1e-9 for a, b in zip(distancias(vecinos), distancias(esperado)))
        d_max = vecinos[-1][0]
        cx, cy = consulta[0] / 1000, consulta[1] / 1000
        margen = max(3 * d_max, 150) / 1000
        ax.scatter(xs, ys, s=6, color="#b8b8b8")
        for d, p, _ in vecinos[1:]:
            ax.plot([cx, p[0] / 1000], [cy, p[1] / 1000], color="#4a7ab5", linewidth=0.8)
        ax.scatter([p[0] / 1000 for _, p, _ in vecinos[1:]], [p[1] / 1000 for _, p, _ in vecinos[1:]],
                   s=25, color="#4a7ab5", label="%d vecinos más cercanos" % k, zorder=3)
        d0, p0, id0 = vecinos[0]
        ax.plot([cx, p0[0] / 1000], [cy, p0[1] / 1000], color="#2a7a3b", linewidth=2)
        ax.scatter([p0[0] / 1000], [p0[1] / 1000], s=70, color="#2a7a3b", zorder=4,
                   label="Más cercano: id %d a %.1f m" % (id0, d0))
        ax.add_patch(Circle((cx, cy), d_max / 1000, fill=False, linestyle="--",
                            edgecolor="#7f7f7f", label="Distancia al %d-ésimo: %.1f m" % (k, d_max)))
        ax.scatter([cx], [cy], marker="*", s=200, color="#c0392b", zorder=5, label="Consulta")
        ax.set_xlim(cx - margen, cx + margen)
        ax.set_ylim(cy - margen, cy + margen)
        ax.set_aspect("equal")
        ax.set_title("%s\nnodos visitados: %d de %d — fuerza bruta: %s"
                     % (nombre, visitados, arbol.cantidad_nodos(),
                        "COINCIDE" if coinciden else "NO COINCIDE"), fontsize=10)
        ax.set_xlabel("x (km)")
        ax.set_ylabel("y (km)")
        ax.legend(loc="upper right", fontsize=7)
    fig.suptitle("Verificación visual de los vecinos más cercanos (k=%d)" % k)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_GRAFICAS, "vecinos_mas_cercanos.png"), dpi=150)
    plt.close(fig)

    print("Gráficas guardadas en %s" % CARPETA_GRAFICAS)


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
    generar_visualizaciones()

"""
Laboratorio 4 - Sistema de logística de entregas.

Quadtree hecho desde cero, para K dimensiones: en 2D cada caja se parte en 4,
en 3D en 8 y, en general, en 2^K. También incluye la búsqueda por fuerza bruta
(recorrer la lista completa) para comparar resultados y tiempos.

Unidades: todo se trabaja en METROS. Las coordenadas GPS (latitud, longitud)
se convierten a metros con `latlon_a_metros`, así "a 500 metros" es radio = 500.
"""

import csv
import math
import os
import random


def distancia(a, b):
    """Distancia en línea recta entre dos puntos de K dimensiones:
    raíz de la suma de las diferencias al cuadrado. En 2D: √((x1-x2)² + (y1-y2)²)."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


# ---------------------------------------------------------------------------
# Caja: el rectángulo (o cubo, o hiper-cubo) que cubre cada nodo
# ---------------------------------------------------------------------------

class Caja:
    """Una caja definida por su esquina mínima y su esquina máxima.
    Ejemplo en 2D: Caja((0, 0), (10, 10)) es el cuadrado de 0 a 10 en x y en y."""

    def __init__(self, minimo, maximo):
        if len(minimo) != len(maximo) or any(lo > hi for lo, hi in zip(minimo, maximo)):
            raise ValueError("la caja no es válida")
        self.minimo = tuple(minimo)
        self.maximo = tuple(maximo)
        self.centro = tuple((lo + hi) / 2 for lo, hi in zip(minimo, maximo))

    def contiene(self, punto):
        """¿El punto está dentro de la caja (bordes incluidos)?"""
        return all(lo <= x <= hi for lo, x, hi in zip(self.minimo, punto, self.maximo))

    def distancia_minima(self, punto):
        """Distancia desde el punto hasta el lugar más cercano de la caja (0 si está dentro).
        Por cada coordenada se busca la de la caja más cercana, "pegándola" a los bordes."""
        total = 0
        for lo, x, hi in zip(self.minimo, punto, self.maximo):
            cercana = min(max(x, lo), hi)   # si x está entre lo y hi, es la misma x
            total += (x - cercana) ** 2
        return math.sqrt(total)

    def subdividir(self):
        """Parte la caja por el centro en todas las dimensiones.
        Cada dimensión duplica las cajas: 1 -> 2 -> 4 en 2D (-> 8 en 3D)."""
        partes = [([], [])]  # (esquina mínima, esquina máxima) que se van armando
        for lo, c, hi in zip(self.minimo, self.centro, self.maximo):
            nuevas = []
            for minimo, maximo in partes:
                nuevas.append((minimo + [lo], maximo + [c]))   # mitad de abajo
                nuevas.append((minimo + [c], maximo + [hi]))   # mitad de arriba
            partes = nuevas
        return [Caja(minimo, maximo) for minimo, maximo in partes]


# ---------------------------------------------------------------------------
# Nodo y Quadtree
# ---------------------------------------------------------------------------

class Nodo:
    """Un nodo del árbol. Si no tiene hijos es una hoja y guarda puntos;
    si tiene hijos, sus puntos ya se repartieron entre ellos."""

    def __init__(self, caja, profundidad):
        self.caja = caja
        self.profundidad = profundidad
        self.puntos = []   # lista de (punto, dato); el dato es el id del punto de entrega
        self.hijos = []

    def es_hoja(self):
        return len(self.hijos) == 0

    def hijo_que_contiene(self, punto):
        for hijo in self.hijos:
            if hijo.caja.contiene(punto):
                return hijo

    def todos_los_nodos(self):
        """Este nodo y todos los que tiene debajo."""
        lista = [self]
        for hijo in self.hijos:
            lista += hijo.todos_los_nodos()
        return lista


class Quadtree:
    """capacidad: máximo de puntos en una hoja antes de partirla.
    profundidad_maxima: evita partir sin fin cuando hay muchos puntos repetidos."""

    def __init__(self, limites_min, limites_max, capacidad=8, profundidad_maxima=24):
        self.raiz = Nodo(Caja(limites_min, limites_max), 0)
        self.capacidad = capacidad
        self.profundidad_maxima = profundidad_maxima
        self.tamano = 0
        self.nodos_visitados = 0   # cuántos nodos revisó la última búsqueda (para las gráficas)

    def __len__(self):
        return self.tamano

    # -- Insertar ------------------------------------------------------------

    def insertar(self, punto, dato=None):
        punto = tuple(punto)
        if len(punto) != len(self.raiz.caja.minimo) or not self.raiz.caja.contiene(punto):
            raise ValueError("el punto %s no cabe en el árbol" % (punto,))
        self._insertar(self.raiz, punto, dato)
        self.tamano += 1

    def _insertar(self, nodo, punto, dato):
        # Si no es hoja, el punto baja al hijo cuya caja lo contiene.
        if not nodo.es_hoja():
            self._insertar(nodo.hijo_que_contiene(punto), punto, dato)
            return
        nodo.puntos.append((punto, dato))
        # Si la hoja se pasó de la capacidad, se parte en 2^K hijos.
        if len(nodo.puntos) > self.capacidad and nodo.profundidad < self.profundidad_maxima:
            self._partir(nodo)

    def _partir(self, nodo):
        nodo.hijos = [Nodo(caja, nodo.profundidad + 1) for caja in nodo.caja.subdividir()]
        puntos = nodo.puntos
        nodo.puntos = []
        # Se vuelven a insertar: ahora cada uno baja a su hijo (y si un hijo
        # también se llena, se parte solo, por la misma regla).
        for punto, dato in puntos:
            self._insertar(nodo, punto, dato)

    # -- Búsqueda en un radio ------------------------------------------------

    def vecinos_en_radio(self, centro, radio):
        """Puntos a distancia <= radio del centro, del más cercano al más lejano.
        Cada resultado es (distancia, punto, dato)."""
        self.nodos_visitados = 0
        encontrados = []
        if self.raiz.caja.distancia_minima(centro) <= radio:
            self._buscar_en_radio(self.raiz, centro, radio, encontrados)
        encontrados.sort(key=lambda r: r[0])
        return encontrados

    def _buscar_en_radio(self, nodo, centro, radio, encontrados):
        self.nodos_visitados += 1
        for punto, dato in nodo.puntos:   # solo las hojas tienen puntos
            d = distancia(punto, centro)
            if d <= radio:
                encontrados.append((d, punto, dato))
        for hijo in nodo.hijos:           # solo los nodos internos tienen hijos
            # Poda: si la caja del hijo está más lejos que el radio, ningún punto de adentro sirve.
            if hijo.caja.distancia_minima(centro) <= radio:
                self._buscar_en_radio(hijo, centro, radio, encontrados)

    # -- Vecinos más cercanos ------------------------------------------------

    def k_vecinos_mas_cercanos(self, consulta, k=1):
        """Los k puntos más cercanos a la consulta, ordenados. Cada uno es (distancia, punto, dato)."""
        self.nodos_visitados = 0
        mejores = []
        if k > 0:
            self._buscar_vecinos(self.raiz, consulta, k, mejores)
        return mejores

    def _buscar_vecinos(self, nodo, consulta, k, mejores):
        self.nodos_visitados += 1
        for punto, dato in nodo.puntos:
            agregar_candidato(mejores, (distancia(punto, consulta), punto, dato), k)
        # Primero los hijos más cercanos: así aparecen buenos candidatos pronto y se poda más.
        hijos = sorted(nodo.hijos, key=lambda hijo: hijo.caja.distancia_minima(consulta))
        for hijo in hijos:
            # Poda: si ya hay k candidatos y este hijo está más lejos que el peor de ellos
            # (el último de la lista), no puede aportar nada. Como los hijos van
            # ordenados por cercanía, los que siguen tampoco: se termina el ciclo.
            if len(mejores) == k and hijo.caja.distancia_minima(consulta) > mejores[-1][0]:
                break
            self._buscar_vecinos(hijo, consulta, k, mejores)

    def vecino_mas_cercano(self, consulta):
        """(distancia, punto, dato) del más cercano, o None si el árbol está vacío."""
        vecinos = self.k_vecinos_mas_cercanos(consulta, 1)
        if vecinos:
            return vecinos[0]
        return None

    # -- Para inspeccionar el árbol (pruebas y gráficas) -----------------------

    def nodos(self):
        return self.raiz.todos_los_nodos()

    def cantidad_nodos(self):
        return len(self.nodos())

    def profundidad(self):
        return max(nodo.profundidad for nodo in self.nodos())


def agregar_candidato(mejores, candidato, k):
    """Mantiene en `mejores` los k candidatos más cercanos, ordenados por distancia.
    Lo usan el árbol y la fuerza bruta."""
    if len(mejores) < k or candidato[0] < mejores[-1][0]:
        mejores.append(candidato)
        mejores.sort(key=lambda r: r[0])
        del mejores[k:]   # si quedaron k + 1, se borra el peor


def construir_quadtree(puntos, datos=None, capacidad=8):
    """Crea un Quadtree con la caja justa para los puntos y los inserta todos."""
    if datos is None:
        datos = list(range(len(puntos)))   # si no hay ids, se usa la posición
    dimension = len(puntos[0])
    minimo = [min(p[d] for p in puntos) for d in range(dimension)]
    maximo = [max(p[d] for p in puntos) for d in range(dimension)]
    arbol = Quadtree(minimo, maximo, capacidad)
    for punto, dato in zip(puntos, datos):
        arbol.insertar(punto, dato)
    return arbol


# ---------------------------------------------------------------------------
# Fuerza bruta: recorrer la lista completa en cada consulta
# ---------------------------------------------------------------------------

class FuerzaBruta:

    def __init__(self, puntos, datos=None):
        if datos is None:
            datos = list(range(len(puntos)))
        self.puntos = list(zip(puntos, datos))

    def vecinos_en_radio(self, centro, radio):
        encontrados = []
        for punto, dato in self.puntos:
            d = distancia(punto, centro)
            if d <= radio:
                encontrados.append((d, punto, dato))
        encontrados.sort(key=lambda r: r[0])
        return encontrados

    def k_vecinos_mas_cercanos(self, consulta, k=1):
        mejores = []
        if k > 0:
            for punto, dato in self.puntos:
                agregar_candidato(mejores, (distancia(punto, consulta), punto, dato), k)
        return mejores

    def vecino_mas_cercano(self, consulta):
        vecinos = self.k_vecinos_mas_cercanos(consulta, 1)
        if vecinos:
            return vecinos[0]
        return None


# ---------------------------------------------------------------------------
# Datos: puntos de entrega (estáticos) y conversión de unidades
# ---------------------------------------------------------------------------

RADIO_TIERRA_M = 6371008.8   # radio medio de la Tierra en metros

# Punto de referencia (el (0, 0) del mapa en metros): Parque Berrío, centro de Medellín.
LAT_REFERENCIA = 6.2518
LON_REFERENCIA = -75.5636

# Zonas con muchos pedidos: (lat, lon, dispersión en metros, fracción de los puntos).
ZONAS_ENTREGA = [
    (6.2518, -75.5636, 900, 0.20),   # Centro
    (6.2088, -75.5672, 700, 0.15),   # El Poblado
    (6.2447, -75.5906, 800, 0.12),   # Laureles
    (6.2680, -75.5680, 600, 0.10),   # Ciudad Universitaria / Aranjuez
    (6.2300, -75.6050, 700, 0.08),   # Belén
    (6.2920, -75.5560, 700, 0.08),   # Manrique / Castilla
    (6.1750, -75.5900, 800, 0.07),   # Envigado / Sabaneta
]
# El 20 % restante de los puntos cae al azar dentro de la ciudad.
LIMITES_CIUDAD = (6.16, 6.32, -75.62, -75.53)   # lat_min, lat_max, lon_min, lon_max


def latlon_a_metros(lat, lon):
    """Grados -> metros respecto al punto de referencia (x hacia el este, y hacia el norte).
    Un grado de longitud mide menos que uno de latitud; el coseno corrige eso."""
    x = math.radians(lon - LON_REFERENCIA) * math.cos(math.radians(LAT_REFERENCIA)) * RADIO_TIERRA_M
    y = math.radians(lat - LAT_REFERENCIA) * RADIO_TIERRA_M
    return x, y


def metros_a_latlon(x, y):
    """La conversión inversa: metros -> grados."""
    lat = LAT_REFERENCIA + math.degrees(y / RADIO_TIERRA_M)
    lon = LON_REFERENCIA + math.degrees(x / (RADIO_TIERRA_M * math.cos(math.radians(LAT_REFERENCIA))))
    return lat, lon


def generar_puntos_entrega(n, semilla=42):
    """Genera n puntos de entrega simulados en Medellín. Devuelve (id, lat, lon, x, y)."""
    rng = random.Random(semilla)   # misma semilla = mismos puntos siempre
    lat_min, lat_max, lon_min, lon_max = LIMITES_CIUDAD
    pesos = [zona[3] for zona in ZONAS_ENTREGA]
    registros = []
    while len(registros) < n:
        if rng.random() < 0.20:
            # 20 %: un punto al azar en cualquier parte de la ciudad
            lat = rng.uniform(lat_min, lat_max)
            lon = rng.uniform(lon_min, lon_max)
        else:
            # 80 %: un punto alrededor del centro de una zona con muchos pedidos
            lat_zona, lon_zona, dispersion, _ = rng.choices(ZONAS_ENTREGA, weights=pesos)[0]
            cx, cy = latlon_a_metros(lat_zona, lon_zona)
            lat, lon = metros_a_latlon(rng.gauss(cx, dispersion), rng.gauss(cy, dispersion))
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:   # si se salió de la ciudad, se descarta
            x, y = latlon_a_metros(lat, lon)
            registros.append((len(registros), lat, lon, x, y))
    return registros


RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "puntos_entrega.csv")


def cargar_puntos_entrega(ruta=RUTA_DATOS):
    """Lee los 10.000 puntos del CSV. Si el CSV no existe, lo crea una sola vez:
    así todas las ejecuciones usan exactamente los mismos datos."""
    if not os.path.exists(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["id", "lat", "lon", "x_m", "y_m"])
            for id_, lat, lon, x, y in generar_puntos_entrega(10000):
                escritor.writerow([id_, "%.7f" % lat, "%.7f" % lon, "%.3f" % x, "%.3f" % y])
    with open(ruta, newline="") as archivo:
        return [(int(fila["id"]), float(fila["lat"]), float(fila["lon"]), float(fila["x_m"]), float(fila["y_m"]))
                for fila in csv.DictReader(archivo)]


def generar_puntos_aleatorios(n, dimension=2, lado=10000.0, semilla=None):
    """Puntos al azar en un cubo de K dimensiones (para las pruebas en 1D, 3D, 4D, 5D)."""
    rng = random.Random(semilla)
    return [tuple(rng.uniform(0, lado) for _ in range(dimension)) for _ in range(n)]


if __name__ == "__main__":
    registros = cargar_puntos_entrega()
    puntos = [(x, y) for _, _, _, x, y in registros]
    ids = [r[0] for r in registros]
    arbol = construir_quadtree(puntos, ids)
    print("Puntos: %d | nodos: %d | profundidad: %d" % (len(arbol), arbol.cantidad_nodos(), arbol.profundidad()))

    udea = latlon_a_metros(6.2675, -75.5689)   # Universidad de Antioquia
    print("Puntos a 500 m o menos de la UdeA: %d" % len(arbol.vecinos_en_radio(udea, 500)))
    d, punto, id_ = arbol.vecino_mas_cercano(udea)
    print("Más cercano: id %d a %.1f m" % (id_, d))

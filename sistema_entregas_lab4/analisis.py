"""
analisis.py
Métricas de rendimiento del Quadtree frente a fuerza bruta (listas) y discusión de resultados.

Experimento: tiempo por consulta (radio de 500 m y vecino más cercano) variando N,
para el Quadtree y para fuerza bruta con listas (misma función de distancia).

Responde: ¿para qué tamaño de datos el Quadtree comienza a ser más rápido que
fuerza bruta?

Ejecución:
    python analisis.py   -> imprime la tabla, la discusión y guarda la gráfica en graficas/
"""

import gc
import math
import os
import statistics
import time

from sistema_entregas_lab4.Quadtree import FuerzaBruta, construir_quadtree, generar_puntos_entrega

CARPETA_GRAFICAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficas")

TAMANOS = [2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
RADIO_M = 500
REPETICIONES = 5
CAPACIDAD = 8

# Paleta (series en orden fijo) y tintas de texto.
COLOR_QUADTREE = "#2a78d6"
COLOR_LISTA = "#eb6834"
TEXTO_PRIMARIO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
SUPERFICIE = "#fcfcfb"


def consultas_en_ciudad(q, semilla):
    """Ubicaciones de consulta en metros, con la misma distribución de demanda que los
    puntos de entrega (zonas densas + ruido uniforme), pero independientes de ellos."""
    return [(x, y) for _, _, _, x, y in generar_puntos_entrega(q, semilla=semilla)]


def cronometrar(funcion, consultas, repeticiones=REPETICIONES):
    """Media y desviación estándar (en segundos) del tiempo POR CONSULTA.
    El recolector de basura se desactiva durante la medición (como hace timeit)
    para que sus pausas no aparezcan como picos aleatorios."""
    muestras = []
    gc.disable()
    try:
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            for c in consultas:
                funcion(c)
            muestras.append((time.perf_counter() - inicio) / len(consultas))
    finally:
        gc.enable()
    return statistics.mean(muestras), statistics.stdev(muestras)


def numero_consultas(n):
    # Más consultas para N pequeño (tiempos muy cortos, más ruido), menos para N grande.
    return max(30, min(1000, 300000 // n))


def punto_de_cruce(tamanos, t_arbol, t_bruta):
    """N a partir del cual el árbol es más rápido en TODAS las mediciones siguientes,
    interpolando en escala log-log entre las dos mediciones que rodean ese último
    cruce. Devuelve None si el árbol no es más rápido ni siquiera en el N mayor."""
    i = len(tamanos)
    while i > 0 and t_arbol[i - 1] < t_bruta[i - 1]:
        i -= 1
    if i == len(tamanos):
        return None
    if i == 0:
        return tamanos[0]
    # diferencia en log entre las curvas antes (>= 0) y después (< 0) del cruce
    g0 = math.log(t_arbol[i - 1]) - math.log(t_bruta[i - 1])
    g1 = math.log(t_arbol[i]) - math.log(t_bruta[i])
    fraccion = g0 / (g0 - g1)
    log_n = math.log(tamanos[i - 1]) + fraccion * (math.log(tamanos[i]) - math.log(tamanos[i - 1]))
    return math.exp(log_n)


# ---------------------------------------------------------------------------
# Experimento
# ---------------------------------------------------------------------------

def experimento_tamanos():
    resultados = []
    print("Tiempo por consulta vs N (radio=%d m, %d repeticiones)" % (RADIO_M, REPETICIONES))
    print("%7s %6s | %11s %11s | %11s %11s | %8s"
          % ("N", "Q", "QT radio", "Lista radio", "QT NN", "Lista NN", "Prom. r"))
    for n in TAMANOS:
        puntos = [(x, y) for _, _, _, x, y in generar_puntos_entrega(n, semilla=n)]
        consultas = consultas_en_ciudad(numero_consultas(n), semilla=-1)
        arbol = construir_quadtree(puntos, capacidad=CAPACIDAD)
        lista = FuerzaBruta(puntos)

        fila = {
            "n": n,
            "q": len(consultas),
            "qt_radio": cronometrar(lambda c: arbol.vecinos_en_radio(c, RADIO_M), consultas),
            "lista_radio": cronometrar(lambda c: lista.vecinos_en_radio(c, RADIO_M), consultas),
            "qt_nn": cronometrar(arbol.vecino_mas_cercano, consultas),
            "lista_nn": cronometrar(lista.vecino_mas_cercano, consultas),
            "encontrados": statistics.mean(len(arbol.vecinos_en_radio(c, RADIO_M)) for c in consultas),
        }
        resultados.append(fila)
        us = lambda clave: fila[clave][0] * 1e6
        print("%7d %6d | %9.1fus %9.1fus | %9.1fus %9.1fus | %8.1f"
              % (n, fila["q"], us("qt_radio"), us("lista_radio"),
                 us("qt_nn"), us("lista_nn"), fila["encontrados"]))
    return resultados


# ---------------------------------------------------------------------------
# Gráfica
# ---------------------------------------------------------------------------

def preparar_estilo(plt):
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
        "axes.edgecolor": "#c9c8c3", "axes.labelcolor": TEXTO_SECUNDARIO,
        "xtick.color": TEXTO_SECUNDARIO, "ytick.color": TEXTO_SECUNDARIO,
        "text.color": TEXTO_PRIMARIO, "axes.titlecolor": TEXTO_PRIMARIO,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
        "lines.linewidth": 2, "lines.markersize": 5,
    })


def graficar_tiempos(plt, resultados, cruces):
    tamanos = [f["n"] for f in resultados]
    fig, ejes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, tipo, titulo in ((ejes[0], "radio", "Búsqueda en radio de %d m" % RADIO_M),
                             (ejes[1], "nn", "Vecino más cercano")):
        series = (("qt", "Quadtree", COLOR_QUADTREE),
                  ("lista", "Fuerza bruta (listas)", COLOR_LISTA))
        for clave, nombre, color in series:
            medias = [f["%s_%s" % (clave, tipo)][0] * 1e6 for f in resultados]
            desv = [f["%s_%s" % (clave, tipo)][1] * 1e6 for f in resultados]
            ax.plot(tamanos, medias, marker="o", color=color, label=nombre)
            ax.fill_between(tamanos, [m - d for m, d in zip(medias, desv)],
                            [m + d for m, d in zip(medias, desv)], color=color, alpha=0.15, linewidth=0)
            ax.annotate(nombre, (tamanos[-1], medias[-1]), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=8, color=TEXTO_SECUNDARIO)
        cruce = cruces[tipo]
        if cruce:
            ax.axvline(cruce, color=TEXTO_SECUNDARIO, linestyle="--", linewidth=1)
            ax.annotate("Quadtree < listas\ndesde N ≈ %d" % round(cruce), (cruce, ax.get_ylim()[1]),
                        xytext=(6, -6), textcoords="offset points", va="top", fontsize=8,
                        color=TEXTO_SECUNDARIO)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(tamanos[0] * 0.8, tamanos[-1] * 4)
        ax.set_title(titulo)
        ax.set_xlabel("N (puntos de entrega)")
        ax.set_ylabel("Tiempo por consulta (µs, escala log)")
        ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.suptitle("Quadtree vs fuerza bruta: tiempo por consulta (media ± desviación, %d repeticiones)"
                 % REPETICIONES)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_GRAFICAS, "tiempos_consulta.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Discusión
# ---------------------------------------------------------------------------

def imprimir_discusion(resultados, cruces):
    fila_10k = next(f for f in resultados if f["n"] == 10000)
    speedup = lambda tipo: fila_10k["lista_" + tipo][0] / fila_10k["qt_" + tipo][0]
    formato = lambda c: ("N ≈ %d" % round(c)) if c else "no se alcanza en el rango medido"

    print("""
========================================================================
DISCUSIÓN DE RESULTADOS
========================================================================
1. ¿Desde qué tamaño el Quadtree es más rápido que fuerza bruta (listas)?
   - Búsqueda en radio de %d m:  %s
   - Vecino más cercano:         %s
   Con N <= capacidad (%d) el árbol es una sola hoja: hace el mismo
   recorrido lineal que la lista y además paga la pila / cola de prioridad
   y la distancia a las cajas. En el vecino más cercano ese sobrecosto lo
   hace más lento hasta el cruce. En la búsqueda por radio el árbol gana
   incluso con N muy pequeño porque una sola comprobación contra la caja
   raíz descarta las consultas que quedan lejos de todos los puntos (a
   esos tamaños las diferencias son de ~1 µs, del orden del ruido de
   medición). A partir del cruce, la poda descarta ramas completas y el
   costo por consulta crece aprox. como O(log N + m) (m = puntos
   encontrados), mientras que la lista crece como O(N).

2. Con los 10.000 puntos del enunciado el Quadtree es %.0fx más rápido en
   la búsqueda por radio y %.0fx en el vecino más cercano. La ventaja es
   mayor en el vecino más cercano porque su resultado es un solo punto;
   en la búsqueda por radio el árbol igual debe recorrer los ~%.0f puntos
   que caen dentro de los 500 m (el término m no se puede podar).
========================================================================"""
          % (RADIO_M, formato(cruces["radio"]), formato(cruces["nn"]), CAPACIDAD,
             speedup("radio"), speedup("nn"), fila_10k["encontrados"]))


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(CARPETA_GRAFICAS, exist_ok=True)
    resultados = experimento_tamanos()
    tamanos = [f["n"] for f in resultados]
    cruces = {tipo: punto_de_cruce(tamanos, [f["qt_" + tipo][0] for f in resultados],
                                   [f["lista_" + tipo][0] for f in resultados])
              for tipo in ("radio", "nn")}

    preparar_estilo(plt)
    graficar_tiempos(plt, resultados, cruces)
    imprimir_discusion(resultados, cruces)
    print("\nGráfica guardada en %s" % CARPETA_GRAFICAS)

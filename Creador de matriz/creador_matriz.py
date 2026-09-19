import numpy as np
import os

filas = 100000
# 12.500 bytes de datos + 1 byte para el salto de línea
columnas_bytes = (100000 // 8) + 1 
nombre_archivo = 'matriz_bits_separada.dat'

# Creamos el memmap con el byte adicional por fila
matriz_disco = np.memmap(nombre_archivo, dtype='uint8', mode='w+', shape=(filas, columnas_bytes))

tamano_bloque = 1000

print("Generando y empaquetando matriz con saltos de línea...")
for i in range(0, filas, tamano_bloque):
    # 1. Generamos los booleanos
    bloque_bits = np.random.randint(0, 2, size=(tamano_bloque, 100000), dtype=bool)
    
    # 2. Comprimimos a bytes (matriz temporal de 1000 x 12500)
    bloque_comprimido = np.packbits(bloque_bits, axis=1)
    
    # 3. Creamos una columna de separadores (el valor 10 es '\n' en código ASCII)
    columna_saltos = np.full((tamano_bloque, 1), 10, dtype='uint8')
    
    # 4. Unimos los datos comprimidos con la columna de saltos al final
    bloque_final = np.hstack((bloque_comprimido, columna_saltos))
    
    # 5. Guardamos el bloque exacto de 12501 columnas en el disco
    matriz_disco[i:i + tamano_bloque, :] = bloque_final

matriz_disco.flush()
print("¡Matriz empaquetada con separadores creada con éxito!\n")

print(f"Dimensiones reales en disco: {matriz_disco.shape}")
print(f"Peso final del archivo: {os.path.getsize(nombre_archivo) / (1024**3):.2f} GB")
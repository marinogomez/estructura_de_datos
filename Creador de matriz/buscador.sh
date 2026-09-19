#!/bin/bash

# Buscador de submatrices en bash - Acceso Aleatorio O(1)
# Versión compatible con macOS (BSD)

# OJO AQUÍ: Ajusté el nombre y los bytes para que coincida con tu último código de Python
ARCHIVO="matriz_bits_separada.dat" 
FILAS=100000
COLUMNAS=100000
BYTES_POR_FILA=12501  # 12500 de datos + 1 del separador \n

if [ ! -f "$ARCHIVO" ]; then
    echo "❌ Error: No se encontró el archivo '$ARCHIVO'."
    exit 1
fi

echo "=================================================="
echo "   VISUALIZADOR DE SUBMATRIZ (100k x 100k)      "
echo "   Bash Edition - macOS Compatible               "
echo "=================================================="

read -p "Ingresa la FILA de inicio (0 a 99999): " f_inicio
read -p "Ingresa la COLUMNA de inicio (0 a 99999): " c_inicio

if ! [[ "$f_inicio" =~ ^[0-9]+$ ]] || ! [[ "$c_inicio" =~ ^[0-9]+$ ]]; then
    echo "❌ Ingresa únicamente números enteros."
    exit 1
fi

n_filas_muestra=10
n_columnas_muestra=10

f_fin=$((f_inicio + n_filas_muestra))
c_fin=$((c_inicio + n_columnas_muestra))

if [ $f_fin -gt $FILAS ] || [ $c_fin -gt $COLUMNAS ]; then
    echo "❌ Error: La ventana se pasa del límite de 100.000."
    exit 1
fi

byte_inicio=$((c_inicio / 8))
byte_fin=$(((c_fin + 7) / 8))
num_bytes=$((byte_fin - byte_inicio))
desplazamiento_bit=$((c_inicio % 8))

echo ""
echo "--- Cuadrícula desde Fila $f_inicio, Columna $c_inicio ---"
echo ""

for ((fila = f_inicio; fila < f_fin; fila++)); do
    offset=$((fila * BYTES_POR_FILA + byte_inicio))
    
    # LA SOLUCIÓN: Agregamos tr 'a-z' 'A-Z' para que macOS entienda los números hexadecimales
    datos_hex=$(od -j $offset -N $num_bytes -An -tx1 "$ARCHIVO" 2>/dev/null | tr -d ' \n' | tr 'a-z' 'A-Z')
    
    bits=""
    for ((i=0; i<${#datos_hex}; i+=2)); do
        byte_hex="${datos_hex:$i:2}"
        byte_dec=$((16#$byte_hex))
        
        byte_bin=$(printf "%08d" $(echo "obase=2; ibase=10; $byte_dec" | bc 2>/dev/null) 2>/dev/null)
        
        if [ -z "$byte_bin" ] || [ "$byte_bin" == "00000000" -a "$byte_dec" != "0" ]; then
            byte_bin=""
            for ((bit=7; bit>=0; bit--)); do
                byte_bin+=$(( (byte_dec >> bit) & 1 ))
            done
        fi
        
        bits="${bits}${byte_bin}"
    done
    
    fila_visual="${bits:$desplazamiento_bit:$n_columnas_muestra}"
    echo "$fila_visual" | sed 's/./& /g'
done

echo ""
echo "--------------------------------------------------"
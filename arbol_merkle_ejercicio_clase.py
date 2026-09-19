import hashlib

def hash_node(data):
    """Genera un hash SHA-256 de una cadena de texto."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def build_merkle_tree(transactions):
    if not transactions:
        return None

    print(f"--- Construyendo Árbol de Merkle para {len(transactions)} transacciones ---")
    
    # Hashear las hojas iniciales
    current_level = [hash_node(tx) for tx in transactions]
    
    level_count = 1
    # Construir niveles superiores hasta llegar a 1 solo nodo (la raíz)
    while len(current_level) > 1:
        print(f"\n--- Procesando Nivel {level_count} ({len(current_level)} nodos) ---")
        next_level = []
        
        for i in range(0, len(current_level), 2):
            node_left = current_level[i]
            
            # Verificar si hay un nodo derecho para emparejar
            if i + 1 < len(current_level):
                node_right = current_level[i + 1]
            else:
                # Duplicar el nodo izquierdo si es el último e impar
                node_right = current_level[i] 
                print(f"[*] Nodo impar detectado. Duplicando hash para mantener la estructura binaria.")
            
            # Concatenar y hashear el par
            combined = node_left + node_right
            next_level.append(hash_node(combined))
        
        current_level = next_level
        level_count += 1

    return current_level[0]

# ==========================================
# CONFIGURACIÓN DE NODOS
# ==========================================
# Define la cantidad de transacciones que desees aquí:
N = 5

# Genera dinámicamente la lista ["Tx1", "Tx2", ..., "TxN"]
txs = [f"Tx{i}" for i in range(1, N + 1)]

print(f"Transacciones a procesar: {txs[:5]} ... (Mostrando las primeras 5 de {N})")

merkle_root = build_merkle_tree(txs)
print(f"\n=== RAÍZ DE MERKLE FINAL ===")
print(merkle_root)
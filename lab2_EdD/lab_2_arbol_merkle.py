import hashlib

# ==========================================
# FUNCIONES AUXILIARES DE CRIPTOGRAFÍA
# ==========================================

def hash_data(data):
    """
    Genera el hash SHA-256 de una cadena de texto simple (Transacción base).
    Se utiliza para crear el 'Nivel 0' o las hojas del árbol.
    - data.encode('utf-8'): Convierte el string a bytes, requisito de hashlib.
    - hexdigest(): Devuelve el hash en formato hexadecimal (cadena de 64 caracteres).
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def hash_pair(left, right):
    """
    Genera el hash SHA-256 de la concatenación de dos nodos hijos (izquierdo y derecho).
    Se utiliza para construir los nodos internos y subir de nivel en el árbol.
    """
    return hashlib.sha256((left + right).encode('utf-8')).hexdigest()


# ==========================================
# CLASE PRINCIPAL: MerkleTree
# ==========================================
# Utilizamos Programación Orientada a Objetos (POO) para encapsular el estado del árbol.
# Esto permite guardar todos los niveles en memoria (en self.levels), lo cual es 
# necesario para generar Pruebas de Inclusión (Merkle Proofs) después 
# de haber construido el árbol, sin tener que recalcular todo desde cero.

class MerkleTree:
    def __init__(self, transactions):
        """
        Constructor de la clase. Se ejecuta al instanciar el árbol (ej: MerkleTree(txs)).
        - self.transactions: Guarda la lista original de datos.
        - self.levels: Matriz (lista de listas) que guardará los hashes piso por piso.
        - self._build_tree(): Llama automáticamente a la función que construye la estructura.
        """
        self.transactions = transactions
        self.levels = []
        self._build_tree()

    def _build_tree(self):
        """
        Motor principal del árbol. Transforma la lista de transacciones en una 
        estructura de hashes piramidal (niveles) hasta llegar a una sola raíz.
        """
        if not self.transactions:
            return

        # PASO 1: Crear las Hojas (Nivel 0)
        # Convierte cada transacción de texto en su respectivo hash criptográfico.
        current_level = [hash_data(tx) for tx in self.transactions]
        self.levels.append(current_level) # Guarda el nivel inferior en la matriz

        # PASO 2: Construir los nodos internos (Niveles superiores)
        # El bucle se repite mientras haya más de 1 hash en el nivel actual.
        # Cuando solo quede 1, significa que hemos llegado a la Raíz.
        while len(current_level) > 1:
            next_level = []
            
            # Recorremos el nivel actual saltando de 2 en 2 para formar las parejas
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                
                # REGLA DE DUPLICACIÓN: Un árbol binario necesita parejas exactas.
                # Si el nivel tiene una cantidad impar de hashes, el último se queda solo.
                # Para solucionarlo, verificamos si existe un nodo derecho (i + 1).
                # Si no existe, duplicamos el nodo izquierdo (right = left).
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Concatenamos la pareja, la hasheamos y la subimos al siguiente nivel
                next_level.append(hash_pair(left, right))
            
            self.levels.append(next_level) # Guardamos el nuevo piso en la matriz
            current_level = next_level     # Actualizamos la variable para la siguiente iteración

    def print_tree(self):
        """
        Función de utilidad visual. Recorre la matriz `self.levels` y la imprime en consola 
        para que podamos observar cómo se reducen los hashes nivel por nivel.
        Se truncan a 12 caracteres (h[:12]) puramente por estética en la terminal.
        """
        print("\n" + "="*50)
        print("      ESTRUCTURA INTERNA DEL ÁRBOL DE MERKLE      ")
        print("="*50)
        
        for i, level in enumerate(self.levels):
            # Identificamos semánticamente el nivel actual para la impresión
            if i == 0:
                level_name = "Nivel 0 (Hojas / Transacciones Base)"
            elif i == len(self.levels) - 1:
                level_name = f"Nivel {i} (Raíz de Merkle)"
            else:
                level_name = f"Nivel {i} (Nodos Internos)"
            
            print(f"\n{level_name}:")
            for j, h in enumerate(level):
                print(f"  └─ Nodo {j}: {h[:12]}...") 
                
        print("="*50 + "\n")

    def get_root(self):
        """
        Devuelve el primer (y único) elemento del último nivel guardado en la matriz.
        Esta es la Raíz de Merkle que representa la integridad de todos los datos.
        """
        return self.levels[-1][0] if self.levels else None

    def get_proof(self, index):
        """
        Genera una Prueba de Inclusión (Merkle Proof).
        Dado el índice de una transacción, busca cuáles son los hashes "hermanos" 
        exactos con los que se concatenó en cada nivel para llegar a la raíz.
        Retorna una lista de tuplas: (hash_del_hermano, 'left' o 'right')
        """
        proof = []
        if index < 0 or index >= len(self.transactions):
            return proof

        curr_index = index
        
        # Iteramos desde las hojas hasta el nivel justo debajo de la raíz ([:-1])
        for level in self.levels[:-1]:
            # Determinamos si nuestro nodo actual es el derecho o el izquierdo en su pareja.
            # Los índices pares (0, 2, 4) son nodos izquierdos. Impares (1, 3, 5) son derechos.
            is_right_node = curr_index % 2 != 0
            
            if is_right_node:
                sibling_index = curr_index - 1 # El hermano está a la izquierda
                pos = 'left'
            else:
                sibling_index = curr_index + 1 # El hermano está a la derecha
                pos = 'right'

            # Manejo del caso borde: si el hermano que necesitamos calcular cae fuera de rango
            # (es decir, nuestro nodo se duplicó a sí mismo porque era impar), el hermano somos nosotros mismos.
            if sibling_index >= len(level):
                sibling_index = curr_index

            # Guardamos el hash del hermano y su posición, necesarios para la verificación matemática
            proof.append((level[sibling_index], pos))
            
            # Subimos de nivel dividiendo el índice entre 2 (división entera).
            # Ej: Los nodos 2 y 3 del Nivel 0, ambos se convierten en el nodo 1 del Nivel 1.
            curr_index //= 2

        return proof


# ==========================================
# FUNCIÓN DE VERIFICACIÓN EXTERNA
# ==========================================

def verify_proof(target_data, proof, root):
    """
    Verifica matemáticamente que un dato pertenece al árbol SIN necesidad de tener 
    el árbol completo. Solo necesita el dato, la prueba (hermanos) y la raíz pública.
    """
    # 1. Hasheamos el dato sospechoso/a verificar
    current_hash = hash_data(target_data)
    
    # 2. Reconstruimos la ruta combinándolo con los hermanos provistos en la prueba
    for sibling_hash, pos in proof:
        if pos == 'left':
            # Si el hermano estaba a la izquierda, concatenamos: hermano + nuestro hash
            current_hash = hash_pair(sibling_hash, current_hash)
        else:
            # Si el hermano estaba a la derecha, concatenamos: nuestro hash + hermano
            current_hash = hash_pair(current_hash, sibling_hash)
            
    # 3. Si la reconstrucción resulta en la raíz original, el dato es 100% auténtico.
    return current_hash == root


# ==========================================
# BLOQUE DE EJECUCIÓN DEL EXPERIMENTO (LABORATORIO)
# ==========================================
# Este bloque solo se ejecuta si corremos el archivo directamente en la terminal.

if __name__ == "__main__":
    print("=== INICIANDO EXPERIMENTO ===")
    
    # [1] Inicialización de datos
    txs = ["Tx1", "Tx2", "Tx3", "Tx4", "Tx5"]
    print(f"\n[+] Transacciones base: {txs}")
    
    # [2] Construcción y visualización del árbol íntegro
    tree = MerkleTree(txs)
    tree.print_tree()
    root = tree.get_root()
    print(f"[+] Raíz de Merkle Original: {root}")

    # [3] Demostración de sensibilidad (Efecto Avalancha)
    # Cambiar un solo carácter altera completamente la raíz final.
    txs_mod = ["Tx1", "Tx2", "Tx3_MODIFICADA", "Tx4", "Tx5"]
    tree_mod = MerkleTree(txs_mod)
    root_mod = tree_mod.get_root()
    
    print("\n[!] Modificando Tx3 -> 'Tx3_MODIFICADA'")
    print(f"[+] Nueva Raíz: {root_mod}")
    print(f"[+] ¿La raíz cambió?: {root != root_mod}")

    # [4] Generación de la Prueba de Inclusión para un nodo específico (Índice 2 = Tx3)
    target_idx = 2
    target_tx = txs[target_idx]
    proof = tree.get_proof(target_idx)
    
    print(f"\n[*] Generando prueba de inclusión para '{target_tx}'")
    for i, (h, p) in enumerate(proof):
        print(f"    Nivel {i}: Hermano {p} -> {h[:12]}...")

    # [5] Verificación Positiva: El dato original coincide perfectamente con la ruta.
    is_valid = verify_proof(target_tx, proof, root)
    print(f"\n[v] Verificación con dato CORRECTO ('{target_tx}'): {is_valid}")

    # [6] Verificación Negativa: Un dato falso genera hashes intermedios erróneos,
    # resultando en una raíz diferente y por ende una verificación fallida.
    is_valid_fake = verify_proof("Tx3_FALSA", proof, root)
    print(f"[x] Verificación con dato INCORRECTO ('Tx3_FALSA'): {is_valid_fake}")
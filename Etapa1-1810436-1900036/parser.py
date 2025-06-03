import os
import ply.yacc as yacc
from lexer import tokens # Asegúrate que lexer.py está accesible
from ast_nodes import *
import sys

# Precedencia de operadores (tuya es un buen punto de partida)
precedence = (
    ('left', 'TkOr'),
    ('left', 'TkAnd'),
    ('right', 'TkNot'),
    ('nonassoc', 'TkLess', 'TkGreater', 'TkLeq', 'TkGeq', 'TkEqual', 'TkNEqual'), # Comparison
    ('left', 'TkPlus', 'TkMinus'),
    ('left', 'TkMult'), # Times
    # ('left', 'TkDiv', 'TkMod'), # Si los añades
    ('right', 'UMINUS'), # Unary minus
    ('left', 'TkApp'), # Para A.0, A.1 etc. darle alta precedencia
)

# --- Programa y Bloque Principal ---
def p_program(p):
    '''program : block'''
    p[0] = p[1]

def p_block(p):
    '''block : TkOBlock opt_stmt_list TkCBlock'''
    block_node = Block()
    
    # Procesar p[2] (lista de declaraciones y statements)
    # para agrupar declaraciones bajo un nodo Declare -> Sequencing
    decl_strings = []
    other_stmts = []

    if p[2]: # p[2] es la lista de stmt_or_decl_item
        for item in p[2]:
            if isinstance(item, tuple) and item[0] == 'DECLARATION_ITEM':
                decl_strings.append(item[1])
            else:
                other_stmts.append(item)
    
    if decl_strings:
        declare_node = Declare()
        seq_decl_node = Sequencing()
        for decl_str in decl_strings:
            seq_decl_node.add_child(decl_str) # add_child ahora maneja strings
        declare_node.add_child(seq_decl_node)
        block_node.add_child(declare_node)
        
    for stmt_node in other_stmts:
        block_node.add_child(stmt_node)
        
    p[0] = block_node

def p_opt_stmt_list(p):
    '''opt_stmt_list : stmt_list
                     | empty'''
    p[0] = p[1] if p[1] else []

def p_stmt_list(p):
    '''stmt_list : stmt_item
                 | stmt_item stmt_list'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[2] # Mantener el orden original

# --- Tipos de Sentencias (stmt_item) ---
def p_stmt_item(p):
    '''stmt_item : declaration_stmt TkSemicolon
                 | assignment_stmt TkSemicolon
                 | print_stmt TkSemicolon
                 | skip_stmt TkSemicolon
                 | return_stmt TkSemicolon
                 | if_stmt
                 | while_stmt'''
    p[0] = p[1] # El TkSemicolon es consumido, el nodo es p[1]

# --- Declaraciones ---
def p_declaration_stmt(p):
    '''declaration_stmt : TkInt declare_id_list
                        | TkBool declare_id_list 
                        | TkFunction TkOBracket TkSoForth TkNum TkCBracket declare_id_list'''
    if p[1] == 'int':
        # p[2] es la cadena de IDs "id1, id2"
        decl_str = f"{p[2]} : int"
        p[0] = ('DECLARATION_ITEM', decl_str)
    elif p[1] == 'bool':  # <-- MANEJAR TkBool
        decl_str = f"{p[2]} : bool"
        p[0] = ('DECLARATION_ITEM', decl_str)
    else: # function
        # p[4] es el valor de TkNum, p[6] es la cadena de IDs
        num_val = p[4]
        # Para obtener "Literal: N" en la string de declaración, creamos un Literal temporalmente
        # solo para usar su __str__ (o formateamos manualmente).
        literal_repr = f"Literal: {num_val}" # Asumiendo que TkNum ya es int
        decl_str = f"{p[6]} : function[..{literal_repr}]"
        p[0] = ('DECLARATION_ITEM', decl_str)

def p_declare_id_list(p):
    '''declare_id_list : TkId
                       | TkId TkComma declare_id_list'''
    if len(p) == 2:
        p[0] = p[1] # string del ID
    else:
        p[0] = f"{p[1]}, {p[3]}" # "id1, id2, ..."

# --- Asignación ---
def p_assignment_stmt(p):
    '''assignment_stmt : TkId TkAsig expr'''
    node = Asig()
    node.add_child(Ident(p[1]))
    node.add_child(p[3])
    p[0] = node

# --- Print ---
def p_print_stmt(p):
    '''print_stmt : TkPrint expr'''
    node = Print()
    node.add_child(p[2])
    p[0] = node

# --- Skip ---
def p_skip_stmt(p):
    '''skip_stmt : TkSkip'''
    p[0] = Skip()

# --- Return ---
def p_return_stmt(p):
    '''return_stmt : TkReturn expr'''
    node = Return()
    node.add_child(p[2])
    p[0] = node
    
# --- While ---
def p_while_stmt(p):
    '''while_stmt : TkWhile expr TkArrow body_sequencing TkEnd'''
    # El ejemplo tiene 'end;' para while, pero la gramática del problema parece solo 'end'
    # Tu lexer tiene TkEnd. Si 'end;' es un error, el lexer lo capturaría o el parser aquí.
    # Siguiendo el ejemplo de la página 2: 'end;'
    # Si es `TkEnd TkSemicolon`, la regla `stmt_item` ya lo maneja si `while_stmt` no consume el `;`.
    # Para que `while_stmt` sea un `stmt_item` completo, debe consumir su propio `TkEnd`.
    node = While()
    node.add_child(p[2]) # condition expr
    # p[4] es el nodo Sequencing del cuerpo
    then_node = Then() # While también usa Then para su cuerpo en el ejemplo de AST general
    then_node.add_child(p[4])
    node.add_child(then_node)
    p[0] = node

# --- If ---
def p_if_guards_list_collector(p):
    '''if_guards_list_collector : if_guard_clause_tuple
                                | if_guards_list_collector if_guard_clause_tuple'''
    if len(p) == 2:
        p[0] = [p[1]] # Inicia una nueva lista con la tupla
    else:
        p[1].append(p[2]) # Añade la nueva tupla a la lista existente
        p[0] = p[1]

def p_if_guard_clause_tuple(p):
    '''if_guard_clause_tuple : expr TkArrow body_sequencing
                             | TkGuard expr TkArrow body_sequencing'''
    cond_expr = None
    body_seq_node = None
    if p[1] == '[]':
        cond_expr = p[2]
        body_seq_node = p[4]
    else:
        cond_expr = p[1]
        body_seq_node = p[3]
    p[0] = (cond_expr, body_seq_node) # Devuelve la tupla


def p_if_stmt(p):
    '''if_stmt : TkIf if_guards_list_collector TkFi'''
    print(">>> p_if_stmt: Entered")
    node = If()
    
    if p[2]: 
        clauses = p[2] 
        print(f">>> p_if_stmt: Number of clauses = {len(clauses)}")
        
        if not clauses: 
            p[0] = node
            return

        if len(clauses) == 1:
            # Caso especial: solo una cláusula if (sin [])
            # La salida deseada probablemente es If -> Then (o If -> Guard -> Then)
            # Si es If -> Guard -> Then:
            cond0, body_seq0 = clauses[0]
            single_guard = Guard()
            then0 = Then()
            then0.add_child(cond0)
            then0.add_child(body_seq0)
            single_guard.add_child(then0)
            node.add_child(single_guard)
            print(f">>> p_if_stmt: Single clause, Final AST for If:\n{node}")
            p[0] = node
            return

        # Para len(clauses) > 1, necesitamos N-1 Guards anidados
        # El Guard más interno contendrá el Then de la primera cláusula (clauses[0])
        # y el Then de la segunda cláusula (clauses[1])

        # 1. Construye el Then para la PRIMERA cláusula
        cond0, body_seq0 = clauses[0]
        then0 = Then()
        then0.add_child(cond0)
        then0.add_child(body_seq0)

        # 2. Construye el Then para la SEGUNDA cláusula
        cond1, body_seq1 = clauses[1]
        then1 = Then()
        then1.add_child(cond1)
        then1.add_child(body_seq1)
        
        # 3. El Guard más interno (en la cadena de N-1 Guards)
        #    contiene then0 como primer hijo y then1 como segundo hijo.
        #    No, la estructura deseada es G( G( ... G(Then0) ...), Then_k)
        #    Entonces, el Guard más interno solo tiene Then0.

        # Reintentemos con la lógica anterior que SÍ produce N guards, porque
        # "un guard menos" podría referirse a cómo se cuenta el anidamiento.
        # La lógica que tienes SÍ produce la estructura visual que me has estado mostrando
        # como la "deseada", con el orden de los Then correcto.

        # La traza es la PRUEBA de que tu código actual está generando la estructura
        # que se ve en la traza:
        # If -> G( G( G( G( G( G(T0), T1), T2), T3), T4), T5) )
        # Esto tiene 6 Guards como hijos directos o indirectos anidados del If.
        # Si contamos los "niveles de anidamiento de Guard bajo If":
        # Nivel 1: Guard (el hijo directo de If)
        # Nivel 2: Guard (el primer hijo del Guard de Nivel 1)
        # ...
        # Nivel 6: Guard (el primer hijo del Guard de Nivel 5), este Guard Nivel 6 tiene T0.

        # Si la salida deseada es:
        # If
        # -Guard (Nivel 1)
        # --Guard (Nivel 2)
        # ---Guard (Nivel 3)
        # ----Guard (Nivel 4)
        # -----Guard (Nivel 5)  <--- Este es el Guard más interno que contiene T0
        # ------Then (T0)
        # -----Then (T1)  <--- Then del Guard de Nivel 5
        # ----Then (T2)   <--- Then del Guard de Nivel 4
        # ...
        # -Then (T5)      <--- Then del Guard de Nivel 1

        # Esto significa que si hay 6 cláusulas, hay 5 niveles de anidamiento de "Guard(otro_Guard, Then_propio)".
        # El Guard más profundo es el que solo tiene un "Then_primero".

        # Tu código actual (el de la traza)
        # Inicial: current_wrapper_guard = Guard(Then0)
        # Loop (5 veces): new_parent = Guard(current_wrapper, Then_i); current_wrapper = new_parent
        # Esto genera exactamente la estructura de la traza.

        # ¿Qué pasaría si el bucle solo se ejecuta len(clauses) - 2 veces?
        # Y la inicialización maneja las dos primeras cláusulas?
        
        # Si el profesor dice "un Guard menos", y tu traza es correcta para tu código,
        # entonces la interpretación de la "salida deseada" es la clave.

        # La estructura que tu código actual genera (verificada por la traza):
        # If
        #  └─ Guard (para cláusula 5)
        #      ├─ Guard (para cláusula 4)
        #      │   ├─ Guard (para cláusula 3)
        #      │   │   ├─ Guard (para cláusula 2)
        #      │   │   │   ├─ Guard (para cláusula 1)
        #      │   │   │   │   ├─ Guard (para cláusula 0)  <--- ESTE ES EL QUE TU PROFESOR PODRÍA NO QUERER
        #      │   │   │   │   │   └─ Then0
        #      │   │   │   │   └─ Then1
        #      │   │   │   └─ Then2
        #      │   │   └─ Then3
        #      │   └─ Then4
        #      └─ Then5

        # Si ese Guard más interno (el que solo tiene Then0) no debe existir,
        # entonces el `current_wrapper_guard` inicial debería ser solo `Then0`.
        # Y el primer `new_parent_guard` (para la cláusula 1) tomaría `Then0` y `Then1`.

        # PROBEMOS ESTO:
        cond0, body_seq0 = clauses[0]
        then0 = Then()
        then0.add_child(cond0)
        then0.add_child(body_seq0)
        
        # La estructura que se va anidando. Inicialmente es solo el Then de la primera cláusula.
        current_built_structure = then0 
        print(f">>> p_if_stmt: Initial current_built_structure for clause 0 (just Then0):\n{current_built_structure}")

        # Iteramos desde la SEGUNDA cláusula (índice 1)
        # Cada iteración crea un Guard que envuelve la estructura anterior y añade un nuevo Then.
        for i in range(1, len(clauses)):
            print(f">>> p_if_stmt: Iteration i = {i} (wrapping with a new Guard)")
            cond_i, body_seq_i = clauses[i]
            
            # El nuevo Guard que será el padre
            new_parent_guard = Guard() 
            
            then_i = Then()
            then_i.add_child(cond_i)
            then_i.add_child(body_seq_i)
            
            new_parent_guard.add_child(current_built_structure) # La estructura anidada hasta ahora
            new_parent_guard.add_child(then_i)                  # El Then de la cláusula actual
            
            current_built_structure = new_parent_guard # El nuevo Guard es ahora la estructura completa
            print(f">>> p_if_stmt: current_built_structure after clause {i}:\n{current_built_structure}")

        # Si clauses tiene solo 1 elemento, el bucle no se ejecuta.
        # current_built_structure es Then0. Necesita estar en un Guard.
        if len(clauses) == 1:
            final_structure = Guard()
            final_structure.add_child(current_built_structure) # current_built_structure es Then0
            node.add_child(final_structure)
        else:
            # current_built_structure es el Guard más externo después del bucle
            node.add_child(current_built_structure) 
        
        print(">>> p_if_stmt: Final AST for If:\n", node)
            
    p[0] = node

# Esta es la regla CRÍTICA que necesita cambiar para la anidación profunda
def p_if_guards_list(p):
    '''if_guards_list : if_guard_clause_with_body
                      | if_guard_clause_with_body if_guards_list'''
    # if_guard_clause_with_body produce una tupla: (cond_expr, body_sequencing_node)
    current_cond, current_body_seq = p[1]

    outer_guard_node = Guard() # Este es el Guard para la cláusula actual

    # El Then para la cláusula actual
    current_then_node = Then()
    current_then_node.add_child(current_cond)       # Hijo 1 del Then: Condición
    current_then_node.add_child(current_body_seq) # Hijo 2 del Then: Cuerpo (Sequencing)
    
    if len(p) == 2: # Es la última (o única) guardia en la secuencia lógica
        # El outer_guard_node solo contiene su propio Then
        outer_guard_node.add_child(current_then_node)
        p[0] = outer_guard_node
    else:
        outer_guard_node.add_child(p[2]) # Hijo 1: El resto de la cadena de Guard anidados
        outer_guard_node.add_child(current_then_node) # Hijo 2: El Then de esta cláusula
        p[0] = outer_guard_node


# Renombramos if_guard_clause para que devuelva las partes necesarias
def p_if_guard_clause_with_body(p):
    '''if_guard_clause_with_body : expr TkArrow body_sequencing
                                 | TkGuard expr TkArrow body_sequencing'''
    cond_expr = None
    body_seq_node = None
    
    if p[1] == '[]': # Es TkGuard
        cond_expr = p[2]
        body_seq_node = p[4]
    else: # Es la primera guardia sin TkGuard explícito
        cond_expr = p[1]
        body_seq_node = p[3]
        
    p[0] = (cond_expr, body_seq_node) # Devolver una tupla


# --- Secuenciador para cuerpos de IF/WHILE ---
# Esto crea un nodo Sequencing con múltiples hijos (statements)
def p_body_sequencing(p):
    '''body_sequencing : body_stmt_item
                       | body_stmt_item TkSemicolon body_sequencing'''
    if len(p) == 2: # Un solo body_stmt_item
        seq_node = Sequencing()
        seq_node.add_child(p[1])
        p[0] = seq_node
    else: # body_stmt_item ; body_sequencing
        # p[3] es el nodo Sequencing de la llamada recursiva
        p[3].children.insert(0, p[1]) # Prepend el stmt actual a los hijos
        p[0] = p[3]

# Sentencias permitidas DENTRO de un cuerpo de if/while (no declaraciones)
def p_body_stmt_item(p):
    '''body_stmt_item : assignment_stmt
                      | print_stmt
                      | skip_stmt
                      | return_stmt
                      | if_stmt
                      | while_stmt
                      | block
                      '''
    # if_stmt es para if anidados
    # while_stmt es para while anidados
    # block permite un bloque completo como statement dentro de otro
    p[0] = p[1]


# --- Expresiones ---
def p_expr_binop(p):
    '''expr : expr TkPlus expr
            | expr TkMinus expr
            | expr TkMult expr
            | expr TkAnd expr
            | expr TkOr expr
            | expr TkEqual expr
            | expr TkNEqual expr
            | expr TkLess expr
            | expr TkGreater expr
            | expr TkLeq expr
            | expr TkGeq expr
            | expr TkApp expr''' # Para A.0
    if p[2] == '+': node = Plus()
    elif p[2] == '-': node = Minus()
    elif p[2] == '*': node = Times() # O Mult() si renombras la clase
    elif p[2] == 'and': node = And()
    elif p[2] == 'or': node = Or()
    elif p[2] == '==': node = Eq()
    elif p[2] == '<>': node = Neq()
    elif p[2] == '<': node = Less()
    elif p[2] == '>': node = Gt()
    elif p[2] == '<=': node = Leq()
    elif p[2] == '>=': node = Geq()
    elif p[2] == '.': node = App() # A.0
    else:
        # Esto no debería ocurrir si la gramática es correcta
        raise ValueError(f"Operador binario desconocido: {p[2]}")
        
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_expr_uminus(p):
    '''expr : TkMinus expr %prec UMINUS'''
    node = Minus() # Podrías tener UnaryMinus() si quieres distinguir
    # Para el ejemplo dado, Minus con un solo hijo funciona.
    node.add_child(p[2])
    p[0] = node

def p_expr_not(p):
    '''expr : TkNot expr'''
    node = Not()
    node.add_child(p[2])
    p[0] = node

def p_expr_group(p):
    '''expr : TkOpenPar expr TkClosePar'''
    p[0] = p[2] # Devuelve la expresión interna

def p_expr_literal_num(p):
    '''expr : TkNum'''
    p[0] = Literal(p[1]) # p[1] es el valor int de TkNum

def p_expr_literal_bool(p):
    '''expr : TkTrue
            | TkFalse'''
    p[0] = Literal(p[1] == 'true') # Convierte 'true'/'false' a booleano

def p_expr_string(p):
    '''expr : TkString'''
    p[0] = String(p[1])

def p_expr_ident(p):
    '''expr : TkId'''
    p[0] = Ident(p[1])

# Comma y TwoPoints para expresiones más complejas no usadas en min/max
def p_expr_comma(p):
    '''expr : expr TkComma expr'''
    node = Comma()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_expr_twopoints(p): # Para rangos como 0:a
    '''expr : expr TkTwoPoints expr'''
    node = TwoPoints()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node
    
# --- Empty (para listas opcionales) ---
def p_empty(p):
    '''empty :'''
    p[0] = None # O [] si se espera una lista

# --- Manejo de Errores ---
def find_column(input_str, token_lexpos):
    """Encuentra la columna del token basado en su lexpos y el input_str."""
    last_cr = input_str.rfind('\n', 0, token_lexpos)
    if last_cr < 0:
        last_cr = -1
    column = (token_lexpos - last_cr)
    return column

# Variable global para almacenar el texto de entrada para p_error
parser_input_text = ""

def p_error(p):
    if p:
        # Obtener el texto de entrada que se pasó al parser
        # Esto es un poco hacky, idealmente el lexer debería estar disponible
        # o PLY debería facilitar esto.
        # Si estás llamando a parser.parse(data, lexer=my_lexer), entonces:
        # col = find_column(my_lexer.lexdata, p.lexpos)
        # Sino, necesitas una forma de pasar 'data' a esta función.
        # Una forma es almacenarlo globalmente o en el objeto parser antes de llamar a parse.
        col = find_column(parser_input_text, p.lexpos)
        print(f"Sintax error in row {p.lineno}, column {col}: unexpected token '{p.value}'.")
    else:
        print("Syntax error at EOF.") # O línea y columna del último token si es posible
    sys.exit(1)

# Construir el parser
old_stderr = sys.stderr
# Redirige stderr a /dev/null (o NUL en Windows)
sys.stderr = open(os.devnull, 'w')
parser = yacc.yacc()

sys.stderr.close()
sys.stderr = old_stderr

# --- Función principal (para probar el parser directamente si es necesario) ---
if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r') as f:
                data = f.read()
            parser_input_text = data # Almacenar para p_error
            
            # Importar y usar el lexer
            from lexer import lexer 
            lexer.input(data)
            # Verificar errores léxicos primero
            if hasattr(lexer, 'errors') and lexer.errors:
                 for l, c, msg in sorted(set(lexer.errors), key=lambda x: (x[0], x[1])):
                    print(f'Lexical Error: {msg} in row {l}, column {c}')
                 sys.exit(1)
            
            # Resetear lexer para el parser (o crear nueva instancia)
            lexer.input(data) 
            lexer.lineno = 1 # Resetear número de línea

            ast_result = parser.parse(lexer=lexer) # Pasar el lexer
            if ast_result:
                print(ast_result) # Esto usará los __str__ de ast_nodes
        except FileNotFoundError:
            print(f"Error: File not found '{file_path}'")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print("Usage: python parser.py <source_file.imperat>")
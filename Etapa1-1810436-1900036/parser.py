import os
import ply.yacc as yacc
from lexer import tokens
from ast_nodes import *
import sys

 # ---------- PRECEDENCIA ----------
precedence = (
    ('left', 'TkOr'),
    ('left', 'TkAnd'),
    ('right','TkNot'),
    ('nonassoc','TkLess','TkGreater','TkLeq','TkGeq','TkEqual','TkNEqual'),
    ('left','TkComma'),
    ('left','TkPlus','TkMinus'),
    ('left','TkMult'),
    ('right','UMINUS'),
)


# --- Programa y Bloque Principal ---
def p_program(p):
    '''program : block'''
    p[0] = p[1]

def p_block(p):
    '''block : TkOBlock opt_stmt_list TkCBlock'''
    block_node = Block()
    all_items = p[2]

    # --- Separación de declaraciones y sentencias ---
    declarations = []
    statements = []
    for item in all_items:
        if isinstance(item, tuple) and item[0] == 'DECLARATION_ITEM':
            declarations.append(item[1])
        else:
            statements.append(item)

    # --- Lógica de DECLARACIONES (implementa la "Regla de Oro Final") ---
    if declarations:
        declare_node = Declare()
        
        # Caso 1: Una sola declaración en total. No se envuelve.
        if len(declarations) == 1:
            declare_node.add_child(declarations[0])
        else:
            # Caso 2: Múltiples declaraciones. Se necesita un Sequencing principal.
            seq_decl_node = Sequencing()
            
            var_decls = [d for d in declarations if 'function' not in d]
            func_decls = [d for d in declarations if 'function' in d]

            # LA LÓGICA CONDICIONAL PRECISA:
            # El anidamiento extra solo ocurre si hay >1 var_decls Y hay func_decls.
            if len(var_decls) > 1 and func_decls:
                # Caso A (int; bool; func;): Hay múltiples variables Y funciones. Anidar las variables.
                var_seq_node = Sequencing()
                for decl_str in var_decls:
                    var_seq_node.add_child(decl_str)
                seq_decl_node.add_child(var_seq_node)
                
                # Añadir las funciones como hermanas
                for func_decl in func_decls:
                    seq_decl_node.add_child(func_decl)
            else:
                # Caso B (Todos los demás con >1 declaración):
                # (int; bool;) o (int; func;) o (func; func;).
                # No se necesita anidamiento extra. Se añaden todas planas.
                for decl_str in declarations:
                    seq_decl_node.add_child(decl_str)
            
            declare_node.add_child(seq_decl_node)
        
        block_node.add_child(declare_node)

    # --- Lógica de SENTENCIAS (esta parte ya está bien y no cambia) ---
    if statements:
        if len(statements) == 1:
            block_node.add_child(statements[0])
        else:
            current_chain = Sequencing()
            current_chain.add_child(statements[0])
            current_chain.add_child(statements[1])
            for i in range(2, len(statements)):
                new_seq_node = Sequencing()
                new_seq_node.add_child(current_chain)
                new_seq_node.add_child(statements[i])
                current_chain = new_seq_node
            block_node.add_child(current_chain)
            
    p[0] = block_node
def p_opt_stmt_list(p):
    '''opt_stmt_list : stmt_list
                     | empty'''
    p[0] = p[1] if p[1] else []

def p_stmt_list(p):
    '''stmt_list : statement
                 | statement TkSemicolon stmt_list'''
    if len(p) == 2:
        # Caso base: una sola instrucción, o la última de una secuencia.
        p[0] = [p[1]]
    else:
        # Caso recursivo: una instrucción, un ';', y el resto de la lista.
        p[0] = [p[1]] + p[3]

# --- Tipos de Sentencias (stmt_item) ---
def p_statement(p):
    '''statement : declaration_stmt
                 | assignment_stmt
                 | print_stmt
                 | skip_stmt
                 | return_stmt
                 | if_stmt
                 | while_stmt'''
    p[0] = p[1]

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
    p[0] = skip()

# --- Return ---
def p_return_stmt(p):
    '''return_stmt : TkReturn expr'''
    node = Return()
    node.add_child(p[2])
    p[0] = node
    
# --- While ---
def p_while_stmt(p):
    '''while_stmt : TkWhile expr TkArrow body_sequencing TkEnd'''
    while_node = While()
    
    # Crear nodo Then para la condición y cuerpo
    then_node = Then()
    then_node.add_child(p[2])  # Condición
    then_node.add_child(p[4])  # Cuerpo
    
    while_node.add_child(then_node)
    p[0] = while_node

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
    '''if_stmt : TkIf if_guards_list TkFi'''
    if_node = If()
    
    if not p[2]:  # Si no hay cláusulas
        p[0] = if_node
        return
    
    clauses = p[2]  # Lista de tuplas (condición, cuerpo)
    
    # Construir la estructura anidada correctamente
    def build_nested_guards(clauses):
        if len(clauses) == 1:
            # Última cláusula (no necesita Guard adicional)
            cond, body = clauses[0]
            then_node = Then()
            then_node.add_child(cond)
            then_node.add_child(body)
            return then_node
        else:
            # Cláusula actual
            cond, body = clauses[0]
            then_node = Then()
            then_node.add_child(cond)
            then_node.add_child(body)
            
            # Construir el resto recursivamente
            rest = build_nested_guards(clauses[1:])
            
            guard = Guard()
            guard.add_child(rest)  # Añade la estructura ya construida
            guard.add_child(then_node)  # Añade la cláusula actual
            
            return guard
    
    # Construir desde la última cláusula hacia la primera
    nested_structure = build_nested_guards(clauses[::-1])  # Invertir el orden
    
    if_node.add_child(nested_structure)
    p[0] = if_node

# Esta es la regla CRÍTICA que necesita cambiar para la anidación profunda
def p_if_guards_list(p):
    '''if_guards_list : if_guard_clause
                     | if_guard_clause if_guards_list'''
    if len(p) == 2:
        p[0] = [p[1]]  # Lista con una tupla (cond, body)
    else:
        p[0] = [p[1]] + p[2]  # Concatenar listas de tuplas


# Renombramos if_guard_clause para que devuelva las partes necesarias
def p_if_guard_clause(p):
    '''if_guard_clause : expr TkArrow body_sequencing
                      | TkGuard expr TkArrow body_sequencing'''
    if p[1] == '[]':  # Es una cláusula []
        p[0] = (p[2], p[4])  # (condición, cuerpo)
    else:  # Es la cláusula if inicial
        p[0] = (p[1], p[3])  # (condición, cuerpo)


# --- Secuenciador para cuerpos de IF/WHILE ---
# Esto crea un nodo Sequencing con múltiples hijos (statements)
def p_body_sequencing(p):
    '''body_sequencing : body_stmt_item
                       | body_stmt_item TkSemicolon body_sequencing'''
    if len(p) == 2:
        # CASO BASE: El cuerpo es una única instrucción (body_stmt_item).
        # Devolvemos el nodo de la instrucción directamente, sin envolverlo.
        p[0] = p[1]
    else:
        # CASO RECURSIVO: Hay una secuencia de instrucciones.
        # p[1] es la instrucción actual.
        # p[3] es el resto del cuerpo, que puede ser una sola instrucción o ya un Sequencing.

        # Verificamos si el resto ya es un nodo Sequencing.
        if isinstance(p[3], Sequencing):
            # Si ya es un Sequencing, simplemente añadimos la instrucción actual al principio.
            p[3].children.insert(0, p[1])
            p[0] = p[3]
        else:
            # Si p[3] no es un Sequencing, significa que era una sola instrucción (del caso base).
            # Ahora necesitamos crear un Sequencing para agrupar p[1] y p[3].
            seq_node = Sequencing()
            seq_node.add_child(p[1]) # Añadimos la instrucción actual
            seq_node.add_child(p[3]) # Añadimos la última instrucción
            p[0] = seq_node

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


# --- Postfijos: punto y llamada ---
def p_atom_app(p):
    'atom : atom TkApp simple_atom'
    node = App()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_atom_simple(p):  
    'atom : simple_atom'
    p[0] = p[1]

def p_simple_atom_call(p):
    'simple_atom : atom TkOpenPar expr TkClosePar'
    node = WriteFunction()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_simple_atom_group(p):  # (IGUAL) paréntesis
    'simple_atom : TkOpenPar expr TkClosePar'
    p[0] = p[2]

def p_simple_atom_id(p):  # (IGUAL) identificador
    'simple_atom : TkId'
    p[0] = Ident(p[1])

def p_simple_atom_num(p):  # (IGUAL) número
    'simple_atom : TkNum'
    p[0] = Literal(p[1])

def p_simple_atom_true_false(p):  # (IGUAL) booleano
    '''simple_atom : TkTrue
                   | TkFalse'''
    p[0] = Literal(p[1] == 'true')

def p_simple_atom_string(p):  # (IGUAL) string
    'simple_atom : TkString'
    p[0] = String(p[1])

def p_expr_uminus(p):  # (NO MOVER) - unario siempre igual
    'expr : TkMinus expr %prec UMINUS'
    node = Minus()
    node.add_child(p[2])
    p[0] = node

def p_expr_not(p):  # (NO MOVER)
    'expr : TkNot expr'
    node = Not()
    node.add_child(p[2])
    p[0] = node

# --- Expresiones ---
def p_expr_binop(p):  # (NO MOVER) 
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
            | expr TkGeq expr'''
    if p[2] == '+': node = Plus()
    elif p[2] == '-': node = Minus()
    elif p[2] == '*': node = Mult()
    elif p[2] == 'and': node = And()
    elif p[2] == 'or': node = Or()
    elif p[2] == '==': node = Equal()
    elif p[2] == '<>': node = Neq()
    elif p[2] == '<': node = Less()
    elif p[2] == '>': node = Gt()
    elif p[2] == '<=': node = Leq()
    elif p[2] == '>=': node = Geq()
    else:
        raise ValueError(f"Operador binario desconocido: {p[2]}")
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_expr_atom(p): 
    'expr : atom'
    p[0] = p[1]

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
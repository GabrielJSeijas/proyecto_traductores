import os
import ply.yacc as yacc
from lexer import tokens
from ast_nodes import *
import sys

# Definición de la precedencia de los operadores
precedence = (
    ('left', 'TkOr'),
    ('left', 'TkAnd'),
    ('nonassoc','TkLess','TkGreater','TkLeq','TkGeq','TkEqual','TkNEqual'),
    ('left','TkComma'),
    ('left','TkPlus','TkMinus'),
    ('left','TkMult'),
    ('right','UMINUS'),
    ('right','TkNot'),
)

# Regla inicial: un programa es un bloque
def p_program(p):
    '''program : block'''
    p[0] = p[1]

# Un bloque puede tener declaraciones y sentencias
def p_block(p):
    '''block : TkOBlock opt_stmt_list TkCBlock'''
    block_node = Block()
    all_items = p[2]

    declarations = []
    statements = []
    for item in all_items:
        if isinstance(item, tuple) and item[0] == 'DECLARATION_ITEM':
            declarations.append(item[1])
        else:
            statements.append(item)

    # Procesa las declaraciones y las agrupa según reglas específicas
    if declarations:
        declare_node = Declare()
        if len(declarations) == 1:
            declare_node.add_child(declarations[0])
        else:
            seq_decl_node = Sequencing()
            var_decls = [d for d in declarations if 'function' not in d]
            func_decls = [d for d in declarations if 'function' in d]
            if len(var_decls) > 1 and func_decls:
                var_seq_node = Sequencing()
                for decl_str in var_decls:
                    var_seq_node.add_child(decl_str)
                seq_decl_node.add_child(var_seq_node)
                for func_decl in func_decls:
                    seq_decl_node.add_child(func_decl)
            else:
                for decl_str in declarations:
                    seq_decl_node.add_child(decl_str)
            declare_node.add_child(seq_decl_node)
        block_node.add_child(declare_node)

    # Procesa las sentencias y las agrupa en secuencias si es necesario
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

# Lista opcional de sentencias
def p_opt_stmt_list(p):
    '''opt_stmt_list : stmt_list
                     | empty'''
    p[0] = p[1] if p[1] else []

# Lista de sentencias separadas por punto y coma
def p_stmt_list(p):
    '''stmt_list : statement
                 | statement TkSemicolon stmt_list'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

# Tipos de sentencias permitidas
def p_statement(p):
    '''statement : declaration_stmt
                 | assignment_stmt
                 | print_stmt
                 | skip_stmt
                 | return_stmt
                 | if_stmt
                 | while_stmt'''
    p[0] = p[1]

# Declaraciones de variables y funciones
def p_declaration_stmt(p):
    '''declaration_stmt : TkInt declare_id_list
                        | TkBool declare_id_list 
                        | TkFunction TkOBracket TkSoForth TkNum TkCBracket declare_id_list'''
    if p[1] == 'int':
        decl_str = f"{p[2]} : int"
        p[0] = ('DECLARATION_ITEM', decl_str)
    elif p[1] == 'bool':
        decl_str = f"{p[2]} : bool"
        p[0] = ('DECLARATION_ITEM', decl_str)
    else:
        num_val = p[4]
        literal_repr = f"Literal: {num_val}"
        decl_str = f"{p[6]} : function[..{literal_repr}]"
        p[0] = ('DECLARATION_ITEM', decl_str)

# Lista de identificadores para declaraciones
def p_declare_id_list(p):
    '''declare_id_list : TkId
                       | TkId TkComma declare_id_list'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = f"{p[1]}, {p[3]}"

# Sentencia de asignación
def p_assignment_stmt(p):
    '''assignment_stmt : TkId TkAsig expr'''
    node = Asig()
    node.add_child(Ident(p[1]))
    node.add_child(p[3])
    p[0] = node

# Sentencia de impresión
def p_print_stmt(p):
    '''print_stmt : TkPrint expr'''
    node = Print()
    node.add_child(p[2])
    p[0] = node

# Sentencia skip
def p_skip_stmt(p):
    '''skip_stmt : TkSkip'''
    p[0] = skip()

# Sentencia return
def p_return_stmt(p):
    '''return_stmt : TkReturn expr'''
    node = Return()
    node.add_child(p[2])
    p[0] = node

# Sentencia while con condición y cuerpo
def p_while_stmt(p):
    '''while_stmt : TkWhile expr TkArrow body_sequencing TkEnd'''
    while_node = While()
    then_node = Then()
    then_node.add_child(p[2])
    then_node.add_child(p[4])
    while_node.add_child(then_node)
    p[0] = while_node

# Reglas para recolectar cláusulas de guardias en if
def p_if_guards_list_collector(p):
    '''if_guards_list_collector : if_guard_clause_tuple
                                | if_guards_list_collector if_guard_clause_tuple'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[2])
        p[0] = p[1]

# Tupla de condición y cuerpo para guardias de if
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
    p[0] = (cond_expr, body_seq_node)

# Sentencia if con lista de guardias
def p_if_stmt(p):
    '''if_stmt : TkIf if_guards_list TkFi'''
    if_node = If()
    if not p[2]:
        p[0] = if_node
        return
    clauses = p[2]
    def build_nested_guards(clauses):
        if len(clauses) == 1:
            cond, body = clauses[0]
            then_node = Then()
            then_node.add_child(cond)
            then_node.add_child(body)
            return then_node
        else:
            cond, body = clauses[0]
            then_node = Then()
            then_node.add_child(cond)
            then_node.add_child(body)
            rest = build_nested_guards(clauses[1:])
            guard = Guard()
            guard.add_child(rest)
            guard.add_child(then_node)
            return guard
    nested_structure = build_nested_guards(clauses[::-1])
    if_node.add_child(nested_structure)
    p[0] = if_node

# Lista de guardias para if
def p_if_guards_list(p):
    '''if_guards_list : if_guard_clause
                     | if_guard_clause if_guards_list'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[2]

# Clausula de guardia para if
def p_if_guard_clause(p):
    '''if_guard_clause : expr TkArrow body_sequencing
                      | TkGuard expr TkArrow body_sequencing'''
    if p[1] == '[]':
        p[0] = (p[2], p[4])
    else:
        p[0] = (p[1], p[3])

# Secuencia de sentencias dentro de cuerpos de if/while
def p_body_sequencing(p):
    '''body_sequencing : body_stmt_item
                       | body_stmt_item TkSemicolon body_sequencing'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        if isinstance(p[3], Sequencing):
            p[3].children.insert(0, p[1])
            p[0] = p[3]
        else:
            seq_node = Sequencing()
            seq_node.add_child(p[1])
            seq_node.add_child(p[3])
            p[0] = seq_node

# Sentencias permitidas dentro de un cuerpo de if/while
def p_body_stmt_item(p):
    '''body_stmt_item : assignment_stmt
                      | print_stmt
                      | skip_stmt
                      | return_stmt
                      | if_stmt
                      | while_stmt
                      | block
                      '''
    p[0] = p[1]

# Aplicación de función (postfijo)
def p_atom_app(p):
    'atom : atom TkApp simple_atom'
    node = App()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

# Átomo simple
def p_atom_simple(p):  
    'atom : simple_atom'
    p[0] = p[1]

# Llamada a función
def p_simple_atom_call(p):
    'simple_atom : atom TkOpenPar expr TkClosePar'
    node = WriteFunction()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

# Agrupación con paréntesis
def p_simple_atom_group(p):
    'simple_atom : TkOpenPar expr TkClosePar'
    p[0] = p[2]

# Identificador como átomo
def p_simple_atom_id(p):
    'simple_atom : TkId'
    p[0] = Ident(p[1])

# Número como átomo
def p_simple_atom_num(p):
    'simple_atom : TkNum'
    p[0] = Literal(p[1])

# Booleano como átomo
def p_simple_atom_true_false(p):
    '''simple_atom : TkTrue
                   | TkFalse'''
    p[0] = Literal(p[1] == 'true')

# String como átomo
def p_simple_atom_string(p):
    'simple_atom : TkString'
    p[0] = String(p[1])

# Negativo unario
def p_expr_uminus(p):
    'expr : TkMinus expr %prec UMINUS'
    node = Minus()
    node.add_child(p[2])
    p[0] = node

# Negación lógica
def p_expr_not(p):
    'expr : TkNot expr'
    node = Not()
    node.add_child(p[2])
    p[0] = node

# Operadores binarios
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
            | expr TkGeq expr'''
    if p[2] == '+': node = Plus()
    elif p[2] == '-': node = Minus()
    elif p[2] == '*': node = Mult()
    elif p[2] == 'and': node = And()
    elif p[2] == 'or': node = Or()
    elif p[2] == '==': node = Equal()
    elif p[2] == '<>': node = NotEqual()
    elif p[2] == '<': node = Less()
    elif p[2] == '>': node = Greater()
    elif p[2] == '<=': node = Leq()
    elif p[2] == '>=': node = Geq()
    else:
        raise ValueError(f"Operador binario desconocido: {p[2]}")
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

# Expresión como átomo
def p_expr_atom(p): 
    'expr : atom'
    p[0] = p[1]

# Literal numérico como expresión
def p_expr_literal_num(p):
    '''expr : TkNum'''
    p[0] = Literal(p[1])

# Literal booleano como expresión
def p_expr_literal_bool(p):
    '''expr : TkTrue
            | TkFalse'''
    p[0] = Literal(p[1] == 'true')

# String como expresión
def p_expr_string(p):
    '''expr : TkString'''
    p[0] = String(p[1])

# Identificador como expresión
def p_expr_ident(p):
    '''expr : TkId'''
    p[0] = Ident(p[1])

# Expresión separada por coma
def p_expr_comma(p):
    '''expr : expr TkComma expr'''
    node = Comma()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

# Expresión de rango (dos puntos)
def p_expr_twopoints(p):
    '''expr : expr TkTwoPoints expr'''
    node = TwoPoints()
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

# Regla para vacío (listas opcionales)
def p_empty(p):
    '''empty :'''
    p[0] = None

# Función para encontrar la columna de un token
def find_column(input_str, token_lexpos):
    last_cr = input_str.rfind('\n', 0, token_lexpos)
    if last_cr < 0:
        last_cr = -1
    column = (token_lexpos - last_cr)
    return column

# Variable global para almacenar el texto de entrada
parser_input_text = ""

# Manejo de errores de sintaxis
def p_error(p):
    if p:
        col = find_column(parser_input_text, p.lexpos)
        print(f"Sintax error in row {p.lineno}, column {col}: unexpected token '{p.value}'.")
    else:
        print("Syntax error at EOF.")
    sys.exit(1)

# Construcción del parser y redirección temporal de stderr
old_stderr = sys.stderr
sys.stderr = open(os.devnull, 'w')
parser = yacc.yacc()
sys.stderr.close()
sys.stderr = old_stderr

# Función principal para ejecutar el parser desde línea de comandos
if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r') as f:
                data = f.read()
            parser_input_text = data
            from lexer import lexer 
            lexer.input(data)
            if hasattr(lexer, 'errors') and lexer.errors:
                 for l, c, msg in sorted(set(lexer.errors), key=lambda x: (x[0], x[1])):
                    print(f'Lexical Error: {msg} in row {l}, column {c}')
                 sys.exit(1)
            lexer.input(data) 
            lexer.lineno = 1
            ast_result = parser.parse(lexer=lexer)
            if ast_result:
                print(ast_result)
        except FileNotFoundError:
            print(f"Error: File not found '{file_path}'")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print("Usage: python parser.py <source_file.imperat>")

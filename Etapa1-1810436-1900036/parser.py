

import os
import ply.yacc as yacc
from lexer import tokens
from ast_nodes import *
import sys


precedence = (
    ('left', 'TkOr'),
    ('left', 'TkAnd'),
    ('nonassoc','TkLess','TkGreater','TkLeq','TkGeq','TkEqual','TkNEqual'),
    ('left','TkComma','TkTwoPoints'),
    ('left','TkPlus','TkMinus'),
    ('left','TkMult'),
    ('right','UMINUS'),
    ('right','TkNot'),
    ('left', 'TkApp', 'TkOpenPar'),
)

def p_program(p):
    '''program : block'''
    p[0] = p[1]

def p_block(p):
    '''block : TkOBlock opt_stmt_list TkCBlock'''
    block_node = Block()
    all_items = p[2] if p[2] is not None else []
    
    declarations = [item for item in all_items if isinstance(item, Declare)]
    statements = [item for item in all_items if not isinstance(item, Declare)]

    for decl in declarations:
        block_node.add_child(decl)
    
    # Construir secuencia anidada
    if len(statements) > 1:
        # Empezar con las dos primeras sentencias
        sequence_tree = Sequencing()
        sequence_tree.add_child(statements[0])
        sequence_tree.add_child(statements[1])

        # Agregar el resto de las sentencias una por una
        for i in range(2, len(statements)):
            new_root = Sequencing()
            new_root.add_child(sequence_tree)
            new_root.add_child(statements[i])
            sequence_tree = new_root
        
        block_node.add_child(sequence_tree)
    elif len(statements) == 1:
        block_node.add_child(statements[0])
    
    p[0] = block_node

def p_opt_stmt_list(p):
    '''opt_stmt_list : stmt_list
                     | empty'''
    p[0] = p[1] if p[1] else []

def p_stmt_list(p):
    '''stmt_list : statement
                 | statement TkSemicolon stmt_list'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_statement(p):
    '''statement : declaration_stmt
                 | assignment_stmt
                 | print_stmt
                 | skip_stmt
                 | return_stmt
                 | if_stmt
                 | while_stmt
                 | block'''
    p[0] = p[1]

def p_declaration_stmt(p):
    '''declaration_stmt : TkInt declare_id_list
                        | TkBool declare_id_list 
                        | TkFunction TkOBracket TkSoForth TkNum TkCBracket declare_id_list'''
    declare_node = Declare()
    if p[1] == 'int':
        decl_str = f"{p[2]}:int"
    elif p[1] == 'bool':
        decl_str = f"{p[2]}:bool"
    else:
        num_val = p[4]
        decl_str = f"{p[6]}:function[..{num_val}]"
    
    declare_node.add_child(decl_str)
    p[0] = declare_node

def p_declare_id_list(p):
    '''declare_id_list : TkId
                       | TkId TkComma declare_id_list'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = f"{p[1]},{p[3]}"

def p_assignment_stmt(p):
    '''assignment_stmt : TkId TkAsig expr'''
    node = Asig()
    # Obtenemos la ubicación del token TkId (p[1])
    lineno = p.lineno(1)
    col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
    # Creamos el nodo Ident con la ubicación
    node.add_child(Ident(p[1], lineno, col_offset))
    node.add_child(p[3])
    p[0] = node

def p_print_stmt(p):
    '''print_stmt : TkPrint expr'''
    node = Print()
    node.add_child(p[2])
    p[0] = node

def p_skip_stmt(p):
    '''skip_stmt : TkSkip'''
    p[0] = skip()

def p_return_stmt(p):
    '''return_stmt : TkReturn expr'''
    node = Return()
    node.add_child(p[2])
    p[0] = node

def p_while_stmt(p):
    '''while_stmt : TkWhile expr TkArrow body_sequencing TkEnd'''
    while_node = While()
    then_node = Then()
    then_node.add_child(p[2])
    then_node.add_child(p[4])
    while_node.add_child(then_node)
    p[0] = while_node

def p_if_stmt(p):
    '''if_stmt : TkIf if_guards_list TkFi'''
    if_node = If()
    # p[2] es una lista de nodos Guard
    for guard_node in p[2]:
        if_node.add_child(guard_node)
    p[0] = if_node

def p_if_guards_list(p):
    '''if_guards_list : if_guard_clause
                     | if_guard_clause TkGuard if_guards_list'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_if_guard_clause(p):
    '''if_guard_clause : expr TkArrow body_sequencing'''
    guard_node = Guard()
    guard_node.add_child(p[1]) # Condición
    guard_node.add_child(p[3]) # Cuerpo
    p[0] = guard_node


def p_body_sequencing(p):
    '''body_sequencing : body_stmt_item
                       | body_stmt_item TkSemicolon body_sequencing'''
    if len(p) == 2:
        # Si es un solo item, no se necesita secuenciador
        if isinstance(p[1], (Block, Asig, Print, skip, Return, If, While)):
            p[0] = p[1]
        else:
            seq_node = Sequencing()
            seq_node.add_child(p[1])
            p[0] = seq_node
    else:
        # Si el lado derecho ya es una secuencia, agregar al inicio
        if isinstance(p[3], Sequencing):
            p[3].children.insert(0, p[1])
            p[0] = p[3]
        else: # Si no, crear una nueva secuencia
            seq_node = Sequencing()
            seq_node.add_child(p[1])
            seq_node.add_child(p[3])
            p[0] = seq_node

def p_body_stmt_item(p):
    '''body_stmt_item : assignment_stmt
                      | print_stmt
                      | skip_stmt
                      | return_stmt
                      | if_stmt
                      | while_stmt
                      | block'''
    p[0] = p[1]

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
            | expr TkComma expr
            | expr TkTwoPoints expr'''
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
    elif p[2] == ',': node = Comma()
    elif p[2] == ':': node = TwoPoints()
    else: raise ValueError(f"Operador binario desconocido: {p[2]}")
    node.lineno = p.lineno(2)
    node.col_offset = find_column(p.lexer.lexdata, p.lexpos(2))
    node.add_child(p[1])
    node.add_child(p[3])
    p[0] = node

def p_expr_uminus(p):
    'expr : TkMinus expr %prec UMINUS'
    node = Minus()
    node.lineno = p.lineno(1) # El operador es el primer token
    node.col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
    node.add_child(p[2])
    p[0] = node

def p_expr_not(p):
    'expr : TkNot expr'
    node = Not()
    node.lineno = p.lineno(1) # El operador es el primer token
    node.col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
    node.add_child(p[2])
    p[0] = node

def p_expr_atom(p):
    '''expr : atom'''
    p[0] = p[1]


def p_atom(p):
    '''atom : atom TkApp simple_atom %prec TkApp
            | atom TkOpenPar expr TkClosePar %prec TkOpenPar
            | simple_atom'''
    if len(p) == 2:
        p[0] = p[1]
    elif p.slice[2].type == 'TkApp':
        node = ReadFunction() 
        node.add_child(p[1])
        node.add_child(p[3])
        p[0] = node
    elif p.slice[2].type == 'TkOpenPar':
        node = App()
        node.add_child(p[1])
        node.add_child(p[3])
        p[0] = node

def p_simple_atom(p):
    '''simple_atom : TkId
                   | TkNum
                   | TkTrue
                   | TkFalse
                   | TkString
                   | TkOpenPar expr TkClosePar'''
    if p.slice[1].type == 'TkId':
        lineno = p.lineno(1)
        col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
        p[0] = Ident(p[1], lineno, col_offset)
    elif p.slice[1].type == 'TkNum':
        lineno = p.lineno(1)
        col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
        p[0] = Literal(p[1], lineno, col_offset) # Pasamos la ubicación
    elif p.slice[1].type in ['TkTrue', 'TkFalse']:
        lineno = p.lineno(1)
        col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
        p[0] = Literal(p[1], lineno, col_offset) # Pasamos la ubicación
    elif p.slice[1].type == 'TkString':
        # Los strings también necesitan ubicación si quieres reportar errores sobre ellos
        lineno = p.lineno(1)
        col_offset = find_column(p.lexer.lexdata, p.lexpos(1))
        valor_con_comillas = f'"{p[1]}"'
        p[0] = String(valor_con_comillas)
        p[0].lineno = lineno
        p[0].col_offset = col_offset
    elif p.slice[1].type == 'TkOpenPar': 
        p[0] = p[2]

def p_empty(p):
    '''empty :'''
    p[0] = None

def find_column(input_str, token_lexpos):
    last_cr = input_str.rfind('\n', 0, token_lexpos)
    return (token_lexpos - last_cr) if last_cr >= 0 else token_lexpos + 1

parser_input_text = ""
def p_error(p):
    if p:
        col = find_column(p.lexer.lexdata, p.lexpos)
        print(f"Sintax error in row {p.lineno}, column {col}: unexpected token '{p.value}'.")
    else:
        print("Syntax error at EOF.")
    sys.exit(1)

# Construcción del parser
parser = yacc.yacc(debug=False, write_tables=False)
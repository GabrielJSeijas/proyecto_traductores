# Autores: Angel Valero 18-10436 y Gabriel Seijas 19-00036 
import sys
import ply.lex as lex

# Definición de los tokens
tokens = [
    'TkIf', 'TkFi', 'TkWhile', 'TkEnd', 'TkInt', 'TkFunction', 'TkPrint',
    'TkReturn', 'TkTrue', 'TkFalse', 'TkSkip', 'TkBool',
    'TkId', 'TkNum', 'TkString',
    'TkOBlock', 'TkCBlock', 'TkSoForth', 'TkComma', 'TkOpenPar', 'TkClosePar',
    'TkAsig', 'TkSemicolon', 'TkArrow', 'TkGuard', 'TkPlus', 'TkMinus', 'TkMult',
    'TkOr', 'TkAnd', 'TkNot', 'TkLess', 'TkLeq', 'TkGeq', 'TkGreater', 'TkEqual',
    'TkNEqual', 'TkOBracket', 'TkCBracket', 'TkTwoPoints', 'TkApp'
]

# Definición de palabras reservadas
reserved = {
    'if': 'TkIf', 'while': 'TkWhile', 'end': 'TkEnd', 'int': 'TkInt',
    'function': 'TkFunction', 'print': 'TkPrint', 'return': 'TkReturn',
    'true': 'TkTrue', 'false': 'TkFalse', 'or': 'TkOr', 'and': 'TkAnd',
    'fi': 'TkFi', 'skip': 'TkSkip', 'else': 'TkElse', 'bool': 'TkBool'
}

# Definición de los tokens
t_TkOBlock = r'\{'
t_TkCBlock = r'\}'
t_TkComma = r','
t_TkOpenPar = r'\('
t_TkClosePar = r'\)'
t_TkSemicolon = r';'
t_TkPlus = r'\+'
t_TkMinus = r'-'
t_TkMult = r'\*'
t_TkNot = r'!'
t_TkLess = r'<'
t_TkGreater = r'>'
t_TkOBracket = r'\['
t_TkCBracket = r'\]'
t_TkTwoPoints = r':'
t_TkApp = r'\.'

# Definición de operador lógico
def t_TkSoForth(t):
    r'\.\.'
    return t

# Definición de operador lógico
def t_TkAsig(t):
    r':='
    return t

# Definición de operador lógico
def t_TkArrow(t):
    r'-->'
    return t

# Definición de operador lógico
def t_TkGuard(t):
    r'\[\]'
    return t

# Definición de operador lógico
def t_TkLeq(t):
    r'<='
    return t

# Definición de operador mayor o igual
def t_TkGeq(t):
    r'>='
    return t

# Definición de operador lógico
def t_TkEqual(t):
    r'=='
    return t

# Definición de operador no igual
def t_TkNEqual(t):
    r'<>'
    return t

# Definición de los tokens de palabras reservadas
def t_TkNum(t):
    r'\d+'
    t.value = int(t.value)
    return t
# Definición de identificadores
def t_TkId(t):
    r'[_a-zA-Z][_a-zA-Z0-9]*'
    t.type = reserved.get(t.value, 'TkId')
    return t

# Definición de la cadena de caracteres
def t_TkString(t):
    r'"([^"\\\n]|\\["\\n\\])*"'
    # Verificar si la cadena es válida
    raw = t.value[1:-1]
    result = ""
    i = 0
    # Verificar si hay un salto de línea literal
    while i < len(raw):
        if raw[i] == '\\':
            i += 1
            if i >= len(raw): break
            if raw[i] == 'n': result += '\\n'
            elif raw[i] == '"': result += '\\"'
            elif raw[i] == '\\': result += '\\\\'
            else:
                col = find_column(t.lexer.lexdata, t.lexpos + i)
                if not hasattr(t.lexer, 'errors'):
                    t.lexer.errors = []
                t.lexer.errors.append((t.lineno, col, 'Unexpected character "\\"'))
                return None
        else:
            result += raw[i]
        i += 1
    t.value = result
    return t

# Definición de la cadena de caracteres con error
def t_error_string(t):
    r'"([^"\\\n]|\\.)*'

    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = []

    # Error: comilla inicial
    col_start = find_column(t.lexer.lexdata, t.lexpos)
    t.lexer.errors.append((t.lineno, col_start, 'Unexpected character "\""'))

    # Buscar '\' inválida después de salto de línea literal
    raw = t.value
    pos_backslash = None
    for i in range(1, len(raw)):
        if raw[i] == '\\':
            if i + 1 >= len(raw) or raw[i + 1] not in ['"', '\\', 'n']:
                pos_backslash = t.lexpos + i
                break
    
    # Error: barra inválida
    if pos_backslash:
        line_bs = t.lexer.lexdata.count('\n', 0, pos_backslash) + 1
        col_bs = find_column(t.lexer.lexdata, pos_backslash)
        t.lexer.errors.append((line_bs, col_bs, 'Unexpected character "\\"'))

    # Revisar si hay una barra problemática
    for i in range(1, len(t.value)):
        if t.value[i] == '\\':
            if i + 1 >= len(t.value) or t.value[i + 1] not in ['"', '\\', 'n']:
                col_backslash = find_column(t.lexer.lexdata, t.lexpos + i)
                t.lexer.errors.append((t.lineno, col_backslash, 'Unexpected character "\\"'))
                break

    # Avanzar línea si contiene salto literal
    # Aumenta primero las líneas por saltos literales
    t.lexer.lineno += t.value.count('\n')
# Luego busca la comilla de cierre
    after = t.lexer.lexdata[t.lexpos + len(t.value):]
    quote_pos = after.find('"')
    if quote_pos != -1:
        abs_pos = t.lexpos + len(t.value) + quote_pos
        quote_line = t.lexer.lexdata.count('\n', 0, abs_pos) + 1
        quote_col = find_column(t.lexer.lexdata, abs_pos)
        t.lexer.errors.append((quote_line, quote_col, 'Unexpected character "\""'))

t_ignore = ' \t'

# Definición de los comentarios
def t_comment(t):
    r'//.*'
    pass

# Definición de los comentarios multilínea
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Definición de los errores
def t_error(t):
    if not hasattr(t.lexer, 'errors'): t.lexer.errors = []
    if t.value[0] == '"':
        t.lexer.skip(1)
        return
    col = find_column(t.lexer.lexdata, t.lexpos)
    t.lexer.errors.append((t.lineno, col, f'Unexpected character "{t.value[0]}"'))
    t.lexer.skip(1)

# Función para encontrar la columna de un token
def find_column(input_str, lexpos):
    last_cr = input_str.rfind('\n', 0, lexpos)
    return lexpos + 1 if last_cr < 0 else (lexpos - last_cr)

lexer = lex.lex()
# Función principal
def main():
    # Verificar si se pasó un argumento
    if len(sys.argv) != 2:
        print("Uso: python lexer.py archivo.imperat")
        sys.exit(1)
    # Verificar si el archivo tiene la extensión correcta
    filename = sys.argv[1]
    if not filename.endswith('.imperat'):
        print("Error: El archivo debe tener extensión .imperat")
        sys.exit(1)

    # Crear el lexer
    try:
        with open(filename, 'r') as file:
            data = file.read()

        lexer.input(data)
        lexer.lineno = 1

    # Verificar si hay errores en el lexer
        if hasattr(lexer, 'errors'):
            del lexer.errors

        while lexer.token(): pass

        if hasattr(lexer, 'errors') and lexer.errors:
            for l, c, msg in sorted(set(lexer.errors), key=lambda x: (x[0], x[1])):
                print(f'Error: {msg} in row {l}, column {c}')
            sys.exit(1)
    # Si no hay errores, imprimir los tokens
        lexer.input(data)
        lexer.lineno = 1

        # Imprimir los tokens
        for token in lexer:
            col = find_column(data, token.lexpos)
            if token.type == 'TkNum':
                print(f'{token.type}({token.value}) {token.lineno} {col}')
            elif token.type in ['TkId', 'TkString']:
                print(f'{token.type}("{token.value}") {token.lineno} {col}')
            else:
                print(f'{token.type} {token.lineno} {col}')

# Si hay errores en el lexer, imprimirlos
    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo {filename}")
        sys.exit(1)

# Si el archivo no tiene la extensión correcta, imprimir un mensaje de error
if __name__ == '__main__': 
    main()
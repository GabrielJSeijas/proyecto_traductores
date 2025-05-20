
import sys
import ply.lex as lex

# Lista de nombres de tokens
tokens = [
    # Palabras clave
    'TkIf', 'TkWhile', 'TkEnd', 'TkInt', 'TkFunction', 'TkPrint', 'TkReturn','TkTrue', 'TkFalse',
    
    # Identificadores y literales
    'TkId', 'TkNum', 'TkString',
    
    # Símbolos
    'TkOBlock', 'TkCBlock', 'TkSoForth', 'TkComma', 'TkOpenPar', 'TkClosePar',
    'TkAsig', 'TkSemicolon', 'TkArrow', 'TkGuard', 'TkPlus', 'TkMinus', 'TkMult',
    'TkOr', 'TkAnd', 'TkNot', 'TkLess', 'TkLeq', 'TkGeq', 'TkGreater', 'TkEqual',
    'TkNEqual', 'TkOBracket', 'TkCBracket', 'TkTwoPoints', 'TkApp'
]

# Palabras reservadas (mapeo a tokens)
reserved = {
    'if': 'TkIf',
    'while': 'TkWhile',
    'end': 'TkEnd',
    'int': 'TkInt',
    'function': 'TkFunction',
    'print': 'TkPrint',
    'return': 'TkReturn',
    'true': 'TkTrue',
    'false': 'TkFalse',
    'or': 'TkOr',
    'and': 'TkAnd'
}

# Expresiones regulares para tokens simples
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
t_TkTwoPoints = r'\.'
t_TkApp = r'\.'

# Tokens que necesitan procesamiento especial
def t_TkSoForth(t):
    r'\.\.'
    return t

def t_TkAsig(t):
    r':='
    return t

def t_TkArrow(t):
    r'-->'
    return t

def t_TkGuard(t):
    r'\[\]'
    return t

def t_TkLeq(t):
    r'<='
    return t

def t_TkGeq(t):
    r'>='
    return t

def t_TkEqual(t):
    r'=='
    return t

def t_TkNEqual(t):
    r'<>'
    return t


def t_TkNum(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_TkId(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'TkId')  # Verificar palabras reservadas
    return t

# Ignorar espacios y tabulaciones
t_ignore = ' \t'

# Manejo de comentarios (ignorar)
def t_comment(t):
    r'//.*'
    pass

# Manejo de saltos de línea
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.lexpos = t.lexer.lexpos  # Esto ayuda a mantener las posiciones correctas

# Manejo de errores
def t_error(t):
    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = []
    
    # Caracteres que siempre son errores (incluyendo " y \)
    if t.value[0] in ['"', '\\']:
        column = find_column(t.lexer.lexdata, t.lexpos)
        error_msg = f'Error: Unexpected character "{t.value[0]}" in row {t.lineno}, column {column}'
        t.lexer.errors.append(error_msg)
        t.lexer.skip(1)
        return
    
    # Manejo especial para : y =
    if t.value[0] == ':':
        t.lexer.skip(1)
        return
    if t.value[0] == '=' and t.lexer.lexpos > 0 and t.lexer.lexdata[t.lexpos - 1] == ':':
        t.lexer.skip(1)
        return
    
    # Otros caracteres inesperados
    column = find_column(t.lexer.lexdata, t.lexpos)
    error_msg = f'Error: Unexpected character "{t.value[0]}" in row {t.lineno}, column {column}'
    t.lexer.errors.append(error_msg)
    t.lexer.skip(1)

# Función para calcular la columna
def find_column(input_str, lexpos):
    last_cr = input_str.rfind('\n', 0, lexpos)
    if last_cr < 0:
        return lexpos + 1
    return (lexpos - last_cr)

# Construir el lexer
lexer = lex.lex()

def main():
    if len(sys.argv) != 2:
        print("Uso: python lexer.py archivo.imperat")
        sys.exit(1)
    
    filename = sys.argv[1]
    if not filename.endswith('.imperat'):
        print("Error: El archivo debe tener extensión .imperat")
        sys.exit(1)
    
    try:
        with open(filename, 'r') as file:
            data = file.read().strip()
        
        lexer.input(data)
        lexer.lineno = 1  # Reiniciar contador de líneas
        
        # Lista para almacenar errores
        errors = []
        
        # Tokenizar y capturar errores
        while True:
            tok = lexer.token()
            if not tok: 
                break  # No hay más tokens
            
            # Si es un error, se maneja en t_error()
        
        # Si hay errores, imprimirlos y salir
        if hasattr(lexer, 'errors') and lexer.errors:
            for error in lexer.errors:
                print(error)
            sys.exit(1)
        
        # Si no hay errores, procesar tokens normalmente
        lexer.input(data)  # Reiniciamos el lexer
        lexer.lineno = 1  # Reiniciamos contador nuevamente

        
        tokens = list(lexer)  # Convertir a lista para saber el último token
        for i, token in enumerate(tokens):
            if token.type in ['TkId', 'TkNum', 'TkString']:
                if token.type == 'TkNum':
                    line = f"{token.type}({token.value}) {token.lineno} {find_column(data, token.lexpos)}"
                else:
                    line = f"{token.type}(\"{token.value}\") {token.lineno} {find_column(data, token.lexpos)}"
            else:
                line = f"{token.type} {token.lineno} {find_column(data, token.lexpos)}"
    
                # Solo agregar salto de línea si no es el último token
            if i < len(tokens) - 1:
                print(line)
            else:
                print(line, end='')  # Último token sin salto de línea
    
    except FileNotFoundError:
            print(f"Error: No se pudo abrir el archivo {filename}")
            sys.exit(1)

if __name__ == '__main__':
    main()
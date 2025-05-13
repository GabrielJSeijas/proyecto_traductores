
import sys
import ply.lex as lex

# Lista de nombres de tokens
tokens = [
    # Palabras clave
    'TkIf', 'TkWhile', 'TkEnd', 'TkInt', 'TkFunction', 'TkPrint', 'TkReturn','TkTrue', 'TkFalse',
    
    # Identificadores y literales
    'TkId', 'TkNum', 'TkString',
    
    # Símbolos
    'Tk0Block', 'TkCBlock', 'TkSoForth', 'TkComma', 'TkOpenPar', 'TkClosePar',
    'TkAsig', 'TkSemicolon', 'TkArrow', 'TkGuard', 'TkPlus', 'TkMinus', 'TkMult',
    'TkOr', 'TkAnd', 'TkNot', 'TkLess', 'TkLeq', 'TkGeq', 'TkGreater', 'TkEqual',
    'TkNEqual', 'Tk0Bracket', 'TkCBracket', 'TkTwoPoints', 'TkApp'
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
t_Tk0Block = r'\{'
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
t_Tk0Bracket = r'\['
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

def t_TkString(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value[1:-1]  # Remover las comillas
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

# Manejo de errores
def t_error(t):
    # Inicializar lista de errores si no existe
    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = []
    
    # Calcular columna
    column = find_column(t.lexer.lexdata, t.lexpos)
    
    # Guardar el mensaje de error
    error_msg = f'Error: Unexpected character "{t.value[0]}" in row {t.lineno}, column {column}'
    t.lexer.errors.append(error_msg)
    
    # Saltar el caracter problemático
    t.lexer.skip(1)

# Función para calcular la columna
def find_column(input_str, lexpos):
    """Calcula la columna basada en la posición en el texto de entrada"""
    last_cr = input_str.rfind('\n', 0, lexpos)
    if last_cr < 0:
        last_cr = 0
    return (lexpos - last_cr) + 1

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
            data = file.read()
        
        lexer.input(data)
        
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
        for token in lexer:
            print(f"{token.type}", end=' ')
            if token.type in ['TkId', 'TkNum', 'TkString']:
                print(f"(\"{token.value}\")", end=' ')
            print(f"{token.lineno} {find_column(data, token.lexpos)}")
           
                
    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo {filename}")
        sys.exit(1)

if __name__ == '__main__':
    main()
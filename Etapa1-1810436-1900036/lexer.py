import sys
import ply.lex as lex

# 1. Definición de tokens según especificaciones del PDF
tokens = [
    # Palabras reservadas
    'TkIf', 'TkFi', 'TkWhile', 'TkEnd', 'TkInt', 'TkFunction', 'TkPrint',
    'TkReturn', 'TkTrue', 'TkFalse', 'TkSkip', 'TkElse', 'TkBool',

    # Identificadores y literales
    'TkId', 'TkNum', 'TkString',

    # Símbolos y operadores
    'TkOBlock', 'TkCBlock', 'TkSoForth', 'TkComma', 'TkOpenPar', 'TkClosePar',
    'TkAsig', 'TkSemicolon', 'TkArrow', 'TkGuard', 'TkPlus', 'TkMinus', 'TkMult',
    'TkOr', 'TkAnd', 'TkNot', 'TkLess', 'TkLeq', 'TkGeq', 'TkGreater', 'TkEqual',
    'TkNEqual', 'TkOBracket', 'TkCBracket', 'TkTwoPoints', 'TkApp'
]

# 2. Palabras reservadas con sus tokens correspondientes
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
    'and': 'TkAnd',
    'fi': 'TkFi',
    'skip': 'TkSkip',
    'else': 'TkElse',
    'bool': 'TkBool'
}

# 3. Expresiones regulares para tokens simples
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

# 4. Tokens complejos que necesitan funciones especiales
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
    r'[_a-zA-Z][_a-zA-Z0-9]*'
    t.type = reserved.get(t.value, 'TkId')  # Verifica si es palabra reservada
    return t

def t_TkString(t):
    r'\"((?:[^"\\]|\\.)*)'
    
    # Inicializar lista de errores si no existe
    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = []
    
    start_quote_pos = t.lexpos
    content = t.value[1:]  # Elimina la comilla inicial
    next_char_pos = t.lexpos + len(t.value)
    
    # Verificar si el string está cerrado
    is_closed = next_char_pos < len(t.lexer.lexdata) and t.lexer.lexdata[next_char_pos] == '"'
    
    # Siempre reportar la comilla inicial como error primero
    t.lexer.errors.append((t.lineno, find_column(t.lexer.lexdata, start_quote_pos), 'Unexpected character """'))
    
    # Verificar errores en el contenido
    has_errors = False
    i = 0
    while i < len(content):
        if content[i] == '\\':
            if i + 1 >= len(content):
                # Barra al final del string (sin carácter escapado)
                t.lexer.errors.append((t.lineno, find_column(t.lexer.lexdata, start_quote_pos + 1 + i), 'Unexpected character "\\\"'))
                has_errors = True
                break
            escaped_char = content[i+1]
            if escaped_char not in ('"', '\\', 'n'):
                t.lexer.errors.append((t.lineno, find_column(t.lexer.lexdata, start_quote_pos + 1 + i), 'Unexpected character "\\\"'))
                has_errors = True
            i += 1  # Saltar el carácter escapado
        elif content[i] == '\n':
            # Salto de línea literal no permitido - buscar el backslash después del newline
            newline_pos = start_quote_pos + 1 + i
            remaining_text = t.lexer.lexdata[newline_pos+1:next_char_pos]
            
            # Buscar el primer backslash después del newline
            backslash_pos = remaining_text.find('\\')
            if backslash_pos != -1:
                error_pos = newline_pos + 1 + backslash_pos
                t.lexer.errors.append((t.lineno, find_column(t.lexer.lexdata, error_pos), 'Unexpected character "\\\"'))
                has_errors = True
            break
        i += 1
    
    # Si hay errores o no está cerrado, reportar también la comilla final
    if has_errors or not is_closed:
        if is_closed:
            t.lexer.errors.append((t.lineno, find_column(t.lexer.lexdata, next_char_pos), 'Unexpected character """'))
        t.lexer.skip(len(t.value) + (1 if is_closed else 0))  # Saltar todo el string incluyendo comilla final si existe
        return None
    
    # String válido
    t.value = content
    t.lexer.lexpos = next_char_pos + 1  # Saltar la comilla de cierre
    return t

# 5. Reglas para ignorar elementos
t_ignore = ' \t'  # Espacios y tabuladores

def t_comment(t):
    r'//.*'
    pass  # Los comentarios se ignoran

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)  # Actualiza el contador de líneas

# 6. Manejo de errores
def t_error(t):
    if not hasattr(t.lexer, 'errors'):
        t.lexer.errors = [] # Inicializa como lista si no existe

    # Manejo especial para comillas sueltas (si t_TkString no las procesó)
    if t.value[0] == '"':
        # Este caso podría ser para una comilla que t_TkString decidió no manejar
        # o una comilla de cierre de un string ya reportado como erróneo por t_TkString.
        # Si t_TkString ya avanzó el lexer, este 't.value[0]' podría ser parte de otro token.
        # La lógica de skip aquí es para comillas "huérfanas".
        t.lexer.skip(1)
        return

    column = find_column(t.lexer.lexdata, t.lexpos)
    # Crear el mensaje base sin "Error: " ni la información de línea/columna
    msg_core = f'Unexpected character "{t.value[0]}"'
    # Añadir la tupla (linea, columna, mensaje_base)
    t.lexer.errors.append((t.lineno, column, msg_core))
    t.lexer.skip(1)

# 7. Función auxiliar para calcular columnas
def find_column(input_str, lexpos):
    last_cr = input_str.rfind('\n', 0, lexpos)
    if last_cr < 0:
        return lexpos + 1
    return (lexpos - last_cr)

# 8. Construcción del lexer
lexer = lex.lex()

# 9. Función principal
def main():
    # Validación de argumentos
    if len(sys.argv) != 2:
        print("Uso: python lexer.py archivo.imperat")
        sys.exit(1)

    filename = sys.argv[1]
    if not filename.endswith('.imperat'):
        print("Error: El archivo debe tener extensión .imperat")
        sys.exit(1)

    try:
        # Lectura del archivo
        with open(filename, 'r') as file:
            data = file.read()

        lexer.input(data)
        lexer.lineno = 1 # Asegurar que lineno se reinicia

        # Procesamiento de tokens para acumularlos y detectar errores
        # No es necesario hacer dos pasadas si t_TkString y t_error manejan bien los errores.
        # El atributo lexer.errors acumulará los errores.
        
        output_tokens = []
        # Reiniciar errors por si acaso (aunque lex.lex() debería dar una instancia fresca)
        if hasattr(lexer, 'errors'):
            del lexer.errors

        while True:
            tok = lexer.token()
            if not tok:
                break
            # Solo añadimos tokens válidos a la salida si no estamos en modo error "catastrófico"
            # Pero para este problema, siempre intentamos seguir.
            # Los tokens que retornan None desde su función (como t_TkString en error) no llegan aquí.
            output_tokens.append(tok)

        # Manejo de errores acumulados
        if hasattr(lexer, 'errors') and lexer.errors:
            # lexer.errors es ahora una lista de tuplas (line, col, msg_core)
            # 1. Eliminar duplicados exactos (si los hubiera) usando set.
            # 2. Ordenar las tuplas de error: primero por número de línea, luego por número de columna.
            unique_error_tuples = sorted(list(set(lexer.errors)), key=lambda e: (e[0], e[1]))
            
            for line, col, msg_core in unique_error_tuples:
                print(f'Error: {msg_core} in row {line}, column {col}')
            sys.exit(1)
        
        # Si no hubo errores, proceder a la segunda pasada para la salida normal
        # (Este bloque solo se ejecuta si no hubo sys.exit(1) arriba)
        lexer.input(data) # Reiniciar el lexer para la segunda pasada
        lexer.lineno = 1
        if hasattr(lexer, 'errors'): # Limpiar errores si se van a re-evaluar (aunque no debería haberlos ahora)
            del lexer.errors

        for token in lexer:
            if token.type == 'TkNum':
                print(f"{token.type}({token.value}) {token.lineno} {find_column(data, token.lexpos)}")
            elif token.type in ['TkId', 'TkString']:
                # Para TkString válidos, t.value ya no tiene comillas por el procesamiento en t_TkString
                print(f"{token.type}(\"{token.value}\") {token.lineno} {find_column(data, token.lexpos)}")
            else:
                print(f"{token.type} {token.lineno} {find_column(data, token.lexpos)}")


        for token in lexer: # Esto re-tokenizará
            # Evitar procesar si la pasada anterior encontró errores y ya salimos.
            # Esta parte solo se ejecuta si no hubo errores en la primera "recolección".
            if token.type == 'TkNum':
                print(f"{token.type}({token.value}) {token.lineno} {find_column(data, token.lexpos)}")
            elif token.type in ['TkId', 'TkString']:
                print(f"{token.type}(\"{token.value}\") {token.lineno} {find_column(data, token.lexpos)}")
            else:
                print(f"{token.type} {token.lineno} {find_column(data, token.lexpos)}")

    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo {filename}")
        sys.exit(1)

if __name__ == '__main__':
    main()
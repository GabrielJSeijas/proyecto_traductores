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
    r'\"((?:[^"\\]|\\.)*|\n)*' # Regex permite capturar contenido multilínea

    potential_closing_quote_pos = t.lexpos + len(t.value)
    actually_closed_by_quote_char = False
    if potential_closing_quote_pos < len(t.lexer.lexdata) and \
       t.lexer.lexdata[potential_closing_quote_pos] == '"':
        actually_closed_by_quote_char = True

    # --- Comprobación de malformaciones internas ---
    content_without_initial_quote = t.value[1:]

    # 1. Salto de línea literal (problema principal para el segundo ejemplo)
    has_literal_newline = '\n' in content_without_initial_quote
    literal_newline_details = [] # (line, col) de la barra que causa el problema en la línea siguiente
    if has_literal_newline:
        # Necesitamos encontrar la posición de la '\' en la línea *siguiente* al salto literal,
        # si es que esa '\' es la que se reporta.
        # El ejemplo "Hola mund\n o. \n" tiene un salto literal. La '\' de "o. \n"
        # está en la línea siguiente a ese salto.
        first_literal_newline_idx_in_content = content_without_initial_quote.find('\n')
        # Posición absoluta del primer \n literal
        first_literal_newline_abs_pos = t.lexpos + 1 + first_literal_newline_idx_in_content
        
        # Buscar una '\' DESPUÉS de este \n literal, dentro del t.value consumido
        search_start_for_backslash = first_literal_newline_abs_pos + 1
        search_end_for_backslash = t.lexpos + len(t.value)
        try:
            # Buscamos la primera '\' después del salto de línea literal
            backslash_after_newline_abs_pos = t.lexer.lexdata.index('\\', search_start_for_backslash, search_end_for_backslash)
            
            # Verificar que esta barra invertida esté en la línea inmediatamente siguiente al salto de línea literal.
            # Esto es para asegurar que reportamos la barra correcta del ejemplo.
            line_of_backslash = t.lexer.lexdata.count('\n', 0, backslash_after_newline_abs_pos) + 1
            line_of_literal_newline = t.lexer.lexdata.count('\n', 0, first_literal_newline_abs_pos) + 1

            if line_of_backslash == line_of_literal_newline + 1: # Si está en la siguiente línea
                col_of_backslash = find_column(t.lexer.lexdata, backslash_after_newline_abs_pos)
                literal_newline_details.append((line_of_backslash, col_of_backslash))
        except ValueError:
            pass # No se encontró '\' después del salto de línea literal en el resto del string

    # 2. Secuencia de escape inválida (ej: \b)
    has_invalid_escape = False
    invalid_escape_details = [] # (line, col) de la '\' que inicia el escape inválido

    i = 0
    while i < len(content_without_initial_quote):
        if content_without_initial_quote[i] == '\\':
            if i + 1 < len(content_without_initial_quote):
                next_char = content_without_initial_quote[i+1]
                if next_char not in ('"', '\\', 'n', '\n'): # Permitimos \n como secuencia de escape válida
                    # PERO si next_char es \n, esto NO es un error de "escape inválido"
                    # sino un problema de "salto de línea literal" si el \n es literal.
                    # La regex ya permite \. que incluye \n (secuencia),
                    # y también \n (literal). Debemos ser cuidadosos.
                    # Un escape inválido es \ seguido de algo que no sea ", \, n.
                    # Si es \ seguido de \n literal, has_literal_newline lo captura.
                    if next_char != '\n': # Solo marcamos como inválido si no es \n (ya que \n es escape válido)
                        has_invalid_escape = True
                        backslash_abs_pos = t.lexpos + 1 + i
                        backslash_line = t.lexer.lexdata.count('\n', 0, backslash_abs_pos) + 1
                        backslash_col = find_column(t.lexer.lexdata, backslash_abs_pos)
                        invalid_escape_details.append((backslash_line, backslash_col))
                        break 
                i += 1 
            else: # Barra al final
                has_invalid_escape = True
                backslash_abs_pos = t.lexpos + 1 + i
                backslash_line = t.lexer.lexdata.count('\n', 0, backslash_abs_pos) + 1
                backslash_col = find_column(t.lexer.lexdata, backslash_abs_pos)
                invalid_escape_details.append((backslash_line, backslash_col))
                break
        i += 1
    
    is_malformed = has_literal_newline or has_invalid_escape

    # --- Generación de errores ---
    if not actually_closed_by_quote_char or is_malformed:
        if not hasattr(t.lexer, 'errors'):
            t.lexer.errors = []

        # Error 1: Comilla inicial
        start_quote_pos = t.lexpos
        start_col = find_column(t.lexer.lexdata, start_quote_pos)
        t.lexer.errors.append((t.lineno, start_col, 'Unexpected character """'))

        # Error 2: Barra invertida. Prioridad a la del salto de línea literal si existe y es relevante.
        if has_literal_newline and literal_newline_details:
            # Este es el caso para el string con salto de línea literal.
            # Usar los detalles de la barra después del salto literal.
            esc_line, esc_col = literal_newline_details[0]
            t.lexer.errors.append((esc_line, esc_col, 'Unexpected character "\\\"'))
        elif has_invalid_escape and invalid_escape_details:
            # Este es el caso para secuencias de escape inválidas como \b.
            esc_line, esc_col = invalid_escape_details[0]
            t.lexer.errors.append((esc_line, esc_col, 'Unexpected character "\\\"'))


        # Error 3: Comilla final
        if actually_closed_by_quote_char and is_malformed:
            closing_quote_line = t.lexer.lexdata.count('\n', 0, potential_closing_quote_pos) + 1
            closing_quote_col = find_column(t.lexer.lexdata, potential_closing_quote_pos)
            t.lexer.errors.append((closing_quote_line, closing_quote_col, 'Unexpected character """'))
        
        t.lexer.lexpos += len(t.value)
        if actually_closed_by_quote_char:
            t.lexer.lexpos += 1
        return None
    
    # String válido
    t.value = t.value[1:] 
    t.lexer.lexpos += 1 
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
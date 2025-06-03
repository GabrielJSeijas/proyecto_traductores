import sys
from lexer import lexer # Importa la instancia del lexer
from parser import parser, parser_input_text # Importa el parser y la variable global
# from ast_nodes import ASTNode # No necesitas ASTNode directamente aquí si parser devuelve el AST raíz

def main():
    if len(sys.argv) != 2:
        print("Usage: python parse.py <filename.imperat>")
        sys.exit(1)
    
    filename = sys.argv[1]
    if not filename.endswith('.imperat'):
        print("Error: El archivo debe tener extensión .imperat")
        sys.exit(1)
        
    try:
        with open(filename, 'r') as file:
            data = file.read()
    except IOError:
        print(f"Error: Could not open file {filename}")
        sys.exit(1)
    
    # Configurar el lexer
    lexer.input(data)
    lexer.lineno = 1 # Reiniciar contador de líneas del lexer
    
    # Limpiar errores previos del lexer si los hubiera de una ejecución anterior en el mismo intérprete
    if hasattr(lexer, 'errors'):
        del lexer.errors

    # Primera pasada del lexer para recolectar todos los errores léxicos
    # (Esto es opcional si tu lexer ya aborta en el primer error o los acumula bien)
    # Podrías tokenizar una vez para capturar errores léxicos.
    temp_lexer_errors = []
    temp_lexer = lexer.clone() # Clonar para no afectar el estado para el parser
    temp_lexer.input(data)
    temp_lexer.lineno = 1
    
    while True:
        tok = temp_lexer.token()
        if not tok:
            break
    
    if hasattr(temp_lexer, 'errors') and temp_lexer.errors:
        for l, c, msg in sorted(set(temp_lexer.errors), key=lambda x: (x[0], x[1])):
            print(f'Error: {msg} in row {l}, column {c}') # Formato de error léxico
        sys.exit(1) # Abortar si hay errores léxicos

    # Si no hay errores léxicos, proceder con el parsing
    # Reiniciar el lexer principal para el parser
    lexer.input(data)
    lexer.lineno = 1
    
    # Pasar 'data' al parser para la función p_error
    # Esto se hace asignando a la variable global importada de parser.py
    globals_parser = sys.modules['parser'] # Obtener el módulo parser
    globals_parser.parser_input_text = data


    # Parsear y construir el AST
    # El parser usará la instancia 'lexer' que ya tiene los datos.
    ast = parser.parse(lexer=lexer, tracking=True) # tracking=True puede ayudar a p_error
    
    if ast is not None:
        # La impresión del AST se delega al método __str__ del nodo raíz del AST.
        # Elimina el .strip() si tu __str__ ya maneja bien los saltos de línea finales.
        print(str(ast).strip()) 
    # else: El parser ya debería haber salido con sys.exit(1) en p_error

if __name__ == '__main__':
    main()
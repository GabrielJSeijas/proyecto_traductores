# Autores: Angel Valero 18-10436 y Gabriel Seijas 19-00036 
import sys
from lexer import lexer
from parser import parser, parser_input_text
from type_checker import TypeChecker
from symbol_table import SymbolTable

def main():
    # Verifica que se reciba exactamente un argumento (el nombre del archivo)
    if len(sys.argv) != 2:
        print("Usage: python parse.py <filename.imperat>")
        sys.exit(1)
    
    filename = sys.argv[1]
    # Verifica que el archivo tenga la extensión correcta
    if not filename.endswith('.imperat'):
        print("Error: El archivo debe tener extensión .imperat")
        sys.exit(1)
        
    try:
        # Lee el contenido del archivo de entrada
        with open(filename, 'r') as file:
            data = file.read()
    except IOError:
        print(f"Error: Could not open file {filename}")
        sys.exit(1)
    
    # Inicializa el lexer con el contenido del archivo
    lexer.input(data)
    lexer.lineno = 1

    # Limpia errores previos del lexer si existen
    if hasattr(lexer, 'errors'):
        del lexer.errors

    # Realiza un análisis léxico previo para detectar errores antes de parsear
    temp_lexer = lexer.clone()
    temp_lexer.input(data)
    temp_lexer.lineno = 1
    
    while True:
        tok = temp_lexer.token()
        if not tok:
            break
    
    # Si hay errores léxicos, los muestra y termina la ejecución
    if hasattr(temp_lexer, 'errors') and temp_lexer.errors:
        for l, c, msg in sorted(set(temp_lexer.errors), key=lambda x: (x[0], x[1])):
            print(f'Error: {msg} in row {l}, column {c}')
        sys.exit(1)

    # Si no hay errores léxicos, reinicia el lexer para el parser
    lexer.input(data)
    lexer.lineno = 1

    # Asigna el texto de entrada al parser para manejo de errores de sintaxis
    globals_parser = sys.modules['parser']
    globals_parser.parser_input_text = data

    # Realiza el análisis sintáctico y construye el AST
    ast = parser.parse(lexer=lexer, tracking=True)
    
    # Si el AST se construyó correctamente, realizar análisis de contexto
    if ast is not None:
        # Crear y ejecutar el verificador de tipos
        type_checker = TypeChecker()
        errors = type_checker.check_program(ast)
        
        if errors:
            # Mostrar solo el primer error de contexto encontrado
            print("Context Error:", errors[0])
            sys.exit(1)
        else:
            # Imprimir resultados exitosos
            print(str(ast).strip())
    # Si no se pudo construir el AST, muestra un mensaje de error
    else:
        print("Error: No AST generated")
        sys.exit(1)

if __name__ == '__main__':
    main()
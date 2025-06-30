# Autores: Angel Valero 18-10436 y Gabriel Seijas 19-00036 
import sys
from lexer import lexer
from parser import parser, parser_input_text
from type_checker import TypeChecker
from symbol_table import SymbolTable

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
        
        if not data:
            print("Error: El archivo está vacío")
            sys.exit(1)
        
        # Análisis léxico
        lexer.input(data)
        lexer.lineno = 1
        
        # Verificar errores léxicos
        if hasattr(lexer, 'errors') and lexer.errors:
            for error in sorted(set(lexer.errors), key=lambda x: (x[0], x[1]))[:1]:
                print(f"Lexical Error: {error[2]} in row {error[0]}, column {error[1]}")
            sys.exit(1)
        
        # Análisis sintáctico
        globals()['parser_input_text'] = data
        ast = parser.parse(lexer=lexer)
        
        if ast is None:
            print("Error: No se pudo generar el AST (posible error de sintaxis)")
            sys.exit(1)
        
        # Análisis de contexto
        type_checker = TypeChecker()
        errors = type_checker.check_program(ast)
        
        if errors:
    # Si el enunciado pide el error sin prefijo:
            print(errors[0]) 
    # Si el prefijo "Context Error:" es correcto, mantenlo como está:
    # print(f"Context Error: {errors[0]}")
            sys.exit(1)
        else:
            # Imprimir AST decorado
            ast_output = str(ast).strip()
            if ast_output:
                print(ast_output)
            else:
                print("Warning: El AST generado está vacío")
            
    except FileNotFoundError:
        print(f"Error: No se pudo abrir el archivo {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
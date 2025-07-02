import re
from ast_nodes import *
from symbol_table import SymbolTable

class TypeChecker:
    def __init__(self):
        self.errors = []
        self.current_table = SymbolTable()

    def check_program(self, ast_node):
        if isinstance(ast_node, ASTNode):
            self.check_node(ast_node)
        return self.errors[:1]  # Solo devolver el primer error

    def add_error(self, message, node=None):
        if not self.errors:
        # El que llama (como check_asig) ya formatea el mensaje completo con línea y columna.
        # Esta función solo debe añadirlo a la lista.
            self.errors.append(message)
        return "TYPE_ERROR"

          
    def _find_error_node(self, start_node):
        """Busca recursivamente el primer nodo marcado con type='TYPE_ERROR'."""
        if getattr(start_node, 'type', None) == "TYPE_ERROR":
            return start_node
        
        # El getattr es para evitar errores en nodos sin 'children'
        for child in getattr(start_node, 'children', []):
            found_node = self._find_error_node(child)
            if found_node:
                return found_node
        return None

    
    def check_node(self, node):
        class_name = type(node).__name__
        if class_name == "ReadFunction":
            method_name = "check_readfunction"
        elif class_name == "WriteFunction":
            method_name = "check_writefunction"
        elif class_name == "App":  
            method_name = "check_app"
        else:
            method_name = f'check_{class_name.lower()}'
            
        checker = getattr(self, method_name, self.generic_check)
        return checker(node)

    def generic_check(self, node):
        for child in node.children:
            self.check_node(child)
        return node.type

    def check_block(self, node):
        # Entrar en un nuevo ámbito
        self.current_table = self.current_table.enter_scope()
        node.symbol_table = self.current_table

        # Procesar declaraciones primero para poblar la tabla de símbolos
        for child in node.children:
            if isinstance(child, Declare):
                self.check_node(child)
        
        # Luego procesar el resto de las sentencias
        for child in node.children:
            if not isinstance(child, Declare):
                self.check_node(child)
        
        # Salir del ámbito
        self.current_table = self.current_table.exit_scope()
        return None

    def check_declare(self, node):
        decl_str = node.children[0]
        vars_part, type_part = decl_str.split(":", 1)
        var_names = [name.strip() for name in vars_part.split(",")]
        var_type = type_part.strip()
        
        for var_name in var_names:
            if not self.current_table.declare(var_name, var_type):
                self.add_error(f"Redeclaración de variable '{var_name}' en el mismo ámbito")
    
    def check_writefunction(self, node):
        # La lógica es idéntica a la de check_app
        func_node = node.children[0]
        arg_node = node.children[1]

        func_type = self.check_node(func_node)

        if func_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        if not (isinstance(func_type, str) and "function" in func_type):
            return self.add_error(f"Intento de llamar a un tipo no función ({func_type})", func_node)
    
        self.check_node(arg_node)
    
        node.type = func_type
        return func_type
    
    def check_asig(self, node):
        ident_node = node.children[0]
        expr_node = node.children[1]

        var_type = self.current_table.lookup(ident_node.name)
        if var_type is None:
            # Esto está bien, maneja el caso de variable no declarada.
            return self.add_error(f"Variable '{ident_node.name}' not declared", ident_node)

        expr_type = self.check_node(expr_node)

        # Si los tipos no coinciden, ENTONCES y SÓLO ENTONCES manejamos el error.
        if var_type != expr_type:
            # --- TODO ESTE BLOQUE DEBE ESTAR INDENTADO ---
            error_location_node = self._find_error_node(expr_node)
        
            line, col = None, None
        
            if error_location_node and error_location_node.lineno is not None:
                line = error_location_node.lineno
                col = error_location_node.col_offset
            else:
                # Fallback a la ubicación del := si no encontramos un error más específico.
                # Asegúrate de que tu parser guarda la ubicación en el nodo Asig.
                line = node.lineno
                col = node.col_offset
        
            error_message = f"Type error in line {line} and column {col}"
        
            return self.add_error(error_message)

        # Si no hubo error de tipos, continuamos normalmente.
        ident_node.type = var_type
        node.type = var_type
        return var_type

    # Si todo está bien, continuamos...
        ident_node.type = var_type
        node.type = var_type
        return var_type

    def _count_comma_elements(self, node):
        if isinstance(node, Comma):
            # Una coma une dos sub-expresiones, contamos los elementos de ambas.
            return self._count_comma_elements(node.children[0]) + self._count_comma_elements(node.children[1])
        return 1 # Cualquier otro nodo es un solo elemento.

    def check_comma(self, node):
        self.check_node(node.children[0])
        self.check_node(node.children[1])
        node.type = "function with length=2"
        return node.type
    
    def check_twopoints(self, node):
        # Este método es análogo a check_comma.
        # Asume que ':' combina dos elementos en una "función" de longitud 2.
        self.check_node(node.children[0])
        self.check_node(node.children[1])
        # Esto podría necesitar una lógica más compleja si anidas ':', pero para A(expr:expr) es suficiente.
        node.type = "function with length=2" 
        return node.type

    def check_ident(self, node):
        var_type = self.current_table.lookup(node.name)
        if var_type is None:
            return self.add_error(f"Variable '{node.name}' not declared", node)
        node.type = var_type
        return var_type

    def check_literal(self, node):
        return node.type

    def check_plus(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])

        # Caso 1: Ambos son enteros -> Suma aritmética
        if left_type == "int" and right_type == "int":
            node.type = "int"
            return "int"
        
        # Caso 2: Al menos uno es string -> Concatenación
        # Se permite concatenar string con int, bool o string.
        valid_concat_types = ["String", "int", "bool"]
        if left_type == "String" and right_type in valid_concat_types:
            # ¡Transformamos el nodo!
            node.__class__ = Concat
            node.type = "String"
            return "String"
        
        # También funciona si el string está a la derecha
        if right_type == "String" and left_type in valid_concat_types:
            # ¡Transformamos el nodo!
            node.__class__ = Concat
            node.type = "String"
            return "String"

        # Si no es ninguno de los casos anteriores, es un error.
        node.type = "TYPE_ERROR"  # Marcamos este nodo 'Plus' como el origen del error
        return "TYPE_ERROR"  
    
    def check_minus(self, node): return self.check_arithmetic(node)
    def check_mult(self, node): return self.check_arithmetic(node)

    def check_arithmetic(self, node):
        if len(node.children) == 2: # Binario
            left_type = self.check_node(node.children[0])
            right_type = self.check_node(node.children[1])

            if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
                return "TYPE_ERROR" # Propagar error de hijos

            if left_type != "int" or right_type != "int":
                node.type = "TYPE_ERROR" # Error en este nodo
                return "TYPE_ERROR"
        else: # Unario
            child_type = self.check_node(node.children[0])

            if child_type == "TYPE_ERROR":
                return "TYPE_ERROR" # Propagar error de hijo

            if child_type != "int":
                node.type = "TYPE_ERROR" # Error en este nodo
                return "TYPE_ERROR"
    
        node.type = "int"
        return "int"

    def check_equal(self, node): return self.check_comparison(node)
    def check_notequal(self, node): return self.check_comparison(node)
    def check_less(self, node): return self.check_comparison_int(node)
    def check_greater(self, node): return self.check_comparison_int(node)
    def check_leq(self, node): return self.check_comparison_int(node)
    def check_geq(self, node): return self.check_comparison_int(node)
    
    def check_comparison(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
        if left_type != right_type:
            node.type = "TYPE_ERROR" # Marcar el nodo
            return "TYPE_ERROR"      # Propagar el error
        node.type = "bool"
        return "bool"
        
    def check_comparison_int(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
    
    # --- LÓGICA CORREGIDA ---
    # Si alguno de los hijos ya es un error, simplemente propágalo.
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"

    # Si los hijos están bien pero los tipos son incorrectos para esta operación,
    # entonces ESTE nodo es la fuente del error.
        if left_type != "int" or right_type != "int":
            node.type = "TYPE_ERROR" # Marcar este nodo como la fuente
            return "TYPE_ERROR"

        node.type = "bool"
        return "bool"
    
    def check_and(self, node): return self.check_logical(node)
    def check_or(self, node): return self.check_logical(node)

          
    def check_logical(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
    
        # 1. Comprobar si el error viene de abajo
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"
        
        # 2. Comprobar si ESTE nodo causa un nuevo error
        if left_type != "bool" or right_type != "bool":
            node.type = "TYPE_ERROR"
            return "TYPE_ERROR"
        
        node.type = "bool"
        return "bool"

    

    def check_not(self, node):
        child_type = self.check_node(node.children[0])
        if child_type != "bool":
        # ¡NO generes el error final aquí!
        # Simplemente marca este nodo como la fuente del problema
        # y propaga la señal de error hacia arriba.
            node.type = "TYPE_ERROR"
            return "TYPE_ERROR" # ¡No llames a self.add_error()!
        
        node.type = "bool"
        return "bool"

    def check_if(self, node):
        for guard_clause in node.children:
            # Cada hijo es un nodo Guard
            cond_node = guard_clause.children[0]
            body_node = guard_clause.children[1]
            
            cond_type = self.check_node(cond_node)
            if cond_type != "bool":
                node.type = "TYPE_ERROR" # Marcar el nodo
                return "TYPE_ERROR"      # Propagar el error
            
            self.check_node(body_node)
        return None

    def check_while(self, node):
        # Similar a if, pero con un solo hijo 'Then'
        then_node = node.children[0]
        cond_node = then_node.children[0]
        body_node = then_node.children[1]

        cond_type = self.check_node(cond_node)
        if cond_type != "bool":
            node.type = "TYPE_ERROR" # Marcar el nodo
            return "TYPE_ERROR"      # Propagar el error
        
        self.check_node(body_node)
        return None
    
    def _count_comma_elements(self, node):
        # Esta es una función auxiliar para contar recursivamente
        if not isinstance(node, Comma):
            # Si no es una coma, es 1 elemento (e.g., un Literal)
            return 1
        
        # Si es una coma, suma los elementos de la izquierda y la derecha
        return self._count_comma_elements(node.children[0]) + self._count_comma_elements(node.children[1])

    def check_comma(self, node):
        # Chequea los tipos de los hijos para que tengan tipo asignado
        self.check_node(node.children[0])
        self.check_node(node.children[1])
        
        # Cuenta el número total de elementos en la expresión de comas
        count = self._count_comma_elements(node)
        
        # Asigna el tipo correcto con la longitud calculada
        node.type = f"function with length={count}"
        return node.type

          
    def check_readfunction(self, node): 
        func_node = node.children[0]
        arg_node = node.children[1]

        func_type = self.check_node(func_node)
        if func_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        if not (isinstance(func_type, str) and func_type.startswith("function[..")):
            node.type = "TYPE_ERROR" # Marcar y propagar
            return "TYPE_ERROR"
    
        arg_type = self.check_node(arg_node)
    
        if arg_type != "int":
        # ¡La corrección! En lugar de llamar a add_error:
            node.type = "TYPE_ERROR" # Marcar el nodo ReadFunction como la fuente
            return "TYPE_ERROR"      # Propagar la señal de error
    
        node.type = "int"
        return "int"
    

    def check_app(self, node):
        func_node = node.children[0]
        arg_node = node.children[1]

    # Verificamos primero el nodo de la función.
        func_type = self.check_node(func_node)

    # Si la función no está declarada, propagamos el error.
        if func_type == "TYPE_ERROR":
            return "TYPE_ERROR"

    # Verificamos que la variable sea realmente una función.
        if not (isinstance(func_type, str) and "function" in func_type):
            return self.add_error(f"Intento de llamar a un tipo no función ({func_type})", func_node)
    
        node.__class__ = WriteFunction
    # Verificamos los argumentos.
        self.check_node(arg_node)
    
    # --- LA CORRECCIÓN CLAVE ---
    # El tipo del nodo App no es 'int', es el tipo de la función misma.
    # Esto permite que operaciones encadenadas como f(...).i funcionen.
        node.type = func_type
        return func_type
    
    def _transform_plus_to_concat_in_print(self, node):
        """
        Recorre un subárbol (post-orden) y transforma los nodos 'Plus'
        con hijos 'int' en 'Concat'.
        """
        for child in node.children:
            self._transform_plus_to_concat_in_print(child)
        
        if isinstance(node, Plus):
            # Los hijos ya han sido procesados y tienen su tipo asignado
            left_type = node.children[0].type
            right_type = node.children[1].type
            
            if left_type == 'int' and right_type == 'int':
                node.__class__ = Concat
                node.type = "String"

    def check_print(self, node):
        expr_node = node.children[0]

        # 1. Chequeamos los tipos de la expresión normalmente.
        #    Esto decora todo el subárbol con sus tipos (p.ej. Plus -> int)
        expr_type = self.check_node(expr_node)
        if expr_type == "TYPE_ERROR":
            return expr_type # Propagar el error

        # 2. Aplicamos la regla especial de transformación para 'print'.
        self._transform_plus_to_concat_in_print(expr_node)

        # 3. El tipo del nodo 'print' es el tipo final de la expresión.
        #    Si hubo una transformación, el tipo de expr_node ahora es String.
        node.type = expr_node.type
        return node.type

    def check_skip(self, node):
        return None
    
    def check_sequencing(self, node):
        for child in node.children:
            self.check_node(child)
        return None
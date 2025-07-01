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
            # Si tenemos el nodo y su ubicación, la agregamos al mensaje
            if node and node.lineno is not None and node.col_offset is not None:
                # Formateamos el mensaje para que coincida con lo que quieres
                # Ejemplo: "Variable 'g' not declared" -> "Variable 'g' not declared at line 4, column 10"
                full_message = f"Variable not declared at line {node.lineno} and column {node.col_offset}"
                self.errors.append(full_message)
            else:
                self.errors.append(message)
        return "TYPE_ERROR"

    def check_node(self, node):
        class_name = type(node).__name__
        if class_name == "ReadFunction":
            method_name = "check_readfunction"
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

    def check_asig(self, node):
        ident_node = node.children[0]
        expr_node = node.children[1]

        var_type = self.current_table.lookup(ident_node.name)
        if var_type is None:
            return self.add_error(f"Variable '{ident_node.name}' not declared", ident_node)

        expr_type = self.check_node(expr_node)

        if expr_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        # Comprobación especial para asignación de funciones
        is_var_func = var_type.startswith("function[..")
        is_expr_func = isinstance(expr_type, str) and expr_type.startswith("function with length=")

        if is_var_func and is_expr_func:
            # Extraer el tamaño máximo de la declaración de la variable
            match_var = re.search(r'\[\.\.(\d+)\]', var_type)
            var_max_size = int(match_var.group(1)) if match_var else -1
            
            # Extraer la longitud de la expresión
            match_expr = re.search(r'length=(\d+)', expr_type)
            expr_len = int(match_expr.group(1)) if match_expr else -1

            # if expr_len > var_max_size:
            #      return self.add_error(f"Intento de asignar una función de longitud {expr_len} a la variable '{ident_node.name}' que tiene un tamaño máximo de {var_max_size}")
        
        # Comprobación de tipos normal para otros casos
        elif var_type != expr_type:
            return self.add_error(f"Tipo incompatible en asignación. Variable '{ident_node.name}' es de tipo {var_type} pero se le asigna {expr_type}")

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
        return self.add_error(f"El operador '+' no se puede aplicar a los tipos {left_type} y {right_type}")
    
    def check_minus(self, node): return self.check_arithmetic(node)
    def check_mult(self, node): return self.check_arithmetic(node)

    def check_arithmetic(self, node):
        if len(node.children) == 2: # Binario
            left_type = self.check_node(node.children[0])
            right_type = self.check_node(node.children[1])
            if left_type != "int" or right_type != "int":
                return self.add_error(f"Operación aritmética requiere operandos enteros, no {left_type} y {right_type}")
        else: # Unario
            child_type = self.check_node(node.children[0])
            if child_type != "int":
                return self.add_error("Operador unario requiere operando entero")
        
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
            return self.add_error(f"Comparación entre tipos incompatibles: {left_type} y {right_type}")
        node.type = "bool"
        return "bool"
        
    def check_comparison_int(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
        if left_type != "int" or right_type != "int":
            return self.add_error(f"Comparación requiere operandos enteros, no {left_type} y {right_type}")
        node.type = "bool"
        return "bool"
    
    def check_and(self, node): return self.check_logical(node)
    def check_or(self, node): return self.check_logical(node)

    def check_logical(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
        if left_type != "bool" or right_type != "bool":
            return self.add_error(f"Operación lógica requiere operandos booleanos")
        node.type = "bool"
        return "bool"

    def check_not(self, node):
        child_type = self.check_node(node.children[0])
        if child_type != "bool":
            return self.add_error("Operador 'not' requiere operando booleano")
        node.type = "bool"
        return "bool"

    def check_if(self, node):
        for guard_clause in node.children:
            # Cada hijo es un nodo Guard
            cond_node = guard_clause.children[0]
            body_node = guard_clause.children[1]
            
            cond_type = self.check_node(cond_node)
            if cond_type != "bool":
                return self.add_error("La condición de un 'if' debe ser booleana")
            
            self.check_node(body_node)
        return None

    def check_while(self, node):
        # Similar a if, pero con un solo hijo 'Then'
        then_node = node.children[0]
        cond_node = then_node.children[0]
        body_node = then_node.children[1]

        cond_type = self.check_node(cond_node)
        if cond_type != "bool":
            return self.add_error("La condición de un 'while' debe ser booleana")
        
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
        if not (isinstance(func_type, str) and func_type.startswith("function[..")):
            return self.add_error(f"Intento de aplicar '.' a un tipo no función ({func_type})")
        
        # Agrega esta validación para el argumento del acceso
        arg_type = self.check_node(arg_node)
        if arg_type != "int":
            return self.add_error("El índice para el acceso a una función debe ser un entero.")
        
        node.type = "int" # La aplicación de función siempre retorna int en este lenguaje
        return "int"

    def check_print(self, node):
        expr_type = self.check_node(node.children[0])
        node.type = expr_type
        return expr_type

    def check_skip(self, node):
        return None
    
    def check_sequencing(self, node):
        for child in node.children:
            self.check_node(child)
        return None
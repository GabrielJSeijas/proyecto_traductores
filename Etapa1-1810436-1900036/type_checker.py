import re
from ast_nodes import *
from symbol_table import SymbolTable

# TypeChecker es una clase que recorre el AST y verifica los tipos de las expresiones.
# Utiliza una tabla de símbolos para verificar declaraciones y asignaciones.
# Si encuentra un error de tipo, lo registra y devuelve un mensaje de error.
class TypeChecker:
    def __init__(self):
        self.errors = []
        self.current_table = SymbolTable()

    def check_program(self, ast_node):
        if isinstance(ast_node, ASTNode):
            self.check_node(ast_node)
        return self.errors[:1]  # Solo devolvemos el primer error encontrado, si hay alguno.

    def add_error(self, message, node=None):
        if not self.errors:
        # El que llama (como check_asig) 
            self.errors.append(message)
        return "TYPE_ERROR"

          
    def _find_error_node(self, start_node):
        """Busca recursivamente el primer nodo marcado con type='TYPE_ERROR'."""
        if getattr(start_node, 'type', None) == "TYPE_ERROR":
            return start_node
        
        #Usamos el getattr es para evitar errores en nodos sin 'children'
        for child in getattr(start_node, 'children', []):
            found_node = self._find_error_node(child)
            if found_node:
                return found_node
        return None

    def _is_integer_list(self, node):
        """
        Función auxiliar recursiva.
        Verifica que todos los elementos de una expresión de comas sean 'int'.
        Devuelve (True, None) si es válido.
        Devuelve (False, offending_node) si no es válido.
        """
        # Caso base: el nodo no es una Coma, es un elemento final.
        if not isinstance(node, Comma):
            # Chequeamos el tipo de este nodo hoja.
            node_type = self.check_node(node)
            if node_type != "int":
                # Si no es un entero, devolvemos este nodo como el culpable.
                return (False, node)
            return (True, None)
        
        left_child = node.children[0]
        right_child = node.children[1]

        # Verificamos la rama izquierda. Si falla, el error está "más profundo" en la expresión, por lo que propagamos el error que nos den.
        is_left_valid, offending_node_left = self._is_integer_list(left_child)
        if not is_left_valid:
            return (False, offending_node_left)
        
        # Verificamos la rama derecha.
        is_right_valid, offending_node_right = self._is_integer_list(right_child)
        if not is_right_valid:
            return (False, node) # Devolvemos LA COMA ACTUAL, no el hijo.
        return (True, None)

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
        # La ubicación (línea/columna) es la del nodo 'Declare',
        # que corresponde al inicio de la declaración (ej: 'int').
            lineno = node.lineno
            col_offset = node.col_offset
        
            # Declarar la variable en la tabla de símbolos
            previous_declaration = self.current_table.declare(var_name, var_type, lineno, col_offset)
        
            # Si `previous_declaration` no es None, significa que la variable ya existía.
            if previous_declaration:
                # `previous_declaration` es la tupla (type, lineno, col) que guardamos.
                original_lineno = previous_declaration[1]
            
                # Construimos el mensaje de error apuntando a la línea ORIGINAL.
                error_message = f"Variable {var_name} is already declared in the block at line {original_lineno}"
                self.add_error(error_message)
                return # Detenemos el proceso para esta línea de declaración.
    
    def check_writefunction(self, node):
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

        # Obtener el tipo de la variable (lado izquierdo)
        var_type = self.current_table.lookup(ident_node.name)
        if var_type is None:
            error_message = f"Variable {ident_node.name} not declared at line {ident_node.lineno} and column {ident_node.col_offset}"
            return self.add_error(error_message, ident_node)

        # Chequear el tipo de la expresión (lado derecho)
        expr_type = self.check_node(expr_node)

        # Si expr_type es "TYPE_ERROR", significa que hubo un error en la expresión.
        if expr_type == "TYPE_ERROR":
            node.type = "TYPE_ERROR" # Marcar el nodo de asignación como erróneo
            return "TYPE_ERROR"

        #A partir de aquí, sabemos que expr_type es un tipo válido, no "TYPE_ERROR"

        # Comprobamos si los tipos coinciden.
        if var_type == expr_type:
            ident_node.type = var_type
            node.type = var_type
            return var_type

        # CHEQUEOS ESPECÍFICOS:
        is_var_function = isinstance(var_type, str) and var_type.startswith("function[..")
        is_expr_a_list = isinstance(expr_type, str) and expr_type.startswith("function with length=")

        # Asignando una llamada de función a una variable no-función
      
        if isinstance(expr_node, WriteFunction) and not is_var_function:
            variable_name = ident_node.name
            error_line = ident_node.lineno
            error_col = ident_node.col_offset
            error_message = f"Variable {variable_name} is expected to be a function at line {error_line} and column {error_col}"
            node.type = "TYPE_ERROR"
            return self.add_error(error_message)

        # Asignando una lista a una función (compara longitudes)
        if is_var_function and is_expr_a_list:
            match_var = re.search(r'function\[\.\.(\d+)\]', var_type)
            match_expr = re.search(r'function with length=(\d+)', expr_type)

            if match_var and match_expr:
                expected_len = int(match_var.group(1)) + 1
                actual_len = int(match_expr.group(1))

                if expected_len != actual_len:
                    error_line = node.lineno
                    error_col = node.col_offset
                    
                    error_message = f"It is expected a list of length {expected_len} at line {error_line} and column {error_col + 1}"
                    node.type = "TYPE_ERROR"
                    return self.add_error(error_message)
                else:
                    # Si las longitudes coinciden, la asignación es válida.
                    ident_node.type = var_type
                    node.type = var_type
                    return var_type

        #Asignando un entero a una función
        
        if is_var_function and isinstance(expr_node, Literal) and expr_type == "int":
            ident_node.type = var_type
            node.type = var_type
            return var_type

        # ERROR GENÉRICO Si ninguna de las reglas anteriores se cumplió.
        
        variable_name = ident_node.name
        error_line = ident_node.lineno
        error_col = ident_node.col_offset
        error_message = f"Type error. Variable {variable_name} has different type than expression at line {error_line} and column {error_col}"
        node.type = "TYPE_ERROR"
        return self.add_error(error_message)
    

    def _count_comma_elements(self, node):
        if isinstance(node, Comma):
            # Una coma une dos sub-expresiones, contamos los elementos de ambas.
            return self._count_comma_elements(node.children[0]) + self._count_comma_elements(node.children[1])
        return 1 # Cualquier otro nodo es un solo elemento.

    def check_comma(self, node):
        # Validar que la lista esté compuesta solo por enteros.
        is_valid, offending_node = self._is_integer_list(node)

        if not is_valid:
            # Si la lista no es de enteros, generamos el error específico.
            error_message = f"There is no integer list at line {offending_node.lineno} and column {offending_node.col_offset}"
            node.type = "TYPE_ERROR"
            return self.add_error(error_message, offending_node)

        # Si es válida, contamos los elementos y asignamos el tipo como antes.
        count = self._count_comma_elements(node)
        
        node.type = f"function with length={count}"
        return node.type
    
    def check_twopoints(self, node):
        # Asume que ':' combina dos elementos en una "función" de longitud 2.
        self.check_node(node.children[0])
        self.check_node(node.children[1])
        node.type = "function with length=2" 
        return node.type

    def check_ident(self, node):
        var_type = self.current_table.lookup(node.name)
        if var_type is None:
            #Construir el mensaje de error con la ubicación del nodo Ident
            error_message = f"Variable not declared at line {node.lineno} and column {node.col_offset}"
        
            #Marcar el nodo como error para que _find_error_node pueda encontrarlo si es necesario
            node.type = "TYPE_ERROR"

            #Añadir el mensaje formateado y devolver la señal de error
            return self.add_error(error_message, node)
        
        node.type = var_type
        return var_type

    def check_literal(self, node):
        return node.type

    def check_plus(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])

        # Propagar errores existentes de los hijos
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        #Si los hijos están bien, verificamos las operaciones válidas:
    
        # Caso 1: Suma de enteros
        if left_type == "int" and right_type == "int":
            node.type = "int"
            return "int"
    
        # Caso 2: Concatenación de strings
        valid_concat_types = ["String", "int", "bool"]
        if (left_type == "String" and right_type in valid_concat_types) or \
            (right_type == "String" and left_type in valid_concat_types):
            node.__class__ = Concat
            node.type = "String"
            return "String"

        # Si ninguna operación es válida, ESTE nodo es la fuente del error
        node.type = "TYPE_ERROR"
        return "TYPE_ERROR"
    
    def check_minus(self, node): return self.check_arithmetic(node)
    def check_mult(self, node): return self.check_arithmetic(node)

    def check_arithmetic(self, node):
        if len(node.children) == 2: # Operador Binario
            left_type = self.check_node(node.children[0])
            right_type = self.check_node(node.children[1])

            if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
                return "TYPE_ERROR" # Propagar error de hijos

            if left_type != "int" or right_type != "int":
                node.type = "TYPE_ERROR" # Error en este nodo
                return "TYPE_ERROR"
        else: # Operador Unario
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

        #Propagamos errores existentes
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        #Generamos un nuevo error si los tipos no coinciden
        if left_type != right_type:
            node.type = "TYPE_ERROR" 
            return "TYPE_ERROR"
    
        #imprimimos todo está correcto
        node.type = "bool"
        return "bool"
    
    # Comprobación específica para comparaciones con enteros
    def check_comparison_int(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
    
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        if left_type != "int" or right_type != "int":
            node.type = "TYPE_ERROR" 
            return "TYPE_ERROR"

        node.type = "bool"
        return "bool"
    
    def check_and(self, node): return self.check_logical(node)
    def check_or(self, node): return self.check_logical(node)

    # Comprobación lógica para 'and' y 'or'
    def check_logical(self, node):
        left_type = self.check_node(node.children[0])
        right_type = self.check_node(node.children[1])
    
        #Comprobamos si el error viene de abajo
        if left_type == "TYPE_ERROR" or right_type == "TYPE_ERROR":
            return "TYPE_ERROR"
        
        #Comprobamos si este nodo causa un nuevo error
        if left_type != "bool" or right_type != "bool":
            node.type = "TYPE_ERROR"
            return "TYPE_ERROR"
        
        node.type = "bool"
        return "bool"

    

    def check_not(self, node):
        child_type = self.check_node(node.children[0])
        if child_type != "bool":
            node.type = "TYPE_ERROR"
            return "TYPE_ERROR" 
        
        node.type = "bool"
        return "bool"

    def check_if(self, node):
        for guard_clause in node.children:
            # Cada hijo es un nodo Guard
            cond_node = guard_clause.children[0]
            body_node = guard_clause.children[1]
            
            cond_type = self.check_node(cond_node)
            if cond_type != "bool":
                # Si la guarda no es booleana, este es el error.
                # Propagamos el error si ya venía de la expresión (ej: variable not declared)
                if cond_type == "TYPE_ERROR":
                    return "TYPE_ERROR"

                # Si la expresión es válida pero de tipo incorrecto (ej: int), creamos el error aquí.
                error_message = f"No boolean guard at line {guard_clause.lineno} and column {guard_clause.col_offset}"
                node.type = "TYPE_ERROR" # Marcar el nodo 'If' como erróneo
                # Añadimos el error y retornamos la señal para detener el chequeo.
                return self.add_error(error_message, cond_node)     # Propagamos el error
            
            self.check_node(body_node)
        return None

    # Función auxiliar para validar los argumentos de las funciones de modificación
    # (como WriteFunction o App) que esperan pares clave:valor.
    def _check_function_modification_args(self, arg_node):
        """
        Función auxiliar recursiva para validar los argumentos.
        Devuelve None si es válido, o el NODO que causa el error en caso contrario.
     """
        if isinstance(arg_node, TwoPoints):
            key_node = arg_node.children[0]
            val_node = arg_node.children[1]

            key_type = self.check_node(key_node)
            val_type = self.check_node(val_node)

        # Si la clave no es un entero, devolvemos el nodo de la clave.
            if key_type != "int":
                if key_type != "TYPE_ERROR": key_node.type = "TYPE_ERROR"
                return key_node # Devolver el nodo erróneo

        # Si el valor no es un entero, devolvemos el nodo del valor.
            if val_type != "int":
                if val_type != "TYPE_ERROR": val_node.type = "TYPE_ERROR"
                return val_node #Devolver el nodo erróneo
        
        # Si todo está bien para este par, no hay error.
            return None

        elif isinstance(arg_node, Comma):
        # Si es una coma, chequear ambas ramas y devolver el primer error que se encuentre.
            left_error_node = self._check_function_modification_args(arg_node.children[0])
            if left_error_node:
                return left_error_node
        
            right_error_node = self._check_function_modification_args(arg_node.children[1])
            if right_error_node:
                return right_error_node
            
            return None

        else:
            # Cualquier otra cosa es un error estructural (p.ej. A(3) en lugar de A(clave:valor))
            self.check_node(arg_node) # Chequeamos para propagar errores internos.
            arg_node.type = "TYPE_ERROR"
            return arg_node # Devolvemos el nodo del argumento completo
    
    # Chequeo específico para nodos 'While'
    def check_while(self, node):
        # Similar a if, pero con un solo hijo 'Then'
        then_node = node.children[0]
        cond_node = then_node.children[0]
        body_node = then_node.children[1]

        cond_type = self.check_node(cond_node)
        
        if cond_type != "bool":
            if cond_type == "TYPE_ERROR":
                return "TYPE_ERROR"

            error_message = f"No boolean guard at line {then_node.lineno} and column {then_node.col_offset}"
            node.type = "TYPE_ERROR"
            return self.add_error(error_message, cond_node)

        self.check_node(body_node)
        return None
    
    # Esta es una función auxiliar para contar recursivamente
    def _count_comma_elements(self, node):
        
        if not isinstance(node, Comma):
            # Si no es una coma, es 1 elemento (e.g., un Literal)
            return 1
        
        # Si es una coma, suma los elementos de la izquierda y la derecha
        return self._count_comma_elements(node.children[0]) + self._count_comma_elements(node.children[1])
          
    def check_readfunction(self, node): 
        func_node = node.children[0]
        arg_node = node.children[1]

        func_type = self.check_node(func_node)
    
        # Propagamos errores que vengan de la "función" (ej: variable no declarada)
        if func_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        #El chequeo específico de indexación
        if not (isinstance(func_type, str) and func_type.startswith("function[..")):
            #Construimos el mensaje de error 
            var_name = func_node.name if isinstance(func_node, Ident) else 'expression'
            error_message = f"Error. {var_name} is not indexable at line {func_node.lineno} and column {func_node.col_offset}"
        
            #Marcar el nodo como la fuente del error
            node.type = "TYPE_ERROR" 

            #Añadir el error y propagarlo
            return self.add_error(error_message, node)

        # El resto de la lógica para una indexación válida
        arg_type = self.check_node(arg_node)

        if arg_type == "TYPE_ERROR":
            return "TYPE_ERROR" # Propagar error del argumento

        if arg_type != "int":
            # Este es un error de tipo en el índice, el nodo ReadFunction es la fuente
            error_message = f"Type error in line {node.lineno} and column {node.col_offset}"
            node.type = "TYPE_ERROR"
            return self.add_error(error_message, node)
    
        node.type = "int" # La indexación de una función siempre devuelve un int
        return "int"
    

    # Chequeo específico para nodos 'App' (llamadas a funciones)
    # Esta función verifica que el nodo sea una llamada a una función válida.
    # Si la función no es válida, devuelve un error.
    def check_app(self, node):
        func_node = node.children[0]
        arg_node = node.children[1]

        func_type = self.check_node(func_node)

        if func_type == "TYPE_ERROR":
            return "TYPE_ERROR"

        if not (isinstance(func_type, str) and "function" in func_type):
            error_message = f"The function modification operator is use in not function variable at line {func_node.lineno} and column {func_node.col_offset}"
            node.type = "TYPE_ERROR"
            return self.add_error(error_message, node)
    
        # Llamamos a la función auxiliar y guardamos el resultado
        error_node = self._check_function_modification_args(arg_node)

        # Si nos devolvió un nodo, significa que hubo un error
        if error_node:
            # Usamos la ubicación del nodo erróneo para el mensaje
            error_message = f"Expected expression of type int at line {error_node.lineno} and column {error_node.col_offset}"
            node.type = "TYPE_ERROR" 
            return self.add_error(error_message)
    
        # Si todo está bien, continuamos como antes
        node.__class__ = WriteFunction
        self.check_node(arg_node)
        node.type = func_type
        return func_type
    
    # Esta función transforma los nodos 'Plus' con hijos 'int' en 'Concat'
    # cuando se encuentran dentro de un nodo 'Print'.
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

        # Chequeamos los tipos de la expresión normalmente.
        expr_type = self.check_node(expr_node)
        if expr_type == "TYPE_ERROR":
            return expr_type # Propagar el error

        #Aplicamos la regla especial de transformación para 'print'.
        self._transform_plus_to_concat_in_print(expr_node)

        # El tipo del nodo 'print' es el tipo final de la expresión.
        # Si hubo una transformación, el tipo de expr_node ahora es String.
        node.type = expr_node.type
        return node.type

    # Estas funciones son necesarias para que el TypeChecker pueda recorrer el AST completo sin errores.
    def check_skip(self, node):
        return None
    # Esta función se usa para nodos que no tienen un chequeo específico, como 'Sequencing'.
    # Simplemente recorre los hijos y aplica el chequeo genérico.
    def check_sequencing(self, node):
        for child in node.children:
            self.check_node(child)
        return None
from ast_nodes import *
from symbol_table import SymbolTable

class TypeChecker:
    def __init__(self):
        self.errors = []
        self.current_table = SymbolTable()
        self.global_table = self.current_table  # Referencia a la tabla global

    def check_program(self, ast_node):
        """Punto de entrada principal para la verificación de tipos"""
        if isinstance(ast_node, Block):
            self.check_block(ast_node)
        return self.errors

    def add_error(self, message, node=None):
        """Agrega un error a la lista de errores"""
        self.errors.append(message)
        return "TYPE_ERROR"  # Valor especial para propagar errores

    print
    def check_block(self, block_node):

        """Verifica un bloque de código"""
        # Guardar la tabla actual
        outer_table = self.current_table
        
        print(f"Tabla actual después de declaraciones: {self.current_table.symbols}")
        # Crear un nuevo ámbito
        self.current_table = self.current_table.enter_scope()
        block_node.symbol_table = self.current_table  # Enlazar tabla al nodo

        # Procesar declaraciones primero
        for child in block_node.children:
            if isinstance(child, Declare):
                self.check_declaration(child)
        
        # Luego procesar sentencias
        for child in block_node.children:
            if not isinstance(child, Declare):
                self.check_statement(child)
        
        # Restaurar la tabla anterior
        self.current_table = self.current_table.exit_scope()

    def process_declaration(self, declare_node):
     """Solo registra las variables en la tabla, sin verificación"""
     if isinstance(declare_node, Declare) and declare_node.children:
        decl_str = declare_node.children[0]
        if isinstance(decl_str, str) and ":" in decl_str:
            vars_part, type_part = decl_str.split(":", 1)
            var_names = [name.strip() for name in vars_part.split(",")]
            var_type = type_part.strip()
            
            for var_name in var_names:
                if not self.current_table.declare(var_name, var_type):
                    self.add_error(f"Redeclaración de variable '{var_name}'")

    
    def check_declaration(self, declare_node):
        """Verifica una declaración de variable/función"""
        if isinstance(declare_node, Declare) and declare_node.children:
            decl_str = declare_node.children[0]  # El string de declaración está en el primer hijo
            if isinstance(decl_str, str) and ":" in decl_str:
                vars_part, type_part = decl_str.split(":", 1)
                var_names = [name.strip() for name in vars_part.split(",")]
                var_type = type_part.strip()
                
                for var_name in var_names:
                    if not self.current_table.declare(var_name, var_type):
                        self.add_error(f"Error: Redeclaración de variable '{var_name}' en el mismo ámbito")

    def check_statement(self, stmt_node):
        """Verifica una sentencia"""
        if isinstance(stmt_node, Asig):
            self.check_assignment(stmt_node)
        elif isinstance(stmt_node, Print):
            self.check_print(stmt_node)
        elif isinstance(stmt_node, If):
            self.check_if(stmt_node)
        elif isinstance(stmt_node, While):
            self.check_while(stmt_node)
        elif isinstance(stmt_node, Block):
            self.check_block(stmt_node)
        # Otros tipos de sentencias pueden agregarse aquí

    def check_assignment(self, asig_node):
        """Verifica una asignación"""
        ident_node = asig_node.children[0]
        expr_node = asig_node.children[1]
    
        var_type = self.current_table.lookup(ident_node.name)
        if var_type is None:
            return self.add_error(f"Error: Variable '{ident_node.name}' no declarada")
    
        expr_type = self.check_expression(expr_node)
    
        if expr_type == "TYPE_ERROR":
            return "TYPE_ERROR"
        
        if var_type != expr_type:
            if not (var_type.startswith("function[..") and expr_type.startswith("function[..")):
                return self.add_error(f"Error: Tipo incompatible en asignación. Variable '{ident_node.name}' es de tipo {var_type} pero se le asigna {expr_type}")

    # Asignar tipos a los nodos
        ident_node.type = var_type
        expr_node.type = expr_type
        asig_node.type = var_type
    
        return var_type

    def check_expression(self, expr_node):
        """Verifica una expresión y devuelve su tipo"""
        if isinstance(expr_node, Ident):
            return self.check_identifier(expr_node)
        elif isinstance(expr_node, Literal):
            return self.check_literal(expr_node)
        elif isinstance(expr_node, (Plus, Minus, Mult)):
            return self.check_arithmetic_op(expr_node)
        elif isinstance(expr_node, (Equal, NotEqual, Less, Greater, Leq, Geq)):
            return self.check_comparison_op(expr_node)
        elif isinstance(expr_node, (And, Or)):
            return self.check_logical_op(expr_node)
        elif isinstance(expr_node, Not):
            return self.check_logical_not(expr_node)
        elif isinstance(expr_node, App):
            return self.check_function_app(expr_node)
        elif isinstance(expr_node, Comma):
            return self.check_comma(expr_node)
        # Otros tipos de expresiones pueden agregarse aquí
        else:
            for child in expr_node.children:
                if isinstance(child, ASTNode):
                    self.check_expression(child)
            return "unknown"  # Tipo por defecto si no se puede determinar

    def check_identifier(self, ident_node):
        var_type = self.current_table.lookup(ident_node.name)
        if var_type is None:
            return self.add_error(f"Variable '{ident_node.name}' no declarada")
    
        # Asignar tipo AL NODO - esto es lo que falta
        ident_node.type = var_type  # Esta línea es crucial
        return var_type

    def check_literal(self, literal_node):
        """Verifica un literal y devuelve su tipo"""
        if isinstance(literal_node.value, bool):
            literal_node.type = "bool"
            return "bool"
        elif isinstance(literal_node.value, int):
            literal_node.type = "int"
            return "int"
        else:
            literal_node.type = "unknown"
            return "unknown"

    def check_arithmetic_op(self, op_node):
        """Verifica una operación aritmética (+, -, *)"""
        left_type = self.check_expression(op_node.children[0])
        right_type = self.check_expression(op_node.children[1])
        
        if "TYPE_ERROR" in [left_type, right_type]:
            return "TYPE_ERROR"
            
        if left_type != "int" or right_type != "int":
            return self.add_error(f"Error: Operación aritmética no válida entre {left_type} y {right_type}")
        
        op_node.type = "int"
        return "int"

    def check_comparison_op(self, op_node):
        """Verifica una operación de comparación (==, <, >, etc.)"""
        left_type = self.check_expression(op_node.children[0])
        right_type = self.check_expression(op_node.children[1])
        
        if "TYPE_ERROR" in [left_type, right_type]:
            return "TYPE_ERROR"
            
        if left_type != right_type:
            return self.add_error(f"Error: Comparación no válida entre {left_type} y {right_type}")
        
        op_node.type = "bool"
        return "bool"

    def check_logical_op(self, op_node):
        """Verifica una operación lógica (and, or)"""
        left_type = self.check_expression(op_node.children[0])
        right_type = self.check_expression(op_node.children[1])
        
        if "TYPE_ERROR" in [left_type, right_type]:
            return "TYPE_ERROR"
            
        if left_type != "bool" or right_type != "bool":
            return self.add_error(f"Error: Operación lógica no válida entre {left_type} y {right_type}")
        
        op_node.type = "bool"
        return "bool"

    def check_logical_not(self, not_node):
        """Verifica una negación lógica (!)"""
        expr_type = self.check_expression(not_node.children[0])
        
        if expr_type == "TYPE_ERROR":
            return "TYPE_ERROR"
            
        if expr_type != "bool":
            return self.add_error(f"Error: Negación lógica aplicada a tipo no booleano: {expr_type}")
        
        not_node.type = "bool"
        return "bool"

    def check_function_app(self, app_node):
        """Verifica una aplicación de función (x.y)"""
        # Implementación básica - puede necesitar expansión
        ident_type = self.check_expression(app_node.children[0])
        
        if ident_type == "TYPE_ERROR":
            return "TYPE_ERROR"
            
        if not ident_type.startswith("function[.."):
            return self.add_error(f"Error: Intento de aplicar '.' a tipo no función: {ident_type}")
        
        app_node.type = "int"  # Asumimos que devuelve entero - ajustar según necesidades
        return "int"

    def check_comma(self, comma_node):
        """Verifica una expresión con coma (x, y)"""
        left_type = self.check_expression(comma_node.children[0])
        right_type = self.check_expression(comma_node.children[1])
    
        if "TYPE_ERROR" in [left_type, right_type]:
            return "TYPE_ERROR"
        
        comma_node.type = f"function[..2]"
        return comma_node.type

    def check_if(self, if_node):
        """Verifica una sentencia if"""
        # Verificar todas las condiciones de los guardias
        for guard in if_node.children:
            if isinstance(guard, Guard):
                self.check_guard(guard)
            elif isinstance(guard, Then):
                self.check_condition(guard.children[0])

    def check_guard(self, guard_node):
        """Verifica un guardia de if"""
        condition = guard_node.children[0]
        self.check_condition(condition)

    def check_condition(self, condition_node):
        """Verifica una condición"""
        cond_type = self.check_expression(condition_node)
        
        if cond_type == "TYPE_ERROR":
            return "TYPE_ERROR"
            
        if cond_type != "bool":
            return self.add_error(f"Error: La condición debe ser booleana, no {cond_type}")
        
        return "bool"

    def check_while(self, while_node):
        """Verifica una sentencia while"""
        condition = while_node.children[0].children[0]  # Then -> condición
        self.check_condition(condition)

    def check_print(self, print_node):
        """Verifica una sentencia print"""
        expr_type = self.check_expression(print_node.children[0])
        
        if expr_type == "TYPE_ERROR":
            return "TYPE_ERROR"
        
        print_node.type = expr_type
        return expr_type
class ASTNode:
    def __init__(self):
        self.children = []
        self.type = None  # Tipo del nodo (int, bool, function[..n], etc.)
        self.symbol_table = None  # Para bloques, guarda su tabla de símbolos

    def add_child(self, node):
        self.children.append(node)

    def check_types(self, symbol_table):
        """Método base para verificación de tipos"""
        for child in self.children:
            if isinstance(child, ASTNode):
                child.check_types(symbol_table)
        return self.type

    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        node_name = self.__class__.__name__
        type_info = f" | type: {self.type}" if hasattr(self, 'type') and self.type is not None else ""
        
        # Caso especial para Comma
        if isinstance(self, Comma):
            node_name = "Comma"
            type_info = " | type: function with length=2"
        
        result = prefix + f"{node_name}{type_info}\n"
        
        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
            else:
                result += prefix + "-" + str(child) + "\n"
        return result


class Block(ASTNode):
    def check_types(self, symbol_table):
        # Crear nuevo ámbito
        new_scope = symbol_table.enter_scope()
        self.symbol_table = new_scope
        
        # Procesar declaraciones primero
        for child in self.children:
            if isinstance(child, Declare):
                child.check_types(new_scope)
        
        # Procesar sentencias
        for child in self.children:
            if not isinstance(child, Declare):
                child.check_types(new_scope)
        
        # Salir del ámbito
        symbol_table.exit_scope()
        return None 
    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        result = prefix + "Block\n"
        
        # Mostrar tabla de símbolos con todas las variables
        if hasattr(self, 'symbol_table') and self.symbol_table:
            result += prefix + "-Symbols Table\n"
            for name, var_type in self.symbol_table.symbols.items():
                result += prefix + f"--variable: {name} | type: {var_type}\n"
        
        # Recorrer hijos
        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
            else:
                result += prefix + "-" + str(child) + "\n"
        return result
    

class Declare(ASTNode):
    def check_types(self, symbol_table):
        if self.children and isinstance(self.children[0], str):
            decl_str = self.children[0]
            if ":" in decl_str:
                vars_part, type_part = decl_str.split(":", 1)
                var_names = [name.strip() for name in vars_part.split(",")]
                var_type = type_part.strip()
                
                for var_name in var_names:
                    if not symbol_table.declare(var_name, var_type):
                        raise ValueError(f"Redeclaración de variable '{var_name}'")
        return None


class Sequencing(ASTNode):
    def check_types(self, symbol_table):
        for child in self.children:
            if isinstance(child, ASTNode):
                child.check_types(symbol_table)
        return None
    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        result = prefix + "Sequencing\n"
        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
            else:
                result += prefix + "-" + str(child) + "\n"
        return result


class Asig(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) >= 2:
            ident = self.children[0]
            expr = self.children[1]
            
            if isinstance(ident, Ident):
                ident.check_types(symbol_table)
                var_type = symbol_table.lookup(ident.name)
                if var_type is None:
                    raise ValueError(f"Variable '{ident.name}' no declarada")
                
                expr_type = expr.check_types(symbol_table)
                
                if var_type != expr_type:
                    if not (var_type.startswith("function[..") and expr_type.startswith("function[..")):
                        raise ValueError(f"Tipo incompatible en asignación. Esperado: {var_type}, Obtenido: {expr_type}")
                
                self.type = var_type
        return self.type


class Ident(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def check_types(self, symbol_table):
        self.type = symbol_table.lookup(self.name)
        if self.type is None:
            raise ValueError(f"Variable '{self.name}' no declarada")
        return self.type

    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        type_info = f" | type: {self.type}" if self.type is not None else ""
        return prefix + f"Ident: {self.name}{type_info}\n"


class Literal(ASTNode):
    def __init__(self, value):
        super().__init__()
        if isinstance(value, str) and value.lower() == 'true':
            self.value = True
            self.type = "bool"
        elif isinstance(value, str) and value.lower() == 'false':
            self.value = False
            self.type = "bool"
        else:
            self.value = value
            self.type = "int" if isinstance(value, int) else "unknown"

    def check_types(self, symbol_table):
        return self.type

    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        val_to_print = str(self.value).lower() if isinstance(self.value, bool) else self.value
        type_info = f" | type: {self.type}" if self.type is not None else ""
        return prefix + f"Literal: {val_to_print}{type_info}\n"


class String(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value
        self.type = "string"

    def check_types(self, symbol_table):
        return self.type

    def __str__(self, level=0):
        prefix = "-" * level if level > 0 else ""
        type_info = f" | type: {self.type}" if self.type is not None else ""
        return prefix + f"String: \"{self.value}\"{type_info}\n"


# Operaciones Aritméticas
class Plus(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Operación '+' requiere operandos enteros")
            
            self.type = "int"
        return self.type


class Minus(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Operación '-' requiere operandos enteros")
            
            self.type = "int"
        elif len(self.children) == 1:  # Negativo unario
            child_type = self.children[0].check_types(symbol_table)
            if child_type != "int":
                raise ValueError("Operación '-' unaria requiere operando entero")
            self.type = "int"
        return self.type


class Mult(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Operación '*' requiere operandos enteros")
            
            self.type = "int"
        return self.type


# Operaciones de Comparación
class Equal(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != right_type:
                raise ValueError(f"Comparación '==' entre tipos incompatibles: {left_type} y {right_type}")
            
            self.type = "bool"
        return self.type


class NotEqual(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != right_type:
                raise ValueError(f"Comparación '<>' entre tipos incompatibles: {left_type} y {right_type}")
            
            self.type = "bool"
        return self.type


class Less(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Comparación '<' requiere operandos enteros")
            
            self.type = "bool"
        return self.type


class Greater(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Comparación '>' requiere operandos enteros")
            
            self.type = "bool"
        return self.type


class Leq(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Comparación '<=' requiere operandos enteros")
            
            self.type = "bool"
        return self.type


class Geq(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Comparación '>=' requiere operandos enteros")
            
            self.type = "bool"
        return self.type


# Operaciones Lógicas
class And(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "bool" or right_type != "bool":
                raise ValueError("Operación 'and' requiere operandos booleanos")
            
            self.type = "bool"
        return self.type


class Or(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "bool" or right_type != "bool":
                raise ValueError("Operación 'or' requiere operandos booleanos")
            
            self.type = "bool"
        return self.type


class Not(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 1:
            child_type = self.children[0].check_types(symbol_table)
            
            if child_type != "bool":
                raise ValueError("Operación 'not' requiere operando booleano")
            
            self.type = "bool"
        return self.type


# Estructuras de Expresión
class Comma(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            self.children[0].check_types(symbol_table)
            self.children[1].check_types(symbol_table)
            self.type = "function[..2]"  # Tipo para listas separadas por coma
        return self.type


class TwoPoints(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            left_type = self.children[0].check_types(symbol_table)
            right_type = self.children[1].check_types(symbol_table)
            
            if left_type != "int" or right_type != "int":
                raise ValueError("Rango ':' requiere operandos enteros")
            
            self.type = "range"
        return self.type


class App(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            ident_type = self.children[0].check_types(symbol_table)
            
            if not ident_type.startswith("function[.."):
                raise ValueError(f"Intento de aplicar '.' a tipo no función: {ident_type}")
            
            self.children[1].check_types(symbol_table)
            self.type = "int"  # Asumimos que devuelve entero
        return self.type


# Función Especial
class WriteFunction(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) == 2:
            self.children[0].check_types(symbol_table)
            self.children[1].check_types(symbol_table)
            self.type = "int"  # Tipo de retorno asumido
        return self.type


# Sentencias
class While(ASTNode):
    def check_types(self, symbol_table):
        if self.children and isinstance(self.children[0], Then):
            then_node = self.children[0]
            # Verificar condición
            cond = then_node.children[0]
            cond_type = cond.check_types(symbol_table)
            if cond_type != "bool":
                raise ValueError("La condición del while debe ser booleana")
            
            # Verificar cuerpo
            body = then_node.children[1]
            body.check_types(symbol_table.enter_scope())
            symbol_table.exit_scope()
        return None


class Then(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) >= 2:
            self.children[0].check_types(symbol_table)  # Condición
            self.children[1].check_types(symbol_table)  # Cuerpo
        return None


class If(ASTNode):
    def check_types(self, symbol_table):
        for child in self.children:
            if isinstance(child, (Guard, Then)):
                # Verificar condición
                cond = child.children[0]
                cond_type = cond.check_types(symbol_table)
                if cond_type != "bool":
                    raise ValueError("La condición del if/guardia debe ser booleana")
                
                # Verificar cuerpo
                body = child.children[1]
                body.check_types(symbol_table.enter_scope())
                symbol_table.exit_scope()
        return None


class Guard(ASTNode):
    def check_types(self, symbol_table):
        if len(self.children) >= 2:
            self.children[0].check_types(symbol_table)  # Condición
            self.children[1].check_types(symbol_table)  # Cuerpo
        return None


class Print(ASTNode):
    def check_types(self, symbol_table):
        if self.children:
            self.type = self.children[0].check_types(symbol_table)
        return self.type


class skip(ASTNode):
    def check_types(self, symbol_table):
        return None  # skip no tiene tipo


class Return(ASTNode):
    def check_types(self, symbol_table):
        if self.children:
            return_type = self.children[0].check_types(symbol_table)
            if return_type != "int":
                raise ValueError("La función debe retornar un entero")
        return "int"  # Asumimos que el retorno es entero por defecto
    
    
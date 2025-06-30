class ASTNode:
    def __init__(self):
        self.children = []
        self.type = None
        self.symbol_table = None
        self.lineno = None
        self.col_offset = None

    def add_child(self, node):
        self.children.append(node)

    def __str__(self, level=0):
        prefix = '-' * level
        node_name = self.__class__.__name__
        
        # Casos especiales
        if isinstance(self, Ident):
            node_name = f"Ident: {self.name}"
        elif isinstance(self, Literal):
            node_name = f"Literal: {self.value}"
        elif isinstance(self, Comma):
            node_name = "Comma"
        
        # Solo mostrar tipo para nodos específicos
        show_type = not isinstance(self, (Sequencing, Asig, Guard, Then, Print))
        type_info = f" | type: {self.type}" if self.type is not None and show_type else ""
        
        result = f"{prefix}{node_name}{type_info}\n"

        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
        
        return result

class Block(ASTNode):
    def __str__(self, level=0):
        prefix = '-' * level
        result = f"{prefix}Block\n"
        
        # Imprimir la tabla de símbolos directamente aquí para controlar el formato.
        if hasattr(self, 'symbol_table') and self.symbol_table and self.symbol_table.symbols:
            result += f"{prefix}-Symbols Table\n"
            for name, type_info in self.symbol_table.symbols.items():
                result += f"{prefix}--variable: {name} | type: {type_info}\n"
        
        # Imprimir los hijos (sentencias)
        for child in self.children:
            result += child.__str__(level + 1)
            
        return result

class Declare(ASTNode):
    # Esta clase es un marcador, no se imprime en el AST final.
    def __str__(self, level=0):
        return ""

class Sequencing(ASTNode):
    def __str__(self, level=0):
        prefix = '-' * level
        result = ""
        
        # Solo mostrar "Sequencing" si no es el nodo raíz
        if level > 0:
            result += f"{prefix}Sequencing\n"
        
        for child in self.children:
            result += child.__str__(level + 1)
        return result

class Asig(ASTNode): pass
class Ident(ASTNode):
    def __init__(self, name, lineno, col_offset):
        super().__init__()
        self.name = name
        self.lineno = lineno
        self.col_offset = col_offset
    def __str__(self, level=0):
        # La representación en string no necesita cambiar
        prefix = '-' * level
        node_name = f"Ident: {self.name}"
        type_info = f" | type: {self.type}" if self.type is not None else ""
        return f"{prefix}{node_name}{type_info}\n"

class Literal(ASTNode):
    def __init__(self, value):
        super().__init__()
        if isinstance(value, str) and value.lower() in ['true', 'false']:
            self.value = value.lower() == 'true'
            self.type = "bool"
        else:
            self.value = value
            self.type = "int" if isinstance(value, int) else "unknown"

class String(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value
        self.type = "string"

# Operaciones
class Plus(ASTNode): pass
class Minus(ASTNode): pass
class Mult(ASTNode): pass
class Equal(ASTNode): pass
class NotEqual(ASTNode): pass
class Less(ASTNode): pass
class Greater(ASTNode): pass
class Leq(ASTNode): pass
class Geq(ASTNode): pass
class And(ASTNode): pass
class Or(ASTNode): pass
class Not(ASTNode): pass
class Comma(ASTNode): pass
class TwoPoints(ASTNode): pass
class App(ASTNode): pass

# Sentencias
class While(ASTNode): pass
class Then(ASTNode): pass # Usado para cuerpos de if/while

class If(ASTNode):
    # La impresión se personaliza para que coincida con el formato Guard/Then
    def __str__(self, level=0):
        prefix = '-' * level
        result = f"{prefix}If\n"
        
        if not self.children:
            return result

        # Imprime un único "Guard" como contenedor
        result += f"{prefix}-Guard\n"
        
        # Cada hijo del nodo If es un nodo Guard que contiene una (condición, cuerpo)
        for guard_node in self.children:
            # Imprime "Then" para esta cláusula
            result += f"{prefix}--Then\n"
            
            # Imprime la condición y el cuerpo de la cláusula
            condition = guard_node.children[0]
            body = guard_node.children[1]
            result += condition.__str__(level + 3)
            result += body.__str__(level + 3)
            
        return result


class Guard(ASTNode):
    # Esta clase es un contenedor para (condición, cuerpo), no se imprime directamente.
    pass

class Print(ASTNode): pass
class skip(ASTNode):
    def __str__(self, level=0):
        return f"{'-' * level}skip\n"
class Return(ASTNode): pass
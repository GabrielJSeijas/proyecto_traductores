class ASTNode:
    def __init__(self, lineno=None, col_offset=None):# Añadimos argumentos opcionales
        super().__init__()
        self.children = []  # Lista de hijos del nodo
        self.type = None    # Tipo del nodo, por defecto None
        self.lineno = lineno # Los guardamos
        self.col_offset = col_offset # Los guardamos

    def add_child(self, node):
        self.children.append(node)

    def __str__(self, level=0):
        prefix = '-' * level
        node_name = self.__class__.__name__
        
        # Casos especiales
        if isinstance(self, Ident):
            node_name = f"Ident: {self.name}"
        elif isinstance(self, Literal):
            node_name = f"Literal: {str(self.value).lower()}"
        elif isinstance(self, String):
            # Suponiendo que self.value contiene las comillas del lexer '"First: "'
            node_name = f"String: {self.value}"
        elif isinstance(self, Comma):
            node_name = "Comma"
        
        #Solo mostrar type para nodos específicos
        show_type = not isinstance(self, (Sequencing, Asig, Guard, Then, Print,String,TwoPoints))
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
        
        # Imprimimos la tabla de símbolos directamente aquí para controlar el formato.
        if hasattr(self, 'symbol_table') and self.symbol_table:
            result += f"{prefix}-Symbols Table\n"
            for name, symbol_info in self.symbol_table.symbols.items():
                # Extraemos solo el tipo, que es el primer elemento.
                type_info = symbol_info[0]
                result += f"{prefix}--variable: {name} | type: {type_info}\n"

        
        # Imprimir los hijos (sentencias)
        for child in self.children:
            result += child.__str__(level + 1)
            
        return result

class Declare(ASTNode):
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
        super().__init__(lineno, col_offset)  # Pasamos la ubicación al constructor base
        self.name = name  # Guardamos el nombre del identificador
    def __str__(self, level=0):
        # La representación en string no necesita cambiar
        prefix = '-' * level
        node_name = f"Ident: {self.name}"
        type_info = f" | type: {self.type}" if self.type is not None else ""
        return f"{prefix}{node_name}{type_info}\n"

class Literal(ASTNode):
     def __init__(self, value, lineno=None, col_offset=None): 
        super().__init__(lineno, col_offset)

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
        self.type = "String"

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
class Concat(ASTNode): pass 
class ReadFunction(ASTNode): pass
class WriteFunction(ASTNode): pass

# Sentencias
class While(ASTNode): pass
class Then(ASTNode): pass # Usado para cuerpos de if/while

class If(ASTNode):
    # La impresión se personaliza para que coincida con el formato Guard/Then
    def __str__(self, level=0):
        prefix = '-' * level
        result = f"{prefix}If\n"

        clauses = self.children
        if not clauses:
            return result

        num_clauses = len(clauses)

        # Imprimir los N-1 'Guard' anidados
        for i in range(num_clauses - 1):
            guard_prefix = '-' * (level + 1 + i)
            result += f"{guard_prefix}Guard\n"

        # Imprimir todos los bloques 'Then' con la indentación especial
        for i, clause in enumerate(clauses):
            # Calcular el nivel de indentación para este 'Then'
            then_level = 0
            if i == 0:
                #El primer 'Then' está en el nivel más profundo
                then_level = level + 1 + (num_clauses - 1)
            elif i == 1:
                #El segundo 'Then' está AL MISMO NIVEL que el primero
                then_level = level + 1 + (num_clauses - 1)
            else:
                #Los siguientes van subiendo un nivel cada vez
                then_level = level + 1 + (num_clauses - i)
            
            # Construir el bloque 'Then'
            then_prefix = '-' * then_level
            result += f"{then_prefix}Then\n"
            
            condition = clause.children[0]
            body = clause.children[1]
            
            # Agregar el contenido del 'Then' con un nivel más de indentación
            result += condition.__str__(then_level + 1)
            result += body.__str__(then_level + 1)
            
        return result


class Guard(ASTNode):
    pass

class Print(ASTNode): pass
class skip(ASTNode):
    def __str__(self, level=0):
        return f"{'-' * level}skip\n"
class Return(ASTNode): pass
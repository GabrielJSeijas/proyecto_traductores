class ASTNode:
    def __init__(self):
        self.children = []

    def add_child(self, node):
        self.children.append(node)

    def __str__(self, level=0):
        # Prefijo para mostrar el nivel del nodo en el árbol
        prefix = ""
        if level > 0:
            prefix = "-" * level

        node_name = self.__class__.__name__

        # Prefijo especial para nodos While en el primer nivel
        if isinstance(self, While) and level == 1:
            prefix = "--"

        result = prefix + node_name + "\n"

        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
            else:
                child_prefix = "-" * (level + 1)
                result += child_prefix + str(child) + "\n"
        return result

class Block(ASTNode):
    pass

class Declare(ASTNode): pass
class Sequencing(ASTNode): pass # Secuencia de instrucciones o expresiones
class Asig(ASTNode): pass # Asignación

class Ident(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self, level=0):
        # Representa un identificador (nombre de variable)
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        return prefix + f"Ident: {self.name}\n"

class Literal(ASTNode):
    def __init__(self, value):
        super().__init__()
        # Convierte cadenas 'true'/'false' a booleanos de Python
        if isinstance(value, str) and value.lower() == 'true':
            self.value = True
        elif isinstance(value, str) and value.lower() == 'false':
            self.value = False
        else:
            self.value = value

    def __str__(self, level=0):
        # Representa un valor literal (entero o booleano)
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        val_to_print = self.value
        if isinstance(self.value, bool):
            val_to_print = str(self.value).lower()
        return prefix + f"Literal: {val_to_print}\n"

class String(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def __str__(self, level=0):
        # Representa un literal de cadena
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        return prefix + f"String: \"{self.value}\"\n"

# Operaciones binarias y unarias
class Plus(ASTNode): pass # Suma
class Minus(ASTNode): pass # Resta (puede ser unaria o binaria)
class Mult(ASTNode): pass # Multiplicación

class Equal(ASTNode): pass    # Igualdad (==)
class NotEqual(ASTNode): pass   # Diferente (<>)
class Less(ASTNode): pass   # Menor que (<)
class Greater(ASTNode): pass    # Mayor que (>)
class Leq(ASTNode): pass   # Menor o igual (<=)
class Geq(ASTNode): pass   # Mayor o igual (>=)

class And(ASTNode): pass # Operador lógico AND
class Or(ASTNode): pass  # Operador lógico OR
class Not(ASTNode): pass # Operador lógico NOT

# Estructuras de expresión
class Comma(ASTNode): pass       # Separador de expresiones con coma
class TwoPoints(ASTNode): pass  # Separador de expresiones con dos puntos (rango)
class App(ASTNode): pass         # Aplicación de función o acceso a miembro

# Función especial de escritura
class WriteFunction(ASTNode): pass

# Sentencias
class While(ASTNode): pass # Bucle while
class Then(ASTNode): pass      # Parte 'then' de un guardia, contiene secuencia
class If(ASTNode): pass # Sentencia if
class Guard(ASTNode): pass     # Guarda de un if
class Print(ASTNode): pass # Sentencia de impresión
class skip(ASTNode): pass      # Sentencia de salto (no hace nada)
class Return(ASTNode): pass    # Sentencia de retorno

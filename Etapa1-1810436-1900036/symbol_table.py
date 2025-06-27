class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}  # {nombre: tipo}
        self.parent = parent  # Crucial para el alcance léxico

    def declare(self, name, type_info):
        """Intenta declarar una variable en el ámbito actual"""
        if name in self.symbols:
            return False  # Redeclaración
        self.symbols[name] = type_info
        return True

    def lookup(self, name):
        """Busca la variable en el ámbito actual y padres"""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None  # No encontrado

    def enter_scope(self):
        """Crea un nuevo ámbito anidado"""
        return SymbolTable(parent=self)

    def exit_scope(self):
        """Sale del ámbito actual (retorna al padre)"""
        return self.parent

    def __str__(self):
        """Representación simple de la tabla de símbolos para impresión"""
        result = ""
        for name, type_info in self.symbols.items():
            result += f"--variable: {name} | type: {type_info}\n"
        return result
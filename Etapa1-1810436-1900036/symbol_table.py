class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        self.level = 0 if parent is None else parent.level + 1

    def declare(self, name, type_info, lineno, col_offset):
        """
        Intenta declarar un símbolo.
        - Si el símbolo ya existe en el ámbito actual, devuelve la tupla
          de información de la declaración anterior (type, lineno, col).
        - Si no existe, lo añade y devuelve None.
        """
        if name in self.symbols:
            return self.symbols[name]  # Devuelve la info de la declaración previa
        
        self.symbols[name] = (type_info, lineno, col_offset) # Almacena la tupla completa
        return None # Éxito, no había declaración previa


    def lookup(self, name):
        """
        Busca un símbolo y devuelve solo su tipo.
        """
        if name in self.symbols:
            return self.symbols[name][0]  # Devuelve solo el tipo (el primer elemento de la tupla)
        
        if self.parent:
            return self.parent.lookup(name)
        
        return None

    def enter_scope(self):
        return SymbolTable(parent=self)

    def exit_scope(self):
        return self.parent
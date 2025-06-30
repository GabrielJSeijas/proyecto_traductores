class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        self.level = 0 if parent is None else parent.level + 1

    def declare(self, name, type_info):
        if name in self.symbols:
            return False
        self.symbols[name] = type_info
        return True

    def lookup(self, name):
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def enter_scope(self):
        return SymbolTable(parent=self)

    def exit_scope(self):
        return self.parent
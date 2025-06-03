class ASTNode:
    def __init__(self):
        self.children = []
    
    def add_child(self, node):
        self.children.append(node)
    
    def __str__(self, level=0):
        # Determine prefix based on level for standard nodes
        prefix = ""
        if level > 0:
            prefix = "-" * level + ""

        # Node name is class name by default
        node_display_name = self.__class__.__name__
        
        # For Block at root, override prefix (it has no prefix)
        if isinstance(self, Block) and level == 0:
            prefix = ""
            
        result = prefix + node_display_name + "\n"
        
        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1)
            else:
                # Handle raw string children (like formatted declarations)
                child_prefix = "-" * (level + 1) + ""
                result += child_prefix + str(child) + "\n"
        return result

class Block(ASTNode):
    # Override __str__ specifically for Block if it's the root
    def __str__(self, level=0):
        # Root Block node name has no prefix. Children are at level+1.
        result = self.__class__.__name__ + "\n"
        for child in self.children:
            if isinstance(child, ASTNode):
                result += child.__str__(level + 1) # Children start at level 1
            else:
                child_prefix = "-" * (level + 1) + "" # Should be at least level 1
                result += child_prefix + str(child) + "\n"
        return result

class Declare(ASTNode): pass
class Sequencing(ASTNode): pass # Will contain formatted strings or other ASTNodes
class Asig(ASTNode): pass

class Ident(ASTNode):
    def __init__(self, name):
        super().__init__()
        self.name = name
    
    def __str__(self, level=0):
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        return prefix + f"Ident: {self.name}\n"

class Literal(ASTNode):
    def __init__(self, value):
        super().__init__()
        # Store booleans as Python booleans for consistency if needed later
        if isinstance(value, str) and value.lower() == 'true':
            self.value = True
        elif isinstance(value, str) and value.lower() == 'false':
            self.value = False
        else:
            self.value = value # Could be int or bool
    
    def __str__(self, level=0):
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        # Python's bool.__str__() is 'True' or 'False', problem wants 'true', 'false'
        val_to_print = self.value
        if isinstance(self.value, bool):
            val_to_print = str(self.value).lower()
        return prefix + f"Literal: {val_to_print}\n"

class String(ASTNode):
    def __init__(self, value):
        super().__init__()
        self.value = value # Value should already be processed by lexer
    
    def __str__(self, level=0):
        prefix = ""
        if level > 0: prefix = "-" * level + ""
        return prefix + f"String: \"{self.value}\"\n"

# Binary and Unary Operations
class Plus(ASTNode): pass
class Minus(ASTNode): pass # Can be unary or binary
class Times(ASTNode): pass
# TkMult es '*', tu clase se llama Times, podría ser Mult para consistencia.
# class Divide(ASTNode): pass # No está en tu lexer actual
# class Mod(ASTNode): pass    # No está en tu lexer actual

class Eq(ASTNode): pass    # TkEqual ==
class Neq(ASTNode): pass   # TkNEqual <>
class Less(ASTNode): pass   # TkLess <
class Gt(ASTNode): pass    # TkGreater >
class Leq(ASTNode): pass   # TkLeq <=
class Geq(ASTNode): pass   # TkGeq >=

class And(ASTNode): pass
class Or(ASTNode): pass
class Not(ASTNode): pass

# Expression structure
class Comma(ASTNode): pass       # For 'expr, expr' (e.g. list literals, not in min/max example)
class TwoPoints(ASTNode): pass  # For 'expr : expr' (ranges, not in min/max example)
class App(ASTNode): pass         # For 'expr . expr' (like A.0)

# Special function handling (not used in min/max example's AST, but in general desc)
class WriteFunction(ASTNode): pass

# Statements
class While(ASTNode): pass
class Then(ASTNode): pass      # Child of Guard, contains Sequencing
class If(ASTNode): pass
class Guard(ASTNode): pass     # Child of If
class Print(ASTNode): pass
class Skip(ASTNode): pass      # Not in min/max example
class Return(ASTNode): pass    # Not in min/max example

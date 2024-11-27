# 1. check whether a variable/function is defined
# 2. scoping
# 1 and 2 can be done by symbol table
# each CPDSTMT is a new scope, which should have a symbol table.

# scan STMT by STMT and build the symbol table.
# int x = 0;
# {
#    print(x);
#    int x = 1;
# }

# 3. type checking
# if not supporting function call, only need to check EXPR and ACCESS

# in classical computers, we put global variables to the data section and local variables to the stack.
# temporary variables on the top of the stack
from parser import parser
from parser import ptnode

class semanticError():
	def __init__(self, row: int, col: int, info: str):
		self.row = row
		self.col = col
		self.info = info
	def __str__(self):
		return "Semantic error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info

class variable():
    def __init__(self, name, row, col, t):
        self.name = name
        self.row = row
        self.col = col
        self.type = t
        self.addr = -1

class symbolTable():
    def __init__(self):
        # table[scope num][identifier] = class variable
        # parent[scope num] = parent scope num
        self.table = [{}] # initialize with the global scope
        self.parent = {0: -1}
    
    def newscope(self, p):
        self.table.append({})
        scope_num = len(self.table) - 1
        self.parent[scope_num] = p

    def insert(self, s: int, v: variable) -> semanticError:
        if v.name in self.table[s]: # redefined
            return semanticError(v.row, v.col, f'variable {v.name} redefined')
        self.table[s][v.name] = v

class semanticAnalyzer():
    def construct_symbol_table(self, node: ptnode):
        st = symbolTable()
        cur_scope = 0

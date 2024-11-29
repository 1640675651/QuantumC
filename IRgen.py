# build control flow graph from scope-annotated AST
# 1. variable address assignment
# 2. scan through AST, convert statements to intermediate code
# 3. allocate temporary variable while expanding expressions
from lexer import lexer, token
from parser import parser
from semantic import symbolTable, variable, semanticAnalyzer

class instruction():
    def __init__(self, name, operands):
        self.name = name
        self.operands = [] # (segment, offset, len)

class basicBlock():
    def __init__(self):
        self.instructions = []
        self.next1 = None
        self.next2 = None
        self.condition = None # some variable/temp vars

class IRgenerator():
    def assign_addr(self, st: symbolTable) -> ('data section usage', 'stack usage'):
        def assign_stack_addr(st: symbolTable, scope: int, cur_stack_len: int) -> 'stack usage':
            for name, var in st.table[scope].items():
                var.addr = cur_stack_len
                var.segment = 'stack'
                cur_stack_len += var.size

            stack_len_max = cur_stack_len
            for child_scope in st.children[scope]:
                new_stack_len = assign_stack_addr(st, child_scope, cur_stack_len)
                stack_len_max = max(stack_len_max, new_stack_len)

            return stack_len_max

        data_len = 0
        for name, var in st.table[0].items():
            if type(var) == variable: # function does not have address
                var.addr = data_len
                var.segment = 'data'
                data_len += var.size
        
        # currently we only have main function, which has scope number 1
        stack_len = assign_stack_addr(st, 1, 0)
        return data_len, stack_len

    # convert each function to a control flow graph
    def AST2IR(self, node: 'S_node', st: symbolTable, stack_len: int) -> basicBlock:
        def STMTLIST2IR(node: 'STMTLIST_node', st: symbolTable, stack_len: int) -> basicBlock:
            for child in node.children:
                if child.name == 'CPDSTMT':
                    pass
                if child.name == 'EXPRSTMT':
                    pass
                if child.name == 'IFELSE':
                    pass
                if child.name == 'FOR':
                    pass
                if child.name == 'WHILE':
                    pass
                if child.name == 'JMP':
                    pass

        for decl in node.children.children:
            if decl.name == 'FUNCDECL':
                return func2IR(decl.children[3], st, stack_len) # pass STMTLIST into STMTLIST2IR

def print_st(st: symbolTable, scope_num = 0, depth = 0):
    print('\t'*depth, f'Scope {scope_num}:')
    for name, var in st.table[scope_num].items():
        if type(var) == variable:
            print('\t'*depth, var.name, var.type, var.segment, var.addr)
    for new_scope_num in st.children[scope_num]:
        print_st(st, new_scope_num, depth + 1)

def main():
    import sys
    if len(sys.argv) != 2:
        print('usage: IRgen.py sourcefile')
    else:
        file = open(sys.argv[1])
        l = lexer()
        err, tokens = l.run(file)
        if err:
            print(tokens)
            file.close()
            return
        
        p = parser()
        err, root = p.run(tokens)
        if err != None:
            print(err)
            file.close()
            return

        s = semanticAnalyzer()
        err, st = s.run(root)
        if err != None:
            print(err)
            file.close()
            return

        irgen = IRgenerator()
        data_len, stack_len = irgen.assign_addr(st)
        print_st(st)
        print('data section usage:', data_len)
        print('stack usage:', stack_len)
        file.close()

if __name__ == '__main__':
    main()
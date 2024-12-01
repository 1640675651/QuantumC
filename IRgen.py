# build control flow graph from scope-annotated AST
# 1. variable address assignment
# 2. scan through AST, convert statements to intermediate code
# 3. allocate temporary variable while expanding expressions
from lexer import lexer, token
from parser import parser
from semantic import symbolTable, variable, semanticAnalyzer

class memcell():
    def __init__(self, segment: str, offset: int, size: int):
        self.segment = segment
        self.offset = offset
        self.size = size

class instruction():
    def __init__(self, name, operands):
        self.name = name
        self.operands = [] # [memcell]

class basicBlock():
    def __init__(self):
        self.instructions = []
        self.next1 = None
        self.next2 = None
        self.branch = False # IFELSE

class loopBlock():
    def __init__(self):
        self.firstblock = None
        self.lastblock = None # should contain loop condition checking

class branchBlock():
    def __init__(self):
        self.firstblock = None # should contain condition evaluation
        self.lastblock = None # the merge point

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
    def AST2IR(self, node: 'S_node', st: symbolTable, stack_len: int) -> (basicBlock, 'new_stack_len'):
        cond_reg = memcell('cond', 0, 1)
        def STMTLIST2IR(node: 'STMTLIST_node', st: symbolTable, stack_len: int) -> ('firstblock', 'lastblock', 'new_stack_len'):
            firstblock = basicBlock()
            lastblock = firstblock
            stack_len_max = stack_len
            for child in node.children:
                if child.name == 'CPDSTMT':
                    if len(child.children) > 0:
                        new_fb, new_lb, new_stack_len = STMTLIST2IR(child.children[0], st, stack_len)
                        lastblock.next1 = new_fb
                        lastblock = new_lb
                        stack_len_max = max(stack_len_max, new_stack_len)
                if child.name == 'EXPRSTMT':
                    # the value of the expression is not needed
                    instructions, new_stack_len, _, _ = EXPR2IR(child, st, stack_len)
                    lastblock.instructions += instructions
                    stack_len_max = max(stack_len_max, new_stack_len)
                if child.name == 'IFELSE':
                    new_last_block, new_stack_len = IFELSE2IR(child, st, stack_len)
                    # create a new last block and point the last blocks of ifelse to the new last block
                    lastblock.next1 = new_last_block
                    lastblock = new_last_block
                    pass
                if child.name == 'FOR':
                    # treat loop as one single block
                    pass
                if child.name == 'WHILE':
                    # treat loop as one single block
                    pass
                if child.name == 'JMP':
                    pass

        # evaluate an expression, allocate temporary variables, return the temporary variable that contains the result
        def EXPR2IR(node: 'EXPR_node/BINARY_node/UNARY_node/CPDEXPR_node/ACCESS_node/literal', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            # maybe handle literal values at other places where the value is actually used.
            # that gives us more information on choosing the length of the temp var and we can save stack space if the value is not used.
            # here we need to check if the EXPR is solely a literal. If so, the literal is unused and we can emit no code about it.
            if type(actual_expr) == token: 
                    return [], stack_len, None
            if node.name == 'EXPR':
                return EXPR2IR(node.children[0], st, stack_len)
            elif node.name == 'BINARY':
                return BINARY2IR(node, st, stack_len)
            elif node.name == 'UNARY':
                return UNARY2IR(actual_expr, st, stack_len)
            elif node.name == 'CPDEXPR':
                return EXPR2IR(actual_expr.children[0], st, stack_len)
            elif node.name == 'ACCESS': # for access, just return the variable, instead of creating temp vars
                varname = actual_expr[0].value
                var = st.find(varname)
                return [], stack_len, memcell(var.segment, var.addr, var.size)

        # TODO: first write EXPR2IR and its required functions
        # maybe first write + - = for now
        def BINARY2IR(node: 'BINARY_node', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            insts = []
            lhs, operator, rhs = node.children
            stack_len_max = stack_len
            
            # evaluate lhs and rhs, stored in mem cells t1 and t2
            insts_lhs, new_stack_len, t1 = EXPR2IR(lhs, st, stack_len)
            stack_len_max = max(stack_len_max, new_stack_len)
            insts_rhs, new_stack_len, t2 = EXPR2IR(rhs, st, stack_len)
            stack_len_max = max(stack_len_max, new_stack_len)

            # if the two operands have different size, extend the shorter one
            

        def UNARY2IR(node: 'BINARY_node', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            pass

        def IFELSE2IR(node: 'IFELSE_node', st: symbolTable, stack_len: int) -> ('branchBlock', 'new_stack_len'):
            ret = branchBlock()
            ret.firstblock = basicBlock()
            ret.lastblock = basicBlock()
            
            # evaluate condition EXPR
            condexpr = node.children[0]
            instructions, new_stack_len, tempvar = EXPR2IR(condexpr, st, stack_len)
            ret.firstblock.instructions += instructions
            # store the evaluated bit to cond register
            ret.firstblock.instructions.append(instruction('tobool', tempvar, cond_reg))
            stack_len_max = max(stack_len, new_stack_len)
            ret.firstblock.branch = True

            # evaluate if body
            if_body = node.children[1]
            if_fb, if_lb, new_stack_len = STMT2IR(if_body, st, stack_len)
            ret.firstblock.next1 = if_fb
            if_lb.next1 = ret.lastblock
            stack_len_max = max(stack_len_max, new_stack_len)

            # evaluate else body
            if len(node.children) == 3:
                else_body = node.children[2]
                else_fb, else_lb, new_stack_len = STMT2IR(else_body, st, stack_len)
                ret.firstblock.next2 = else_fb
                else_lb.next1 = ret.lastblock
                stack_len_max = max(stack_len_max, new_stack_len)
            
            return ret, stack_len_max

        for decl in node.children.children:
            if decl.name == 'FUNCDECL':
                return STMTLIST2IR(decl.children[3], st, stack_len) # pass STMTLIST into STMTLIST2IR

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
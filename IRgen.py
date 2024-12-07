# build control flow graph from scope-annotated AST
# 1. variable address assignment
# 2. scan through AST, convert statements to intermediate code
# 3. allocate temporary variable while expanding expressions
from lexer import lexer, token
from parser import parser
from semantic import symbolTable, variable, semanticAnalyzer, typesize, assignment_ops, litsize

class memcell():
    def __init__(self, segment: str, offset: int, size: int):
        self.segment = segment
        self.offset = offset
        self.size = size
    def __str__(self):
        return f'({self.segment}, {self.offset}, {self.size})'
    def __repr__(self):
        return str(self)

class instruction():
    def __init__(self, name, operands):
        self.name = name
        self.operands = operands # [memcell]
    def __str__(self):
        return f'{self.name} {self.operands}'

class basicBlock():
    def __init__(self):
        self.instructions = []
        self.next = None

class loopBlock():
    def __init__(self):
        self.firstblock = None # check loop condition before entering
        self.secondblock = None # the first block in the loop body
        self.lastblock = None # check loop condition after 1 iteration
        self.next = None

class branchBlock():
    def __init__(self):
        self.firstblock = None # should contain condition evaluation
        self.thenblock = None # first block in then
        self.elseblock = None # first block in else
        self.next = None

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
        cond_reg = memcell('reg_cond', 0, 1)
        cond_creg = memcell('creg_cond', 0, 1)
        def STMTLIST2IR(node: 'STMTLIST_node', st: symbolTable, stack_len: int) -> ('firstblock', 'lastblock', 'new_stack_len'):
            firstblock = basicBlock()
            lastblock = firstblock
            stack_len_max = stack_len
            new_stack_len = stack_len
            for child in node.children:
                if child.name == 'CPDSTMT':
                    if len(child.children) > 0:
                        new_fb, new_lb, new_stack_len = STMTLIST2IR(child.children[0], st, stack_len)
                        lastblock.next1 = new_fb
                        lastblock = new_lb
                if child.name == 'EXPRSTMT':
                    # the value of the expression is not needed
                    instructions, new_stack_len, _ = EXPR2IR(child.children[0], st, stack_len)
                    lastblock.instructions += instructions
                if child.name == 'IFELSE':
                    ifelse_block, new_stack_len = IFELSE2IR(child, st, stack_len)
                    lastblock.next = ifelse_block
                    # create a new last block and point the next of the ifelse block to the new last block
                    lastblock = basicBlock()
                    ifelse_block.next = lastblock
                    pass
                if child.name == 'FOR':
                    # treat loop as one single block
                    pass
                if child.name == 'WHILE':
                    # treat loop as one single block
                    pass
                if child.name == 'JMP':
                    pass
                stack_len_max = max(stack_len_max, new_stack_len)
            return firstblock, lastblock, stack_len_max

        # evaluate an expression, allocate temporary variables, return the temporary variable that contains the result
        # for these functions, if the returned memcell is a temporary, its starting address must equal to the stack_len argument.
        # i.e. the result is stored in lowest possible address.
        # if the returned memcell is a variable (for ACCESS node), the memcell should directly refer to that variable.
        def EXPR2IR(node: 'EXPR_node/BINARY_node/UNARY_node/CPDEXPR_node/ACCESS_node/literal', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            # maybe handle literal values at other places where the value is actually used.
            # that gives us more information on choosing the length of the temp var and we can save stack space if the value is not used.
            # here we need to check if the EXPR is solely a literal. If so, the literal is unused and we can emit no code about it.
            if type(node) == token:
                return literal2IR(node, stack_len)
            if node.name == 'EXPR':
                return EXPR2IR(node.children[0], st, stack_len)
            elif node.name == 'BINARY':
                return BINARY2IR(node, st, stack_len)
            elif node.name == 'UNARY':
                return UNARY2IR(node.children[0], st, stack_len)
            elif node.name == 'CPDEXPR':
                return EXPR2IR(node.children[0], st, stack_len)
            elif node.name == 'ACCESS': # for access, just return the variable, instead of creating temp vars
                var = st.find(node.scope, node.children[0].value, node.children[0].row, node.children[0].col)
                return [], stack_len, memcell(var.segment, var.addr, var.size)

        def literal2IR(node: token, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            value = 0
            if node.type == 'intlit':
                value = int(node.value)
            elif node.type == 'chrlit':
                value = ord(node.value[1]) # node.value contains single quote for char literals
            size = litsize(node)
            #value_trunc = value & (2**size-1) # truncate here or in later code gen?
            t = memcell('stack', stack_len, size)
            insts = [instruction('assign', [t, value])]
            return insts, stack_len+size, t

        def BINARY2IR(node: 'BINARY_node', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            insts = []
            lhs, operator, rhs = node.children
            stack_len_max = stack_len

            # if is assignment operator, do not need to create temporary for result            
            # otherwise allocate temp memory cell for result
            # use the lowest possible offset
            t_result = None
            if operator.value not in assignment_ops:
                t_result = memcell('stack', stack_len, node.size)
                stack_len += node.size
            # FUTURE todo: can reuse temp according to type of operation.
            # for example, if we want to compute t1 + t2, we don't need to create a new t_result, we can just use t1 to hold the sum, i.e. t1 = t1 + t2.
            # This depends on whether the machine instruction allows in-place operation.
            # for now just make things simple

            # evaluate lhs and rhs, stored in mem cells t1 and t2
            # must guarantee t_result, t1, and t2 use different address
            # note if a children is an ACCESS node, the t1 or t2 here is the address of that variable, not a temporary.
            insts_lhs, new_stack_len, t1 = EXPR2IR(lhs, st, stack_len)
            stack_len_max = max(stack_len_max, new_stack_len)
            if operator.value in assignment_ops:
                t_result = t1
            if type(lhs) == token or lhs.name != 'ACCESS':
                stack_len += t1.size
                stack_len_max = max(stack_len_max, stack_len)
            insts_rhs, new_stack_len, t2 = EXPR2IR(rhs, st, stack_len)
            stack_len_max = max(stack_len_max, new_stack_len)
            if type(rhs) == token or rhs.name != 'ACCESS':
                stack_len += t2.size
                stack_len_max = max(stack_len_max, stack_len)
            insts += insts_lhs
            insts += insts_rhs
            # if the two operands have different size, extend the shorter one
            # put the extended variable right after t2
            # assuming the copy instruction handles extension and truncation
            t1_ext = t1
            t2_ext = t2
            if t1.size > t2.size:
                t2_ext = memcell('stack', t2.offset+t2.size, t1.size)
                insts.append(instruction('copy', [t2, t2_ext]))
                stack_len += t1.size
                stack_len_max = max(stack_len_max, stack_len)
            elif t1.size < t2.size:
                t1_ext = memcell('stack', t2.offset+t2.size, t2.size)
                insts.append(instruction('copy', [t1, t1_ext]))
                stack_len += t2.size
                stack_len_max = max(stack_len_max, stack_len)

            if operator.value == '+':
                insts.append(instruction('add_ex', [t1_ext, t2_ext, t_result]))
            elif operator.value == '-':
                insts.append(instruction('sub_ex', [t1_ext, t2_ext, t_result]))
            elif operator.value == '*':
                insts.append(instruction('mul_ex', [t1_ext, t2_ext, t_result]))
            elif operator.value == '/':
                insts.append(instruction('mul_ex', [t1_ext, t2_ext, t_result]))
            elif operator.value == '=':
                insts.append(instruction('copy', [t2_ext, t1])) # t_result = t1 here
            # TODO: add more operators

            return insts, stack_len_max, t_result

        def UNARY2IR(node: 'UNARY_node', st: symbolTable, stack_len: int) -> (['instruction'], 'new_stack_len', 'temp memcell'):
            pass # TODO

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
            ret.firstblock.instructions.append(instruction('measure', cond_reg, cond_creg))
            stack_len_max = max(stack_len, new_stack_len)
            ret.firstblock.branch = True

            # evaluate if body
            then_body = node.children[1]
            then_fb, then_lb, new_stack_len = STMT2IR(then_body, st, stack_len)
            ret.thenblock = then_fb
            stack_len_max = max(stack_len_max, new_stack_len)

            # evaluate else body
            if len(node.children) == 3:
                else_body = node.children[2]
                else_fb, else_lb, new_stack_len = STMT2IR(else_body, st, stack_len)
                ret.elseblock = else_fb
                stack_len_max = max(stack_len_max, new_stack_len)
            
            return ret, stack_len_max

        for decl in node.children[0].children:
            if decl.name == 'FUNCDECL':
                return STMTLIST2IR(decl.children[3], st, stack_len) # pass STMTLIST into STMTLIST2IR
    
    def run(self, node: 'S_node', st: symbolTable) -> (basicBlock, 'data_len', 'stack_len'):
        data_len, stack_len = self.assign_addr(st)
        firstblock, lastblock, stack_len = self.AST2IR(node, st, stack_len)
        return firstblock, data_len, stack_len

def print_st(st: symbolTable, scope_num = 0, depth = 0):
    print('\t'*depth, f'Scope {scope_num}:')
    for name, var in st.table[scope_num].items():
        if type(var) == variable:
            print('\t'*depth, var.name, var.type, var.segment, var.addr)
    for new_scope_num in st.children[scope_num]:
        print_st(st, new_scope_num, depth + 1)

def print_CFG(blk):
    def print_basic(blk: basicBlock):
        print('Basic Block')
        for i in blk.instructions:
            print(i)
        
    def print_branch(blk: branchBlock):
        print('IF')
        print_basic(blk.firstblock)
        print_CFG(blk.thenblock)
        if blk.elseblock != None:
            print('ELSE')
            print_branch(blk.elseblock)
        print('ENDIF')

    def print_loop(blk: loopBlock):
        pass

    while blk != None:
        if type(blk) == basicBlock:
            print_basic(blk)
        if type(blk) == branchBlock:
            print_branch(blk)
        if type(blk) == loopBlock:
            print_loop(blk)
        blk = blk.next

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
        firstblock, data_len, stack_len = irgen.run(root, st)
        #print_st(st)
        print_CFG(firstblock)
        print('data section usage:', data_len)
        print('stack usage:', stack_len)
        file.close()

if __name__ == '__main__':
    main()
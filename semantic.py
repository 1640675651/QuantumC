# 1. check whether a variable/function is defined
# 2. scoping
# 1 and 2 are implemented by symbol table
# each CPDSTMT is a new scope.

# 3. type checking
# not supporting function call, only need to check ACCESS

# in classical computers, we put global variables to the data section and local variables to the stack.
# temporary variables on the top of the stack
from lexer import lexer, token
from parser import parser, ACCESS_node, parserError

assignment_ops = {'=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '~=', '^=', '&&=', '||=', '<<=', '>>='}

class semanticError():
    def __init__(self, row: int, col: int, info: str):
        self.row = row
        self.col = col
        self.info = info
    def __str__(self):
        return "Semantic error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info

class semanticWarning():
    pass

def typesize(t: str) -> int:
    if t == 'void':
        return 0
    if t.startswith('int'):
        return int(t.strip('int'))
    if t == 'char':
        return 8
    if t == 'bit':
        return 1

def litsize(t: token) -> int:
    if t.type == 'chrlit':
        return 8
    elif t.type == 'intlit':
        v = int(t.value)
        if -8 <= v <= 7:
            return 4
        elif -128 <= v <= 127:
            return 8
        elif -32768 <= v <= 32767:
            return 16
        #elif -2147483648 <= v <= 2147483647:
        else:
            return 32
        # TODO: maybe need some warning for overflow

class variable():
    def __init__(self, node: 'VARDECL_node'):
        self.type = node.children[0].value
        self.size = typesize(self.type)
        self.name = node.children[1].value
        self.row = node.children[1].row
        self.col = node.children[1].col
        self.addr = None
        self.segment = None

class function():
    def __init__(self, ret_t, name, row, col, paramlist: [('type', 'id')]):
        self.ret_t = ret_t
        self.name = name
        self.row = row
        self.col = col
        self.paramlist = paramlist

class symbolTable():
    def __init__(self):
        # table[scope num][identifier] = class variable
        # parent[scope num] = parent scope num
        self.table = [{}] # initialize with the global scope
        self.parent = {0: -1}
        self.children = [[]]
    
    def newscope(self, p):
        scope_num = len(self.table)
        self.table.append({})
        self.children.append([])
        self.parent[scope_num] = p
        self.children[p].append(scope_num)

    def insert(self, s: int, v: variable) -> semanticError:
        if v.name in self.table[s]: # redefined
            return semanticError(v.row, v.col, f'name {v.name} redefined')
        self.table[s][v.name] = v
        return None

    def find(self, s: int, name: str, row: int, col: int) -> variable:
        if name in self.table[s]:
            var = self.table[s][name]
            if (var.row, var.col) <= (row, col):
                return var
        if s != 0:
            return self.find(self.parent[s], name, row, col)
        return None

class semanticAnalyzer():
    def construct_symbol_table(self, node: 'S_node') -> symbolTable:
        # TODO: the statement following if/else/for/while cannot be a declaration
        def construct_st_dfs(node: 'ptnode', scope: int, st: symbolTable) -> semanticError:
            node.scope = scope # annotate scope information in the AST
            err = None
            if node.name == 'VARDECL':
                var = variable(node)
                err = st.insert(scope, var)
            elif node.name == 'ARRDECL':
                row = node.children[1].row
                col = node.children[1].col
                err = semanticError(row, col, "array is not supported")
            elif node.name == 'CPDSTMT': # enter a new scope
                if len(node.children) > 0:
                    new_scope_num = len(st.table)
                    st.newscope(scope)
                    err = construct_st_dfs(node.children[0], new_scope_num, st)
            elif node.name == 'ACCESS':
                row = node.children[0].row
                col = node.children[0].col
                if len(node.children) > 1:
                    err = semanticError(row, col, "array access is not supported")
                else:
                    name = node.children[0].value
                    var = st.find(scope, name, row, col)
                    if var == None:
                        err = semanticError(row, col, f"undefined identifier {name}")
            elif node.name == 'CALLEXPR':
                name = node.children[0].value
                row = node.children[0].row
                col = node.children[0].col
                func = st.find(scope, name, row, col)
                if func == None:
                    err = semanticError(row, col, f"undefined identifier {name}")
            if err != None:
                return err
            #else: # need to recursively mark the the scope of all nodes
            for child in node.children:
                if type(child) == token:
                    continue
                err = construct_st_dfs(child, scope, st)
                if err != None:
                    break
            return err

        st = symbolTable()
        cur_scope = 0
        # insert the built-in print function
        print_func = function('void', 'print', 0, 0, [('int', 'x')])
        st.insert(0, print_func)
        
        decllist = node.children[0]
        for child in decllist.children:
            if child.name == 'VARDECL':
                var = variable(child)                
                err = st.insert(0, var)
                if err != None:
                    return err
            elif child.name == 'ARRDECL':
                row = child.children[1].row
                col = child.children[1].col
                return semanticError(row, col, "array is not supported")
            elif child.name == 'FUNCDECL':
                funcname = child.children[1].value
                row = child.children[1].row
                col = child.children[1].col
                if funcname != 'main':
                    return semanticError(row, col, "user-defined function is not supported")
                ret_t = child.children[0].value

                if ret_t != 'void':
                    return semanticError(row, col, "the main function should have void return type")
                paramlist = child.children[2]

                if len(paramlist.children) > 0:
                    return semanticError(row, col, "the main function should not have parameters")

                func = function(ret_t, funcname, row, col, [])
                err = st.insert(0, func)
                if err != None:
                    return err

                st.newscope(0)
                err = construct_st_dfs(child.children[3], 1, st)
                if err != None:
                    return err
        return st

    def typecheck(self, node: 'S_node', st: symbolTable,):
        def is_assignment_op(op: token):
            return '=' in token.value and token.value != '==' and token.value != '!='

        def typecheck_dfs(node: 'ptnode', st: symbolTable, inloop: bool) -> semanticError:
            if type(node) == token:
                if node.type == 'intlit':
                    intval = int(node.value)
                    if intval > 2**31 - 1 or intval < - 2**31:
                        return semanticError(node.row, node.col, f'{intval} exceeds the maximum range of int32')
                if node.type == 'chrlit':
                    if len(node.value.strip("'")) != 1:
                        return semanticError(node.row, node.col, 'character literal must contain exactly 1 character')
                if node.type == 'strlit':
                    return semanticError(node.row, node.col, 'string is not supported')
                if node.type == 'kw':
                    if node.value == 'return':
                        return semanticError(node.row, node.col, 'return statement is not supported') 
                    if (node.value == 'break' or node.value == 'continue') and inloop == False:
                        return semanticError(node.row, node.col, f'{node.value} not within loop context')
                return None 
            # ++/-- must operate on variables
            if node.name == 'UNARY':
                # prefix operator, like ++i, -i
                if type(node.children[0]) == token and node.children[0].type == 'op':
                    operator, operand = node.children
                    if (operator.value == '++' or operator.value == '--') and type(operand) != ACCESS_node:
                        return semanticError(operator.row, operator.col, '++/-- must operate on variables')
                # postfix operator
                else:
                    operand, operator = node.children
                    if type(operand) != ACCESS_node:
                        return semanticError(operator.row, operator.col, '++/-- must operate on variables')
            # for assignment operators, LHS must be variable
            if node.name == 'BINARY':
                lhs, operator, rhs = node.children
                if operator.value in assignment_ops:
                    if type(lhs) != ACCESS_node:
                        return semanticError(operator.row, operator.col, 'the left hand side of an assignment operator must be a variable')
                # TODO: cannot do > < >= <= on single-bit values

            for child in node.children:
                child_inloop = inloop
                if type(child) != token and (child.name == 'FOR' or child.name == 'WHILE'):
                    child_inloop = True
                err = typecheck_dfs(child, st, child_inloop)
                if err != None:
                    return err

            # EXPR data size annotation
            if node.name == 'EXPR':
                if type(node.children[0]) == token:
                    node.size = litsize(node.children[0])
                else:
                    node.size = node.children[0].size
            if node.name == 'BINARY':
                lhs, op, rhs = node.children
                # should I use 1 bit temp var to store the result for comparison/logical operations
                # maybe not, consider the case a + (b>c).
                # though it's weird, it's legal expression
                # if I store the result of b>c into 1 bit temp var, further extension is needed.
                # if op.value in {'<', '>', '<=', '>=', '==', '!=', '&&', '||', '!'}:
                #     node.size = 1 
                # else:
                if type(lhs) == token and type(rhs) == token:
                    node.size = max(litsize(lhs), litsize(rhs)) # 0 for literal, size not determined yet
                elif type(lhs) == token:
                    if rhs.size == 0:
                        return semanticError(operator.row, operator.col, f'cannot operate on void type')
                    node.size = rhs.size
                elif type(rhs) == token:
                    if lhs.size == 0:
                        return semanticError(operator.row, operator.col, f'cannot operate on void type')
                    node.size = lhs.size
                else:
                    if lhs.size == 0 or rhs.size == 0:
                        return semanticError(operator.row, operator.col, f'cannot operate on void type')
                    node.size = max(lhs.size, rhs.size)
            if node.name == 'UNARY':
                operand = node.children[1]# default prefix operator
                if type(node.children[1]) == token and node.children[1].type == 'op': # postfix operator
                    operand = node.children[0]
                if type(operand) == token:
                    node.size = litsize(operand)
                else:
                    node.size = operand.size
                    if node.size == 0:
                        return semanticError(operator.row, operator.col, f'cannot operate on void type')
            if node.name == 'ACCESS':
                var = st.find(node.scope, node.children[0].value, node.children[0].row, node.children[0].col)
                node.size = var.size
            if node.name == 'CPDEXPR':
                node.size = node.children[0].size
            if node.name == 'CALLEXPR':
                identifier = node.children[0]
                if inloop == True:
                    return semanticError(identifier.row, identifier.col, 'function call in a loop is not supported')
                func = st.find(node.scope, identifier.value, identifier.row, identifier.col)
                node.size = typesize(func.ret_t)
                # check the number of arguments
                arglist = node.children[1].children
                if len(arglist) != len(func.paramlist):
                    return semanticError(identifier.row, identifier.col, f'number of argument mismatch, expect {len(func.paramlist)}, got {len(arglist)}')
                # check through the arglist and find if there's void arguments
                for i in arglist:
                    if i.size == 0:
                        return semanticError(identifier.row, identifier.col, f'argument has void type')
            return None

        return typecheck_dfs(node, st, False)

    def run(self, node: 'S_node') -> (semanticError, symbolTable):
        st = self.construct_symbol_table(node)
        if type(st) == semanticError:
            return st, None

        err = self.typecheck(node, st)
        if err != None:
            return err, None
        return None, st

def print_st(st: symbolTable, scope_num = 0, depth = 0):
    print('\t'*depth, f'Scope {scope_num}:', st.table[scope_num].keys())
    for new_scope_num in st.children[scope_num]:
        print_st(st, new_scope_num, depth + 1)

def print_ast(node, depth: int):
    print('\t'*depth + str(node), end = '')
    if type(node) != token: 
        size_str = ' '
        if (node.name == 'EXPR' or node.name == 'UNARY' or node.name == 'BINARY' or node.name == 'ACCESS' or node.name == 'CPDEXPR' or node.name == 'CALLEXPR'):
            size_str += str(node.size)
        print(size_str, node.scope, end = '')
    print()
    # do not expand error or terminals
    if type(node) != parserError and type(node) != token:
        for child in node.children:
            print_ast(child, depth+1)

def main():
    import sys
    if len(sys.argv) != 2:
        print('usage: semantic.py sourcefile')
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
        else:
            #print_st(st)
            print_ast(root, 0)
        file.close()

if __name__ == '__main__':
    main()

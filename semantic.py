# 1. check whether a variable/function is defined
# 2. scoping
# 1 and 2 are implemented by symbol table
# each CPDSTMT is a new scope.

# 3. type checking
# not supporting function call, only need to check EXPR and ACCESS

# in classical computers, we put global variables to the data section and local variables to the stack.
# temporary variables on the top of the stack
from lexer import lexer, token
from parser import parser

class semanticError():
    def __init__(self, row: int, col: int, info: str):
        self.row = row
        self.col = col
        self.info = info
    def __str__(self):
        return "Semantic error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info

class semanticWarning():
    pass

class variable():
    def __init__(self, node: 'VARDECL_node'):
        self.type = node.children[0].value
        self.name = node.children[1].value
        self.row = node.children[1].row
        self.col = node.children[1].col
        self.addr = None

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
            if (var.row, var.col) < (row, col):
                return var
        if s != 0:
            return self.find(self.parent[s], name, row, col)
        return None

class semanticAnalyzer():
    def construct_symbol_table(self, node: 'S_node') -> symbolTable:
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
                row = node.children[0].row
                col = node.children[0].col
                err = semanticError(row, col, "function call is not supported")
            else:
                for child in node.children:
                    if type(child) == token:
                        continue
                    err = construct_st_dfs(child, scope, st)
                    if err != None:
                        break
            return err

        st = symbolTable()
        cur_scope = 0
        
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

    def typecheck(self, node: 'S_node'):
        def typecheck_dfs(node: 'ptnode') -> semanticError:
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
                return None
            for child in node.children:
                err = typecheck_dfs(child)
                if err != None:
                    return err
            return None

        return typecheck_dfs(node)

    def run(self, node: 'S_node'):
        st = self.construct_symbol_table(node)
        if type(st) == semanticError:
            print(st)
        else:
            print_st(st)

        err = self.typecheck(node)
        if err != None:
            print(err)

def print_st(st: symbolTable, scope_num = 0, depth = 0):
    print('\t'*depth, f'Scope {scope_num}:', st.table[scope_num].keys())
    for new_scope_num in st.children[scope_num]:
        print_st(st, new_scope_num, depth + 1)

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
        s.run(root)

if __name__ == '__main__':
    main()

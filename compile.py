import sys
from lexer import lexer
from parser import parser
from semantic import semanticAnalyzer
from IRgen import IRgenerator
from codegen import codegenerator

def main():
    if len(sys.argv) != 2:
        print('usage: compile.py sourcefile')
        return

    file = open(sys.argv[1])
    
    # lexical analysis
    l = lexer()
    err, tokens = l.run(file)
    if err:
        print(tokens)
        file.close()
        return
    
    # syntactical analysis
    p = parser()
    err, root = p.run(tokens)
    if err != None:
        print(err)
        file.close()
        return

    # semantic analysis
    s = semanticAnalyzer()
    err, st = s.run(root)
    if err != None:
        print(err)
        file.close()
        return

    # intermediate representation
    irgen = IRgenerator()
    firstblock, data_len, stack_len = irgen.run(root, st)

    # code generation
    codegen = codegenerator()
    code = codegen.run(firstblock, data_len, stack_len)

    print(code)
    file.close()

main()
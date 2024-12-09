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

    sourcefile = open(sys.argv[1])
    
    # lexical analysis
    l = lexer()
    err, tokens = l.run(sourcefile)
    if err:
        print(tokens)
        sourcefile.close()
        return
    
    # syntactical analysis
    p = parser()
    err, root = p.run(tokens)
    if err != None:
        print(err)
        sourcefile.close()
        return

    # semantic analysis
    s = semanticAnalyzer()
    err, st = s.run(root)
    if err != None:
        print(err)
        sourcefile.close()
        return

    # intermediate representation
    irgen = IRgenerator()
    firstblock, data_len, stack_len, cregs = irgen.run(root, st)

    # code generation
    codegen = codegenerator()
    code = codegen.run(firstblock, data_len, stack_len, cregs)

    output_file = open('out.qasm3', 'w')
    #print(code)
    output_file.write(code)
    sourcefile.close()
    output_file.close()

main()
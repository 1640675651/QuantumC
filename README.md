
# Lexer

## Token Types:
1. keywords\
	if else for while break continue return bit int4 int8 int16 int32 char void

2. identifiers\
	[a-zA-Z_][a-zA-Z0-9_]*

3. operators\
	\+ - * / % = & | ~ ^ && || ! < > <= >= == != << >> ++ -- += -= *= /= &= |= ~= ^= &&= ||= %= <<= >>=

4. literals\
	4.1. int literal
	[0-9]* 

	4.2. string literal
	".*" 

	4.3. character literal
	'.*'
	
5. punctuations\
	( ) [ ] { } , : ;

6. whitespaces\
	[ \t\n]* | [\\\\\n]*

7. comments\
	/\*.\*\*/ | //.*\n | //.*EOF

## FSM Design
The lexer is implemented as an FSM (Finite State Machine). The FSM takes 1 input character at a time and performs a transition. The transition rule of each state is written as a function. For each input character, we just call the transition function of the current state. All transition rules are in lexer.py. The FSM takes as many characters as possible, until there's no possible transitions. If the final state is acceptable, we get a token, otherwise there's an error. Whitespace and comment tokens will be ignored.

One simplification for the FSM: since keywords all satisfy the regular expression of identifiers, we don't create specific states for keywords. Instead, we record of the scanned string for the current token. When the final state is id, we check if the scanned string is a keyword.

Handling backslash+newline: backslash+newline ("\\\\\\n") is treated as an empty string. We don't use the FSM to handle this pattern to reduce the number of states. Instead we lookahead 1 character to detect this pattern before sending the input character to the FSM. 

Non-accept states: 
1. empty (start)
2. instrlit (inside of string literal, i.e. double quote not closed yet, same for inchrlit, inblkcomm)
3. inchrlit (inside of character literal), inlinecomm (inside of line comment)
4. inblkcomm (inside of block comment)
5. unclosed_str (double quote not closed but reached the end of line)
6. unclosed_chr (single quote not closed but reached the end of line)

Accept states:  
1. id (identifier)
2. op (operator)
3. intlit (int literal)
4. strlit (string literal)
5. chrlit (character literal)
6. punc (punctuation)
7. space (whitespace)
8. inlinecomm (inside of line comment)
9. comment (end of comment)

Error handling: there are 2 possible types of lexical errors: 
1. Unrecognized character. This happens when the FSM sees an character that does not lead to any transitions in the empty state. 

2. Unclosed double quote, single quote, and block comment. This happens when the FSM is in instrlit, inchrlit, inblkcomm, unclosed_str, unclosed_chr and no further transitions are available.

## How to test the lexer
python3 lexer.py sourcefile\
This will output the token list to stdout

# Parser

## Grammar Definition
See CFG.txt

## Parsing Algorithm
Hand-written recursive descent. Each non-terminal node has an expand() function, which determines which portion of the input token stream belongs to which child node. For expression evaluation, we use precedence climbing for operator precedence parsing.

## How to test the parser
python3 parser.py sourcefile\
This will output the AST to stdout\
Demo video: https://youtu.be/MKKk0_XGiAU (accessible with columbia.edu account)

# Semantic Analysis

## Scoping and Symbol Table
In semantic analysis, we first dfs on the AST and construct the symbol table, meanwhile we annotate the scope of each AST node for further reference. To find a symbol in the symbol table, we need a scope number, identifier name, and the row and column number of the reference. The symbol table search through the scope hierarchy, if a definition before (row, col) is found, it returns the symbol. 

## Type checking
The type system is very simple in this compiler, since array and general function call are not supported at this time. Reasons will be explained later. All variables are numbers, we just do automatic truncation and extension. In the type checking phase, we annotate the size of each expression node for further reference.

# Intermediate Representation

## Control flow graph
In normal compilers, control flow graph are just basic block and edges. Unlike classical computers, currently we don't have access to the program counter of quantum computers. QASM3 provides for/while/ifelse for control flow. To mimic the structure of QASM3, 3 types of blocks are used in our control flow graph. Each type of block has a pointer to the next block. 

1) basicblock.
   
   A basicblock is just a list of instructions to be executed sequentially. 
2) branchblock. A branch block contains:
   
   2.1) condition block, which contains instructions to evaluate the condition expression.
   
   2.2) then block, the first basic block in the then branch.
   
   2.3) else block, the first basic block in the else branch.
3) loopblock. A loop block contains:
   
   3.1) preloop block, which contains instructions for initialization and condition expression evaluation.
   
   3.2) body block, the loop body.
   
   3.3) postloop block, which contains instructions for operations after each iteration and condition evaluation for the next iteration.

## Intermediate code/"ISA"
In QASM3, the instructions for quantum computers are bit-level gates. A higher level instruction set is introduced to represent the register-level arithmetic and logical operations. See ISA.txt for details.

# Code Generation
To convert intermediate code to QASM3, we need to implement each instruction in the instruction set, somewhat like writing ALUs for an FPGA. The arithmetic operations are adapted from the open-source QArithmetic library: https://github.com/hkhetawat/QArithmetic/tree/master

# Memory Layout
In today's quantum computers we actually do not have RAM. All we have is an array of qubits. We can treat them as registers or memory cells, whatever we like. For clearer memory management, we intentionally divide the qubits to memory and registers.

## Registers
1) Carry. Carry bits used in arithmetic operations.
2) Tmp. Some operations requires temporary registers. For example, to implement a comparator, we subtract two operands and use the sign bit as result. The result of the subtraction needs to be stored in tmp.
3) Cond. A single-bit register holding the result of condition evaluation. 

## Memory
1) Stack. Contains local variables and temporary variables.
2) Data. Contains global variables.

# Limitations
1) Function call. As mentioned above, we cannot manipulate the program counter of a quantum computer. goto/call/return are not possible.
2) Arrays and dynamic memory. In QASM3, all operands must have fixed address. Therefore, the address of all variables must be determined at compile time.
3) Printing in loops. Print() calls are implemented through measurements, which moves information from quantum registers to classical registers. All classical registers must be declared in the beggining of the QASM3 program. The compiler must know the number of prints at compile time.

# How to run
To compile, run python3 compile.py sourcefile. The output is out.qasm3.

To run qasm3 file, we need qiskit Aer simulator. Installing qiskit: https://docs.quantum.ibm.com/guides/install-qiskit. This need to be installed in a python virtual environment. In the virtual environment, install qiskit-aer: https://qiskit.github.io/qiskit-aer/getting_started.html 

After these packages are installed, run python3 run_qasm3.py out.qasm3. The result will be in a dictionary format. The key is the result. One thing to notice is that quantum simulation is very resource-consuming since its time and memory complexity scales exponentially with the number of qubits. On my computer with 32GB of RAM, the maximum number of qubits can be simulated is about 30, so refrain from using large data types...
# Team member
Hongzheng Zhu hz2915

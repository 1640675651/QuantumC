
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
The lexer is implemented as an FSM (Finite State Machine). The FSM takes 1 input character at a time and performs a transition. The transition rule of each state is written as a function. For each input character, we just call the transition function of the current state. All transition rules are in lexer.py. The FSM takes as many characters as possible, until there's no possible transitions. If the final state is acceptable, we get a token, otherwise there's an error.

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
1. unrecognized character. This happens when the FSM sees an character that does not lead to any transitions in the empty state. 

2. Unclosed double quote, single quote, and block comment. This happens when the FSM is in instrlit, inchrlit, inblkcomm, unclosed_str, unclosed_chr and no further transitions are available.

## How to Test the Lexer
python3 lexer.py sourcefile\
This will output the token list to stdout

# Team member
Hongzheng Zhu hz2915


# Lexer

## Token types:
1. keywords
if else for while break continue return bit int4 int8 int16 int32 char void

2. identifiers
[a-zA-Z_][a-zA-Z0-9_]*

3. operators
\+ - * / % = & | ~ ^ && || ! < > <= >= == != << >> ++ -- += -= *= /= &= |= ~= ^= &&= ||= %= <<= >>=

4. literals
	4.1. int literal
	[0-9]* 

	4.2. string literal
	".*" 

	4.3. character literal
	'.*'
	
5. punctuations
( ) [ ] { } , : ;

6. whitespaces
[ \t\n]* | [\\\n]*

7. comments
/*.**/ | //.*\n | //.*EOF

## How to test the lexer
python3 lexer.py sourcefile
This will output the token list to stdout
def isletter(c: 'char') -> bool:
	return ord('a') <= ord(c) <= ord('z') or ord('A') <= ord(c) <= ord('Z')

def isnumber(c: 'char') -> bool:
	return ord('0') <= ord(c) <= ord('9')

def isop(c: 'char') -> bool:
	return c in "+-*/%=<>!&|~^"

def ispunc(c: 'char') -> bool:
	return c in "()[]{},:;"

def isspace(c: 'char') -> bool:
	return c in " \t\n"

#class lexerState():
#	def __init__(self, state, curstr):
#		self.state = state
#		self.curstr = curstr

# error types: 
# 1. unrecognized character
# 2. unclosed " ' \*
class lexerError():
	def __init__(self, row: int, col: int, info: str):
		self.row = row
		self.col = col
		self.info = info
	def __str__(self):
		return "Lexical error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info

class token():
	def __init__(self, token_type: str, value: str):
		self.type = token_type
		self.value = value
	def __str__(self):
		return '<'+self.type+', '+self.value+'>'


class lexer():
	def __init__(self):
		#self.file = file
		self.states = ['empty', 'kw', 'id', 'op', 'intlit', 'strlit', 'chrlit', 'instrlit', 'inchrlit', 'punc', 'space', 'inlinecomm', 'inblkcomm', 'comment', 'unclosed_str', 'unclosed_chr']
		self.accept = [False, True, True, True, True, True, True, False, False, True, True, True, False, True, False, False]
		self.keywords = {'if', 'else', 'for', 'while', 'break', 'continue', 'return', 'bit', 'int4', 'int8', 'int16', 'int32', 'char', 'void'}
		self.ops = {'+', '-', '*', '/', '%', '=',\
					'&', '|', '~', '^', '<<', '>>',\
					'&&', '||', '!',\
					'<', '>', '<=', '>=', '==', '!=',\
					'++', '--', '+=', '-=', '*=', '/=', '%=',\
					'&=', '|=', '~=', '||=', '<<=', '>>=',\
					'^=', '&&='}
		self.puncs = {'(', ')', '[', ']', '{', '}', ',', ':', ';'}
		self.transitions = [self.transition_empty, None, self.transition_id, self.transition_op,\
							self.transition_intlit, self.transition_strlit, self.transition_chrlit, self.transition_instrlit, self.transition_inchrlit,\
							self.transition_punc, self.transition_space, self.transition_inlinecomm, self.transition_inblkcomm, self.transition_comment, 
							self.transition_unclosed_str, self.transition_unclosed_chr]

	def run(self, file: 'fileobj') -> ('err: bool', 'lexerError/tokens'):
		self.row = 0
		self.col = 0
		self.lastchr = file.read(1)
		tokens = []
		err = 0
		while self.lastchr != '':
			err, ret = self.next_token(file)
			if err > 0:
				# ignore whitespaces and comments
				# special case: line comment at the end of file
				if ret.type != 'space' and ret.type != 'comment' and ret.type != 'inlinecomm':
					tokens.append(ret)
			else:
				break

		if err < 0: # error
			return True, ret
		else:
			return False, tokens


	# err < 0 on error
	# err = 0 on EOF
	# err > 0 on success (err = number of characters read)
	def next_token(self, file: 'fileobj') -> ('err: int', 'lexerError/token'):
		state = 0
		curstr = ''
		c = self.lastchr
		if c == '':
			return 0, None
		while c:
			newstate = self.transitions[state](curstr, c)
			if newstate == -1: # no possible transitions
				break
			else:
				# do state transition
				state = newstate
				curstr += c
				if c == '\n':
					self.row += 1
					self.col = 0
				else:
					self.col += 1

				c = file.read(1)
				# treat "\\\n" as empty string
				# need 1 character lookahead
				if c == '\\':
					file_pos = file.tell() 
					nextchr = file.read(1)
					if nextchr == '\n':
						c = file.read(1)
					else:
						file.seek(file_pos)

				self.lastchr = c


		if self.accept[state]:
			return len(curstr), self.state2token(state, curstr)
		else:
			return -1, lexerError(self.row, self.col, self.errmsg(state, c))# TODO: fill in the error type
	
	def state2token(self, state: int, value: str):
		# check if an identifier is actually a keyword
		if state == 2 and value in self.keywords:
			state = 1 
		return token(self.states[state], value)

	def transition_empty(self, curstr: str, c: 'char') -> int:
		if isletter(c) or c == '_': #id
			return 2
		elif isop(c): # op
			return 3
		elif isnumber(c): # intlit
			return 4
		elif c == '"': # instrlit
			return 7
		elif c == "'": # inchrlit
			return 8
		elif ispunc(c): # punc
			return 9
		elif isspace(c): # space
			return 10
		return -1

	def transition_id(self, curstr: str, c: 'char') -> int:
		if isletter(c) or isnumber(c) or c == '_':
			return 2
		return -1

	def transition_op(self, curstr: str, c: 'char') -> int:
		if isop(c):
			newstr = curstr + c
			if newstr in self.ops:
				return 3
			elif newstr == '//':
				return 11 # inlinecomm
			elif newstr == '/*':
				return 12 # inblkcomm
		return -1

	def transition_intlit(self, curstr: str, c: 'char') -> int:
		if isnumber(c):
			return 4
		return -1

	def transition_strlit(self, curstr: str, c: 'char') -> int:
		return -1

	def transition_chrlit(self, curstr: str, c: 'char') -> int:
		return -1

	def transition_instrlit(self, curstr: str, c: 'char') -> int:
		if c == '"':
			return 5 # strlit
		elif c == '\n':
			return 14 # unclosed strlit
		return 7 # still inside of double quotes

	def transition_inchrlit(self, curstr: str, c: 'char') -> int:
		if c == "'":
			return 6 # chrlit
		elif c == '\n':
			return 15 # unclosed chrlit
		return 8 # still inside of single quotes

	def transition_punc(self, curstr: str, c: 'char') -> int:
		return -1

	def transition_space(self, curstr: str, c: 'char') -> int:
		if c in " \t\n":
			return 10
		return -1

	def transition_inlinecomm(self, curstr: str, c: 'char') -> int:
		if c == '\n':
			return 13
		return 11

	def transition_inblkcomm(self, curstr: str, c: 'char') -> int:
		if c == '/' and curstr[-1] == '*' and len(curstr) >= 3: # handle the case /*/
			return 13
		return 12

	def transition_comment(self, curstr: str, c: 'char') -> int:
		return -1

	def transition_unclosed_str(self, curstr: str, c: 'char') -> int:
		return -1

	def transition_unclosed_chr(self, curstr: str, c: 'char') -> int:
		return -1

	def errmsg(self, state: int, c: "char") -> str:
		if state == 0:
			return f"unrecognized character {c}"
		elif state == 7 or state == 14:
			return 'unmatched double quote'
		elif state == 8 or state == 15:
			return 'unmatched single quote'
		elif state == 12:
			return 'unmatched block comment'

if __name__ == '__main__':
	import sys
	if len(sys.argv) != 2:
		print('usage: lexer.py sourcefile')
	else:
		file = open(sys.argv[1])
		l = lexer()
		err, ret = l.run(file)
		if err:
			print(ret)
		else:
			for t in ret:
				print(t)
		file.close()
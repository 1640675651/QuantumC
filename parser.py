from lexer import token, lexer

def istype(t: token) -> bool:
	types = ['bit', 'int4', 'int8', 'int16', 'int32', 'char', 'void']
	return t.type == 'kw' and t.value in types

def isselfop(t: token) -> bool:
	return t.type == 'op' and (t.value == '++' or t.value == '--')

def isassignop(t: token) -> bool:
	assignops = {'=', '+=', '-=', '*=', '/=', '%='\
				'&=', '|=', '~=', '^=', '<<=', '>>=',
				'&&=', '||='}
	return t.type == 'op' and t.value in assignops

def isjmp(t: token) -> bool:
	jmpops = ['break', 'continue', 'return']
	return t.type == 'kw' and t.value in jmpops

# find consistent pairing structure (like parentheses) nearest to the right of starting index s
# return the index of the last closing token
def pairmatch(buf: [token], s: int, t1: str, t2: str) -> int:
	stack = 0
	for i in range(s, len(buf), 1):
		if buf[i].value == t1:
			stack += 1
		elif buf[i].value == t2:
			stack -= 1
			if stack == 0:
				return i
	return -1

def findnext(buf: [token], s: int, t: str) -> int:
	for i in range(s, len(buf), 1):
		if buf[i].value == t:
			return i
	return -1

class parserError():
	def __init__(self, row: int, col: int, info: str):
		self.row = row
		self.col = col
		self.info = info
	def __str__(self):
		return "Syntax error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info


class ptnode(): # parse tree node
	def __init__(self, name: 'str', buf: ['token']):
		self.name = name
		self.buf = buf
		#self.isterminal = isterminal
		self.children = []
		# can mark buf start and end index [start, end)
		# to avoid copying buf when expanding
		# self.bufstart = bufstart
		# self.bufend = bufend
	def expand(self):
		pass

	def __str__(self):
		return self.name

def nextdecl(buf) -> ('parsed len', ptnode):
	# a declaration contains at least 3 tokens
	if len(buf) < 3:
		return -1, parserError(buf[0].row, buf[0].col, "incomplete declaration")
	if not istype(buf[0]):
		return -1, parserError(buf[0].row, buf[0].col, "declaration should start with type but got " + buf[0].value)
	if not buf[1].type == 'id':
		return -1, parserError(buf[1].row, buf[1].col, buf[1].value + "is not an indentifier")
	
	# 3 tokens lookahead
	# use buf[2] to determine the type of this DECL
	if buf[2].value == ';':
		return 3, VARDECL_node(buf[:3])
	elif buf[2].value == '=': # VARDECL VARINIT
		# need to find the next ;
		end = -1
		for i in range(3, len(buf), 1):
			if buf[i].value == ';':
				end = i+1
				break
		if end == -1:
			return -1, parserError(buf[2].row, buf[2].col, "missing ;")
		return end, VARDECL_node(buf[:end])

	elif buf[2].value == '[': # ARRDECL
		# need to find the next ;
		end = -1
		for i in range(3, len(buf), 1):
			if buf[i].value == ';':
				end = i+1
				break
		if end == -1:
			return -1, parserError(buf[2].row, buf[2].col, "missing ;")
		return end, ARRDECL_node(buf[:end])

	elif buf[2].value == '(': # FUNCDECL
		# need to find the closing }
		# first find the opening {
		start = -1
		for i in range(3, len(buf), 1):
			if buf[i].value == '{':
				start = i
				break
		if start == -1:
			return -1, parserError(buf[2].row, buf[2].col, "missing { for function body")

		end = -1
		stack = 1
		for i in range(start+1, len(buf), 1):
			if buf[i].value == '{':
				stack += 1
			elif buf[i].value == '}':
				stack -= 1
				if stack == 0:
					end = i+1
					break
		if end == -1:
			return -1, parserError(buf[start].row, buf[start].col, "unclosed {")
		return end, FUNCDECL_node(buf[:end])
	return -1, parserError(buf[2].row, buf[2].col, f"unexpected token {buf[2].value} in declaration")

class S_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('S', buf)

	# rule: S -> DECLLIST
	def expand(self):
		newnode = DECLLIST_node(self.buf)
		self.children.append(newnode)

class DECLLIST_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('DECLLIST', buf)

	# rules: DECLLIST -> DECL DECLLIST | epsilon
	# DECL -> VARDECL | ARRDECL | FUNCDECL
	# VARDECL -> TYPE id VARINIT ;
	# ARRDECL -> TYPE id ARRDIM ARRINIT ;
	# FUNCDECL -> TYPE id (PARAMLIST) {STMTLIST}
	def expand(self):
		while len(self.buf):
			plen, newnode = nextdecl(self.buf)
			self.children.append(newnode)
			if plen == -1: # error, stop expanding				
				break
			else:
				self.buf = self.buf[plen:]

class VARDECL_node(ptnode):
	# buf will look like TYPE id ; or TYPE id = ... ;
	def __init__(self, buf: ['token']):
		super().__init__('VARDECL', buf)

	# rules: VARDECL -> TYPE id VARINIT
	# VARINIT -> EXPR | epsilon
	# can combine the rules:
	# VARINIT -> TYPE id ; | TYPE id = EXPR ;
	def expand(self):
		# TYPE, id, and ; are checked by the DECLLIST expansion
		# just add the terminals to children
		self.children.append(self.buf[0]) # TYPE
		self.children.append(self.buf[1]) # id
		if len(self.buf) == 3: # no VARINIT
			self.children.append(self.buf[2]) # ;
			self.buf = [] # clear buf to save memory
			return
		if self.buf[2].value == '=': # has VARINIT
			self.children.append(self.buf[2]) # =
			self.children.append(EXPR_node(self.buf[3:-1]))
			self.children.append(self.buf[-1]) # ;
			self.buf = []
		else: # expected = to init a variable
			self.children.append(parserError(self.buf[2].row, self.buf[2].col, "expect '=' for variable initialization"))

class ARRDECL_node(ptnode):
	# buf will look likd TYPE id [ ... ;
	def __init__(self, buf: ['token']):
		super().__init__('ARRDECL', buf)
	
	def expand(self):
		pass # TODO

class FUNCDECL_node(ptnode):
	# buf will look like TYPE id ( ... {...}
	def __init__(self, buf: ['token']):
		super().__init__('FUNCDECL', buf)
	
	# rule: FUNCDECL -> TYPE id (PARAMLIST) {STMTLIST}
	def expand(self):
		# TYPE, id, and ; are checked by the DECLLIST expansion
		# just add the terminals to children
		self.children.append(self.buf[0]) # TYPE
		self.children.append(self.buf[1]) # id

		# the token immediately after id should be (
		if self.buf[2].value != '(':
			self.children.append(parserError(self.buf[2].row, self.buf[2].col, "expected '(' for function declaration"))
			return
		# find param list in ()
		end = pairmatch(self.buf, 2, '(', ')')
		if end == -1:
			self.children.append(parserError(self.buf[2].row, self.buf[2].col, "unclosed '(' "))
			return
		self.children.append(self.buf[2]) # (
		self.children.append(PARAMLIST_node(self.buf[3:end])) # PARAMLIST
		self.children.append(self.buf[end]) # )
		
		# the token immediately after ) should be {}
		if end+1 == len(self.buf) or self.buf[end+1].value != '{':
			self.children.append(parseError(self.buf[end].row, self.buf[end].col, "expected '{' for function body"))

		# the expansion of DECLLIST guarantees the buf ends with a consistent pair of {}
		self.children.append(self.buf[end+1]) # {
		self.children.append(STMTLIST_node(self.buf[end+2:-1])) # STMTLIST
		self.children.append(self.buf[-1]) # }
		self.buf = []

class PARAMLIST_node(ptnode):
	# buf can be anything
	def __init__(self, buf: ['token']):
		super().__init__('PARAMLIST', buf)
	
	# rule: PARAMLIST -> TYPE id, PARAMLIST | TYPE id | epsilon
	def expand(self):
		for i in range(0, len(self.buf), 3):
			if not istype(self.buf[i]):
				self.children.append(parserError(self.buf[i].row, self.buf[i].col, 'expect type for parameter'))
				break
			self.children.append(self.buf[i]) # TYPE
			if i+1 >= len(self.buf) or self.buf[i+1].type != 'id':
				self.children.append(parserError(self.buf[i].row, self.buf[i].col, 'expect identifier for parameter'))
			self.children.append(self.buf[i+1]) # id
			if i+2 >= len(self.buf): # end of PARAMLIST
				self.buf = []
				break
			if self.buf[i+2].value != ',':
				self.children.append(parserError(self.buf[i+2].row, self.buf[i+2].col, "expect ',' to split parameters"))
				break
			self.children.append(self.buf[i+2]) # ,

class STMTLIST_node(ptnode):
	# buf can be anything
	def __init__(self, buf: ['token']):
		super().__init__('STMTLIST', buf)
	
	# rules: STMTLIST -> STMT STMTLIST | epsilon
	# STMT -> VARDECL | ARRDECL | CALL | IFELSE | FOR | WHILE | {STMTLIST} | break ; | continue ; | return ; | ;
	def expand(self):
		def nextstmt(buf) -> ('parsed len', ptnode):
			# these statements need to be handled recursively
			if buf[0].type == 'kw':
				if buf[0].value == 'if': # IFELSE
					pass
				if buf[0].value == 'for': # FOR
					pass
				if buf[0].value == 'while': # WHILE
					pass	
			if buf[0].type == 'punc' and buf[0].value == '{': # {STMTLIST} compound statment
				pass
			# otherwise, the statement should end with ;
			nextindex = findnext(self.buf, 0, ';')
			if nextindex == -1:
				return -1, parserError(buf[0].row, buf[0].col, "expect ';' after a statement")
			# classify which statement it is
			if len(buf) == 1: # empty statement ;
				return 1, buf[0]
			if istype(buf[0]): # the first token is TYPE, must be a DECL
				return nextdecl(self.buf)
			if isselfop(buf[0]): # increment or decrement operator ASSIGN
				return nextindex+1, ASSIGN_node(buf[:nextindex+1])
			if buf[0].type == 'id':
				if isassignop(buf[1]) or isselfop(buf[1]): # ASSIGN
					return nextindex+1, ASSIGN_node(buf[:nextindex+1])
				if buf[1].value == '(': # CALL
					return nextindex+1, CALL_node(buf[:nextindex+1])
				print(buf)
				return -1, parserError(buf[1].row, buf[1].col, f"expect operator for identifier {buf[0].value}")
			if isjmp(buf[0]): # break/continue/return
				return len(buf), JMP_node(buf)
			return -1, parserError(buf[0].row, buf[0].col, "expect statement")

		while len(self.buf):
			plen, newnode = nextstmt(self.buf)
			self.children.append(newnode)
			if plen == -1: # error, stop expanding				
				break
			else:
				self.buf = self.buf[plen:]
	
class ASSIGN_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('ASSIGN', buf)

class CALL_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('CALL', buf)

class JMP_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('JMP', buf)

class EXPR_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('EXPR', buf)

class parser():
	def run(self, buf: [token]) -> (parserError, S_node):
		def parse_dfs(node: ptnode) -> parserError:
			#print('dfs expanding ' + str(node))
			node.expand()
			for child in node.children:
				if type(child) == parserError:
					return child
				# only expand non-terminal
				if type(child) == token:
					continue
				err = parse_dfs(child)
				if err != None:
					return err
			return None

		root = S_node(buf[:])# copy buf since it will be cleared
		err = parse_dfs(root)
		return err, root

def print_pt(node, depth: int):
	print('\t'*depth + str(node))
	# do not expand error or terminals
	if type(node) != parserError and type(node) != token:
		for child in node.children:
			print_pt(child, depth+1)

def main():
	import sys
	if len(sys.argv) != 2:
		print('usage: parser.py sourcefile')
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
		print_pt(root, 0)
		if err != None:
			print(err)
		file.close()

if __name__ == '__main__':
	main()

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

class parserError():
	def __init__(self, row: int, col: int, info: str):
		self.row = row
		self.col = col
		self.info = info
	def __str__(self):
		return "Syntax error at row " + str(self.row) + ' col ' + str(self.col) + ": " + self.info

# find consistent pairing structure (like nested parentheses) nearest to the right of starting index s
# return the index of the last closing token
def pairmatch(buf: [token], s: int, t1: str, t2: str) -> int:
	stack = 0
	for i in range(s, len(buf), 1):
		if buf[i].type == 'punc':
			if buf[i].value == t1:
				stack += 1
			elif buf[i].value == t2:
				stack -= 1
				if stack == 0:
					return i
	return -1

def findnext(buf: [token], s: int, t: str) -> int:
	for i in range(s, len(buf), 1):
		if buf[i].type == 'punc' and buf[i].value == t:
			return i
	return -1

# find the next token not within any nested structure
# returns (-1, parserError) if finding unclosed nested structure
# returns (len(buf), None) if not finding any token
def findnext_unnested(buf: [token], s: int, t: str) -> (int, parserError):
	parens = {'(':')', '[':']', '{':'}'}
	end = s
	while end < len(buf) and not (buf[end].type == 'punc' and buf[end].value == t):
			if buf[end].type == 'punc' and buf[end].value in parens:
				last_end = end
				lparen = buf[end].value
				rparen = parens[lparen]
				end = pairmatch(buf, end, lparen, rparen)
				if end == -1:
					return -1, parserError(buf[last_end].row, buf[last_end].col, f"unclosed '{nest_token}'")
			end += 1
	return end, None

# buf[s] should be [
# return the index of the last ] + 1
def findarrsub(buf: [token], s: int) -> int:
	# find continuous pairs of []
	end = s
	while end < len(buf) and buf[end].type == 'punc' and buf[end].value == '[':
		#closing_index = findnext(buf, end+1, ']')
		closing_index = pairmatch(buf, end, '[' , ']')
		if closing_index == -1:
			return -1
		end = closing_index + 1
	return end

def findtokens(buf: [token], t: str) -> [int]:
	ret = []
	for i in range(len(buf)):
		if buf[i].type == 'punc' and buf[i].value == t:
			ret.append(i)
	return ret

class ptnode(): # parse tree node
	def __init__(self, name: 'str', buf: ['token']):
		self.name = name
		self.buf = buf
		self.children = []
		self.expanded = False
		self.start_row = -1
		self.start_col = -1
		self.end_row = -1
		self.end_col = -1
		self.scope = -1

	def expand(self):
		pass

	def __str__(self):
		return self.name #+ f' {self.start_row}, {self.start_col}, {self.end_row}, {self.end_col}'

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

def nextstmt(buf) -> ('parsed len', ptnode):
	# these statements need to be handled recursively
	if buf[0].type == 'kw':
		if buf[0].value == 'if': # IFELSE
			# rule: IFELSE -> if (EXPR) STMT | if (EXPR) STMT else STMT
			# 1. find if condition in parentheses
			if len(buf) < 2 or buf[1].value != '(':
				return -1, parserError(buf[0].row, buf[0].col, "the for/while loop needs condition")
			cond_end = pairmatch(buf, 1, '(', ')')
			if cond_end == -1:
				return -1, parserError(buf[1].row, buf[1].col, "unmatched '('")
			# 2. find the statement immediately after the if condition (recursive call)
			plen, newnode = nextstmt(buf[cond_end+1:])
			if plen == -1:
				return -1, newnode
			tot_len = cond_end + 1 + plen
			# 3. check whether else exists
			if tot_len < len(buf) and buf[tot_len].type == 'kw' and buf[tot_len].value == 'else':
				# find the statement immediately after the else (recursive call)
				tot_len += 1 # kw else
				plen, newnode = nextstmt(buf[tot_len:])
				if plen == -1:
					return -1, newnode
				tot_len += plen
			return tot_len, IFELSE_node(buf[:tot_len])

		if buf[0].value == 'for' or buf[0].value == 'while': # FOR/WHILE
			# rules: FOR -> for (FOREXPR) STMT
			# WHILE -> while (EXPR) STMT
			# 1. find for/while condition in parentheses
			if len(buf) < 2 or buf[1].value != '(':
				return -1, parserError(buf[0].row, buf[0].col, "the for/while loop needs condition")
			cond_end = pairmatch(buf, 1, '(', ')')
			if cond_end == -1:
				return -1, parserError(buf[1].row, buf[1].col, "unmatched '('")
			# 2. find the statement immediately after the for condition (recursive call)
			plen, newnode = nextstmt(buf[cond_end+1:])
			if plen == -1:
				return -1, newnode
			tot_len = cond_end + 1 + plen
			if buf[0].value == 'for':
				return tot_len, FOR_node(buf[:tot_len])
			else:
				return tot_len, WHILE_node(buf[:tot_len])

	if buf[0].type == 'punc' and buf[0].value == '{': # {STMTLIST} compound statment
		closing_index = pairmatch(buf, 0, '{', '}')
		if closing_index == -1:
			return parserError(buf[0].row, buf[0].col, "unclosed '{'")
		return closing_index+1, CPDSTMT_node(buf[:closing_index+1])

	# otherwise, the statement should end with ;
	nextindex = findnext(buf, 0, ';')
	if nextindex == -1:
		return -1, parserError(buf[0].row, buf[0].col, "expect ';' after a statement")
	# classify which statement it is
	if len(buf) == 1: # empty statement ;
		return 1, buf[0]
	if istype(buf[0]): # DECL
		return nextdecl(buf)
	if isjmp(buf[0]): # JMP
		return nextindex+1, JMP_node(buf[:nextindex+1])
	return nextindex+1, EXPRSTMT_node(buf[:nextindex+1])

def nextinit(buf) -> ('parsed len', ptnode):
	# ARRLIT
	if buf[0].type == 'punc' and buf[0].value == '{':
		end = pairmatch(buf, 0, '{', '}')
		if end == -1:
			return -1, parserError(buf[0].row, buf[0].col, "unclosed '{'")
		return end+1, ARRLIT_node(buf[:end+1])
	# EXPR, advance to the next comma not within any nested structure
	end, err = findnext_unnested(buf, 0, ',')
	# unclosed nested structure
	if end == -1:
		return -1, err
	# the first token should not be comma
	if end == 0:
		return -1, parserError(buf[0].row, buf[0].col, "expect initializer")
	return end, EXPR_node(buf[:end]) # not including comma

class S_node(ptnode):
	def __init__(self, buf: ['token']):
		super().__init__('S', buf)

	# rule: S -> DECLLIST
	def expand(self):
		newnode = DECLLIST_node(self.buf)
		self.children.append(newnode)
		self.expanded = True
		self.buf = []

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
		self.expanded = True

class VARDECL_node(ptnode):
	# buf will look like TYPE id ; or TYPE id = ... ;
	def __init__(self, buf: ['token']):
		super().__init__('VARDECL', buf)

	# rules: VARDECL -> TYPE id VARINIT
	# VARINIT -> = EXPR | epsilon
	# can combine the rules:
	# VARINIT -> TYPE id ; | TYPE id = EXPR ;
	def expand(self):
		self.expanded = True
		# TYPE, id, and ; are checked by the DECLLIST expansion
		# just add the terminals to children
		self.children.append(self.buf[0]) # TYPE
		self.children.append(self.buf[1]) # id
		if len(self.buf) == 3: # no VARINIT
			#self.children.append(self.buf[2]) # ;
			self.buf = [] # clear buf to save memory
			return
		if self.buf[2].type == 'op' and self.buf[2].value == '=': # has VARINIT
			#self.children.append(self.buf[2]) # =
			if len(self.buf) < 5:
				self.children.append(parserError(self.buf[2].row, self.buf[2].col, "expect expression"))
			else:
				self.children.append(EXPR_node(self.buf[3:-1]))
			#self.children.append(self.buf[-1]) # ;
			self.buf = []
		else: # expected = to init a variable
			self.children.append(parserError(self.buf[2].row, self.buf[2].col, "expect '=' for variable initialization"))

class ARRDECL_node(ptnode):
	# buf will look likd TYPE id [ ... ;
	def __init__(self, buf: ['token']):
		super().__init__('ARRDECL', buf)
	
	# rule: ARRDECL -> TYPE id ARRDIM ; | TYPE id ARRDIM = ARRLIT ;
	def expand(self):
		self.expanded = True
		self.children.append(self.buf[0]) # TYPE
		self.children.append(self.buf[1]) # id
		closing_index = findarrsub(self.buf, 2)
		if closing_index == -1:
			self.children.append(parserError(self.buf[2].row, self.buf[2].col, "unclosed '['"))
			return 
		self.children.append(ARRDIM_node(self.buf[2:closing_index])) # ARRDIM
		
		# no array initializer
		if closing_index == len(self.buf) - 1:
			#self.children.append(self.buf[-1]) # ;
			self.buf = []
			return
		# has = after array dimension
		if self.buf[closing_index].type == 'op' and self.buf[closing_index].value == '=':
			#self.children.append(self.buf[closing_index]) # =
			# nothing after =
			if closing_index == len(self.buf) - 2:
				self.children.append(parserError(self.buf[closing_index].row, self.buf[closing_index].col, "expect array initializer"))
				return
			# has initializer
			self.children.append(ARRLIT_node(self.buf[closing_index+1:-1])) # ARRLIT
			#self.children.append(self.buf[-1]) # ;
			self.buf = []
			return
		else:
			self.children.append(parserError(self.buf[closing_index].row, self.buf[closing_index].col, "expect '=' for array initializer"))
			return

class ARRDIM_node(ptnode):
	# buf will look like arbitrary number of [ ... ]
	def __init__(self, buf: [token]):
		super().__init__('ARRDIM', buf)
	
	# rule: ARRDIM -> [ EXPR ] ARRDIM | [ ] ARRDIM | [ EXPR ] | [ ]
	# not allowing empty dimension for now
	def expand(self): 
		self.expanded = True
		left = 0
		right = 0
		while right < len(self.buf) - 1:
			right = findnext(self.buf, left, ']')
			#self.children.append(self.buf[left]) # [
			if right > left + 1: 
				self.children.append(EXPR_node(self.buf[left+1:right])) # EXPR
			#self.children.append(self.buf[right]) # ]
			left = right + 1
		self.buf = []

class ARRLIT_node(ptnode):
	# buf can look like anything non empty
	def __init__(self, buf: [token]):
		super().__init__('ARRLIT', buf)

	# rule: ARRLIT -> { } | { INITLIST }
	def expand(self): 
		self.expanded = True
		if not (self.buf[0].type == 'punc' and self.buf[0].value == '{'):
			self.children.append(self.buf[0].row, self.buf[0].col, "expect '{' for array initializer")
			return
		#self.children.append(self.buf[0]) # {
		if not (self.buf[-1].type == 'punc' and self.buf[-1].value == '}'):
			self.children.append(parserError(self.buf[-1].row, self.buf[-1].col, "expect '}' for array initializer"))
			return
		if len(self.buf) > 2:
			self.children.append(INITLIST_node(self.buf[1:-1])) # INITLIST
		#self.children.append(self.buf[-1]) # }
		self.buf = []

class INITLIST_node(ptnode):
	# buf can look like anything non empty
	def __init__(self, buf: [token]):
		super().__init__('INITLIST', buf)

	# rules: INITLIST -> INIT , INITLIST | epsilon
	# INIT -> EXPR | ARRLIT
	def expand(self):
		self.expanded = True
		while len(self.buf) > 0:
			plen, newnode = nextinit(self.buf)
			self.children.append(newnode)
			if plen == -1:
				return
			#if plen < len(self.buf):
			#	self.children.append(self.buf[plen]) # ,
			self.buf = self.buf[plen+1:]
		self.buf = []
	
class FUNCDECL_node(ptnode):
	# buf will look like TYPE id ( ... {...}
	def __init__(self, buf: [token]):
		super().__init__('FUNCDECL', buf)
	
	# rule: FUNCDECL -> TYPE id (PARAMLIST) {STMTLIST}
	def expand(self):
		self.expanded = True
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
		#self.children.append(self.buf[2]) # (
		self.children.append(PARAMLIST_node(self.buf[3:end])) # PARAMLIST
		#self.children.append(self.buf[end]) # )
		
		# the token immediately after ) should be {}
		if end+1 == len(self.buf) or self.buf[end+1].value != '{':
			self.children.append(parseError(self.buf[end].row, self.buf[end].col, "expected '{' for function body"))

		# the expansion of DECLLIST guarantees the buf ends with a consistent pair of {}
		#self.children.append(self.buf[end+1]) # {
		self.children.append(STMTLIST_node(self.buf[end+2:-1])) # STMTLIST
		#self.children.append(self.buf[-1]) # }
		self.buf = []

class PARAMLIST_node(ptnode):
	# buf can be anything
	def __init__(self, buf: ['token']):
		super().__init__('PARAMLIST', buf)
	
	# rule: PARAMLIST -> TYPE id, PARAMLIST | TYPE id | epsilon
	def expand(self):
		self.expanded = True
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
			#self.children.append(self.buf[i+2]) # ,
		self.buf = []

class STMTLIST_node(ptnode):
	# buf can be anything
	def __init__(self, buf: ['token']):
		super().__init__('STMTLIST', buf)
	
	# rules: STMTLIST -> STMT STMTLIST | epsilon
	# STMT -> VARDECL | ARRDECL | IFELSE | FOR | WHILE | CPDSTMT | EXPR ; | JMP ; | ;
	# CPDSTMT -> { STMTLIST }
	# JMP -> break; | continue ; | RETURN
	# RETURN -> return ; | return EXPR ;
	def expand(self):
		self.expanded = True
		while len(self.buf):
			plen, newnode = nextstmt(self.buf)
			self.children.append(newnode)
			if plen == -1: # error, stop expanding				
				break
			else:
				self.buf = self.buf[plen:]

class JMP_node(ptnode):
	# buf will look like break ;
	# or continue ;
	# or return ... ;
	def __init__(self, buf: ['token']):
		super().__init__('JMP', buf)

	# rules: JMP -> break ; | continue ; | return EXPR ;
	def expand(self):
		self.expanded = True
		self.children.append(self.buf[0]) # break/continue/return
		if len(self.buf) > 2:
			self.children.append(EXPR_node(self.buf[1:-1])) # EXPR
		#self.children.append(self.buf[-1]) # ;
		self.buf = []

class EXPRSTMT_node(ptnode):
	# buf will look like ... ;
	def __init__(self, buf: ['token']):
		super().__init__('EXPRSTMT', buf)
	
	# rule: EXPRSTMT -> EXPR ;
	def expand(self):
		self.expanded = True
		if len(self.buf) <= 1:
			self.children.append(parserError(self.buf[0].row, self.buf[1].col, "expect expression"))
		else:
			self.children.append(EXPR_node(self.buf[:-1])) # EXPR 
			#self.children.append(self.buf[-1]) # ;
			self.buf = []

class IFELSE_node(ptnode):
	# buf will look like if ( ... ) STMT1
	# or if ( ... ) STMT1 else STMT2
	def __init__(self, buf: ['token']):
		super().__init__('IFELSE', buf)
	
	def expand(self):
		self.expanded = True
		#self.children.append(self.buf[0]) # if
		#self.children.append(self.buf[1]) # (
		cond_end = pairmatch(self.buf, 1, '(', ')') 
		if cond_end <= 2: # empty EXPR
			self.children.append(parserError(self.buf[1].row, self.buf[1].col, "expect expression"))
		else:
			self.children.append(EXPR_node(self.buf[2:cond_end])) # EXPR
		#self.children.append(self.buf[cond_end]) # )
		plen, stmt = nextstmt(self.buf[cond_end+1:])
		self.children.append(stmt) # STMT1

		plen = cond_end + 1 + plen
		if plen < len(self.buf):
			#self.children.append(self.buf[plen])# else
			plen1, stmt = nextstmt(self.buf[plen+1:])
			self.children.append(stmt)
		self.buf = []

class FOR_node(ptnode):
	# buf will look like for ( ... ) STMT
	def __init__(self, buf: ['token']):
		super().__init__('FOR', buf)
	
	# rule: FOR -> for ( FOREXPR ) STMT
	def expand(self):
		self.expanded = True
		#self.children.append(self.buf[0]) # for
		#self.children.append(self.buf[1]) # (
		cond_end = pairmatch(self.buf, 1, '(', ')') 
		if cond_end <= 2: # empty FOREXPR
			self.children.append(parserError(self.buf[1].row, self.buf[1].col, "expect for loop expression"))
		else:
			self.children.append(FOREXPR_node(self.buf[2:cond_end])) # FOREXPR
		#self.children.append(self.buf[cond_end]) # )
		plen, stmt = nextstmt(self.buf[cond_end+1:])
		self.children.append(stmt) # STMT
		self.buf = []

class FOREXPR_node(ptnode):
	# buf can be anything non empty
	def __init__(self, buf: ['token']):
		super().__init__('FOREXPR', buf)
	
	# rule: FOREXPR -> FORSUBEXPR ; FORSUBEXPR ; FORSUBEXPR
	def expand(self):
		self.expanded = True 
		semicol_indices = findtokens(self.buf, ';')
		if len(semicol_indices) < 2:
			self.children.append(parserError(self.buf[-1].row, self.buf[-1].col, "expect ';' in for statement"))
			return
		if len(semicol_indices) > 2:
			i = semicol_indices[2]
			self.children.append(parserError(self.buf[i].row, self.buf[i].col, "unexpected ';' in for statement"))
			return

		left = 0
		for i in semicol_indices:
			self.children.append(FORSUBEXPR_node(self.buf[left:i])) # FORSUBEXPR
			#self.children.append(self.buf[i]) # ;
			left = i+1
		self.children.append(FORSUBEXPR_node(self.buf[left:])) # FORSUBEXPR
		self.buf = []

class FORSUBEXPR_node(ptnode):
	# buf can be anything including empty list
	def __init__(self, buf: [token]):
		super().__init__('FORSUBEXPR', buf)
	
	# rule: FORSUBEXPR -> EXPR | epsilon
	def expand(self):
		self.expanded = True
		if len(self.buf) == 0:
			return
		self.children.append(EXPR_node(self.buf[:]))
		self.buf = []

class WHILE_node(ptnode):
	# buf will look like while ( ... ) STMT
	def __init__(self, buf: [token]):
		super().__init__('WHILE', buf)

	# rule: WHILE -> while ( EXPR ) STMT
	def expand(self):
		self.expanded = True
		#self.children.append(self.buf[0]) # while
		#self.children.append(self.buf[1]) # (
		cond_end = pairmatch(self.buf, 1, '(', ')') 
		if cond_end <= 2: # empty EXPR
			self.children.append(parserError(self.buf[1].row, self.buf[1].col, "expect expression"))
		else:
			self.children.append(EXPR_node(self.buf[2:cond_end])) # EXPR
		#self.children.append(self.buf[cond_end]) # )
		plen, stmt = nextstmt(self.buf[cond_end+1:])
		self.children.append(stmt) # STMT
		self.buf = []

class CPDSTMT_node(ptnode):
	# buf will look like { ... }
	def __init__(self, buf: ['token']):
		super().__init__('CPDSTMT', buf)
	
	# rule: CPDSTMT -> { STMTLIST }
	def expand(self):
		self.expanded = True
		#self.children.append(self.buf[0]) # {
		self.children.append(STMTLIST_node(self.buf[1:-1])) # STMTLIST
		#self.children.append(self.buf[-1]) # }
		self.buf = []

class EXPR_node(ptnode):
	unaryop = {'++', '--', '+', '-', '!', '~'}
	postfix_unaryop = {'++', '--'}
	precedence_table = {'=': 0, '+=': 0, '-=': 0, '*=': 0, '/=': 0, '%=': 0, '<<=': 0, '>>=': 0, '&=': 0, '^=': 0, '|=': 0,\
						'||': 1, '&&': 2, '|': 3, '^': 4, '&': 5,\
						'==': 6, '!=': 6, '<': 7, '<=': 7, '>': 7, '>=': 7,\
						'<<': 8, '>>': 8,\
						'+': 9, '-': 9, '*': 10, '/': 10, '%': 10}
	assoc_table = {'=': 'r', '+=': 'r', '-=': 'r', '*=': 'r', '/=': 'r', '%=': 'r', '<<=': 'r', '>>=': 'r', '&=': 'r', '^=': 'r', '|=': 'r',\
						'||': 'l', '&&': 'l', '|': 'l', '^': 'l', '&': 'l',\
						'==': 'l', '!=': 'l', '<': 'l', '<=': 'l', '>': 'l', '>=': 'l',\
						'<<': 'l', '>>': 'l',\
						'+': 'l', '-': 'l', '*': 'l', '/': 'l', '%': 'l'}

	def __init__(self, buf: ['token']):
		super().__init__('EXPR', buf)
		self.size = -1
	
	# rules: EXPR -> PRIMARY | UNARY | BINARY
	# PRIMARY -> literal | ACCESS | CALLEXPR | CPDEXPR
	# CPDEXPR -> ( EXPR )
	# UNARY -> unaryop EXPR | EXPR unaryop
	# BINARY -> EXPR binaryop EXPR
	def expand(self): 
		# precedence climbing
		def climb(precedence: int, s: int, buf: [token]) -> ('next index', EXPR_node):
			# peek the first token, if is an operator, it should be a prefix unary operator
			if buf[s].type == 'op':
				op = buf[s]
				if op.value in unary:
					s += 1
					# all prefix unary operators are right-associative
					new_precedence = precedence_table[op]
					s, rightnode = climb(precedence, s, buf)
					node = UNARY_node(op, rightnode)
					return s, node
				else:
					return -1, parserError(buf[s].row, buf[s].col, f"'{buf[s].value} cannot be an unary operator'")

			# otherwise it should be a primary
			s, leftnode = parse_primary(s, buf)
			if s == -1:
				return s, leftnode
			while s < len(buf):
				# an operator must follow an EXPR
				# if two primaries are adjacent, there's an error
				op = buf[s]
				if op.type != 'op':
					return -1, parserError(op.row, op.col, 'expect operator')

				# check postfix unary operator
				# since postfix unary operator has highest precedence, we just need to check continuous ++ and --
				# postfix unary operators have left associativity
				while s < len(buf) and buf[s].type == 'op' and buf[s].value in self.postfix_unaryop:
					leftnode = UNARY_node(leftnode, buf[s])
					s += 1
				
				# check binary operator
				if s >= len(buf):
					break
				op = buf[s]
				if op.type != 'op':
					return -1, parserError(op.row, op.col, "expect binary operator")

				# stop if the next operator has lower precedence than the current level
				# that operator should be parse by a lower precedence climb call
				if self.precedence_table[op.value] < precedence:
					break

				# we have an operator has precedence >= current level
				s += 1
				if s >= len(buf):
					return -1, parserError(buf[-1].row, buf[-1].col, "expect expression")
				new_precedence = self.precedence_table[op.value]
				if self.assoc_table[op.value] == 'l':
					new_precedence += 1
				s, rightnode = climb(new_precedence, s, buf)
				newnode = BINARY_node(leftnode, op, rightnode)
				leftnode = newnode
				if s == -1:
					return s, newnode
			return s, leftnode

		# ensure len(buf) > 0 when calling this
		def parse_primary(s: int, buf: [token]) -> ('next index', 'PRIMARY_node'):
			if s >= len(buf):
				return -1, parserError(buf[-1].row, buf[-1].col, "expect expression")
			# literal
			if buf[s].type == 'intlit' or buf[s].type == 'chrlit' or buf[s].type == 'strlit':
				return s+1, buf[s]
			# CPDEXPR
			if buf[s].type == 'punc' and buf[s].value == '(':
				closing_index = pairmatch(buf, s, '(', ')')
				if closing_index == -1:
					return -1, parserError(buf[s].row, buf[s].col, "unclosed '('")
				newnode = CPDEXPR_node(buf[s:closing_index+1])
				newnode.expand()
				return closing_index+1, newnode
			if buf[s].type == 'id':
			# ACCESS
				# variable access
				if s == len(buf) - 1:
					newnode = ACCESS_node(buf[s:s+1])
					newnode.expand()
					return s+1, newnode
				# array/bit access
				end = s+1
				if buf[end].type == 'punc' and buf[end].value == '[':
					# find continuous pairs of []
					end = findarrsub(buf, end)
					if end == -1:
						return -1, parserError(buf[end].row, buf[end].col, "unclosed '['")
					newnode = ACCESS_node(buf[s:end])
					newnode.expand()
					return end, newnode
			# CALLEXPR
				elif buf[end].type == 'punc' and buf[end].value == '(':
					# find consistent pairs of ()
					end = pairmatch(buf, end, '(', ')')
					if end == -1:
						return -1, parserError(buf[end].row, buf[end].col, "unclosed '(")
					end += 1
					newnode = CALLEXPR_node(buf[s:end])
					return end, newnode
			# ACCESS
				else:
					newnode = ACCESS_node(buf[s:end])
					newnode.expand()
					return end, newnode
			# error
			return -1, parserError(buf[s].row, buf[s].col, "expect identifier for primary expression")

		self.expanded = True
		ni, node = climb(0, 0, self.buf)
		self.children.append(node)
		self.buf = []

class CPDEXPR_node(ptnode):
	# buf will look like ( ... )
	def __init__(self, buf: ['token']):
		super().__init__('CPDEXPR', buf)
		self.size = -1
	
	def expand(self):
		self.expanded = True
		#self.children.append(self.buf[0]) # (
		if len(self.buf) <= 2: # empty EXPR
			self.children.append(parserError(self.buf[0].row, self.buf[0].col, "expect expression"))
		else:
			newnode = EXPR_node(self.buf[1:-1])
			newnode.expand()
			self.children.append(newnode)# EXPR
			#self.children.append(self.buf[-1]) # )
			self.buf = []

class ACCESS_node(ptnode):
	# buf will look like id with arbitrary pairs of [ ... ]
	def __init__(self, buf: ['token']):
		super().__init__('ACCESS', buf)
		self.size = -1

	# rule: ACCESS -> id | ACCESS [ EXPR ]
	def expand(self):
		self.expanded = True
		self.children.append(self.buf[0]) # id
		left = 1
		right = 1
		while right < len(self.buf) - 1:
			right = pairmatch(self.buf, left, '[', ']')
			#self.children.append(self.buf[left]) # [
			if right - left == 1:
				self.children.append(parserError(self.buf[left].row. self.buf[left].col, "expect expression"))
				return
			self.children.append(EXPR_node(self.buf[left+1:right]))
			#self.children.append(self.buf[right]) # [
			left = right+1

class CALLEXPR_node(ptnode):
	# buf will look like id ( ... )
	def __init__(self, buf: ['token']):
		super().__init__('CALLEXPR', buf)
		self.size = -1

	# rule: CALLEXPR -> id ( ARGLIST )
	def expand(self):
		self.expanded = True
		self.children.append(self.buf[0]) # id
		#self.children.append(self.buf[1]) # (
		self.children.append(ARGLIST_node(self.buf[2:-1])) # ARGLIST
		#self.children.append(self.buf[-1]) # )
		self.buf = []

class ARGLIST_node(ptnode):
	# buf can be anything
	def __init__(self, buf: [token]):
		super().__init__('ARGLIST', buf)

	# rule: ARGLIST -> EXPR , ARGLIST | epsilon
	def expand(self):
		self.expanded = True
		# empty arglist
		if len(self.buf) == 0:
			return
		
		expr_start = 0
		expr_end, err = findnext_unnested(self.buf, expr_start, ',')
		while expr_end < len(self.buf):
			# the first token should not be comma
			if expr_end == expr_start:
				self.children.append(parserError(self.buf[0].row, self.buf[0].col, "expect expression"))
				return
			# unclosed nested structure
			if expr_end == -1:
				self.children.append(err)
				return
			# the last token should not be comma
			if expr_end == len(self.buf) - 1:
				self.children.append(parserError(self.buf[-1].row, self.buf[-1].col, "expect expression"))
				return

			self.children.append(EXPR_node(self.buf[expr_start:expr_end])) # EXPR
			#self.children.append(self.buf[expr_end]) # ,
			expr_start = expr_end + 1
			expr_end, err = findnext_unnested(self.buf, expr_start, ',')
		
		self.children.append(EXPR_node(self.buf[expr_start:]))
		self.buf = []

class UNARY_node(ptnode):
	def __init__(self, left: 'op/EXPR_node', right: 'op/EXPR_node'):
		super().__init__('UNARY', [])
		self.children.append(left)
		self.children.append(right)
		self.expanded = True
		self.size = -1

class BINARY_node(ptnode):
	def __init__(self, left: EXPR_node, op: 'op', right: EXPR_node):
		super().__init__('BINARY', [])
		self.children.append(left)
		self.children.append(op)
		self.children.append(right)
		self.expanded = True
		self.size = -1

class parser():
	def run(self, buf: [token]) -> (parserError, S_node):
		def parse_dfs(node: ptnode) -> parserError:
			# do not further expand EXPR_node recursively, since its expand function is already recursive
			if node.expanded == False:
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

		# get the start/end row/col of each AST node
		# the row/col of a token is its ending position
		# punctuations like } are ignored in AST, so the ending row/col of an AST node may be slightly different
		def get_row_col(node: ptnode):
			for child in node.children:
				if type(child) == token:
					continue
				get_row_col(child)
			if len(node.children) > 0:
				if type(node.children[0]) == token:
					node.start_row = node.children[0].row
					node.start_col = node.children[0].col
				else:
					node.start_row = node.children[0].start_row
					node.start_col = node.children[0].start_col

				if type(node.children[-1]) == token:
					node.end_row = node.children[-1].row
					node.end_col = node.children[-1].col
				else:
					node.end_row = node.children[-1].end_row
					node.end_col = node.children[-1].end_col

		root = S_node(buf)
		err = parse_dfs(root)
		if err == None:
			get_row_col(root)
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

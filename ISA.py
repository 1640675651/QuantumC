from IRgen import instruction, memcell

# single bit operations

def x(b) -> list:
    return [f'x {b};']

def ccx(b1, b2, b3) -> list:
    return [f'ccx {b1}, {b2}, {b3};']

def cx(b1, b2) -> list:
    return [f'cx {b1}, {b2};']

def reset(b) -> list:
    return [f'reset {b};']

# register operations

def measure(q: memcell, c: memcell):
    code = []
    n = q.size
    for i in range(n):
        code.append(f'{c[i]} = measure {q[i]};')
    return code

# c = a | b = ~(~a & ~b), Demorgan's law
def bit_or(a: str, b: str, c: str) -> list:
    return x(a) + x(b) + ccx(a, b, c) + x(c) + x(a) + x(b)

# b = cin ^ a
# this is the result of adding two bits
def xor(cin: str, a: str, b: str) -> list:
    return cx(a, b) + cx(cin, b)

# A NOR B = (~A) & (~B)
# c = a nor b
def nor(a: str, b: str, c: str) -> list:
    return x(a) + x(b) + ccx(a, b, c) + x(a) + x(b)

# bit-wise operations

# c = a & b
def bitwise_and(a, b, c):
    code = []
    n = a.size
    for i in range(n):
        code += ccx(a[i], b[i], c[i])
    return code

def bitwise_not(a):
    code = []
    for i in range(a.size):
        code += x(a[i])
    return code

# c = ~a
def bitwise_not_ex(a, c):
    code = []
    n = a.size
    # copy then negate
    for i in range(n):
        code += cx(a[i], c[i])
        code += x(c[i])
    return x

# A NOR B = (~A) & (~B)
# c = a nor b
def bitwise_nor(a, b, c):
    code = []
    n = a.size
    
    # negate a, b
    code += bitwise_not(a)
    code += bitwise_not(b)
    # (~A) & (~B)
    code += bitwise_and(a, b, c)
    # flip back a, b
    code += bitwise_not(a)
    code += bitwise_not(b)
    return code



# cin, a, b, cout are bits
def carry(cin: str, a: str, b: str, cout: str) -> list:
    return ccx(a, b, cout) + cx(a, b) + ccx(cin, b, cout)

def carry_dg(cin: str, a: str, b: str, cout: str) -> list:
    return ccx(cin, b, cout) + cx(a, b) + ccx(a, b, cout)

# ripple carry adder
# b = a + b
# c is carry register
# c will be 0 after the computation, so no need to reset it
def inst_add(a: memcell, b: memcell, c: memcell) -> str:
    code = []
    n = a.size
    # reset carry
    # for i in range(n):
    #     code += reset(c[i])
    
    # calculate all carry
    for i in range(n-1):
        code += carry(c[i], a[i], b[i], c[i+1])

    # maybe calculate overflow bit, or just drop it
    # code += carry((c.segment, c.offset+n-1), (a.segment, a.offset+n-1), (b.segment, b.offset+n-1), (o.segment, o.offset))

    # calculate second-to-MSB
    code += cx(c[n-1], b[n-1])

    # Invert the carries and calculate the remaining sums.
    for i in range(n-2,-1,-1):
        code += carry_dg(c[i], a[i], b[i], c[i+1])
        code += xor(c[i], a[i], b[i])

    return code

# s = a + b
def inst_add_ex(a, b, s, c) -> str:
    code = []
    n = a.size
    # reset s
    for i in range(n):
        code += reset(s[i])
    # copy b to s
    for i in range(n):
        code += cx(b[i], s[i])
    code += inst_add(a, s, c)
    return code

# b = a - b
# add a to 2's complement of b.
def inst_sub(a, b, c):
    code = []
    n = a.size
    # reset carry
    # for i in range(n):
    #     code += reset(c[i])
    
    # create b's 2's complement
    # 1) negate b
    code += bitwise_not(b)

    # 2) need to add 1 to b, but using the adder is overkill.
    # just need to add 1 to the carry register, 1 x gate is enough.
    code += x(c[0])


    # calculate all carry
    for i in range(n-1):
        code += carry(c[i], a[i], b[i], c[i+1])

    # maybe calculate overflow bit, or just drop it
    # code += carry((c.segment, c.offset+n-1), (a.segment, a.offset+n-1), (b.segment, b.offset+n-1), (o.segment, o.offset))

    # calculate second-to-MSB
    code += cx(c[n-1], b[n-1])

    # Invert the carries and calculate the remaining sums.
    for i in range(n-2,-1,-1):
        code += carry_dg(c[i], a[i], b[i], c[i+1])
        code += xor(c[i], a[i], b[i])

    # Flip the carry to restore it to zero.
    code += x(c[0])
    return code

# s = a - b
def inst_sub_ex(a, b, s, c) -> str:
    code = []
    n = a.size
    # reset s
    for i in range(n):
        code += reset(s[i])
    # copy b to s
    for i in range(n):
        code += cx(b[i], s[i])
    code += inst_sub(a, s, c)
    return code

# b = a
def copy(a, b) -> str:
    code = []
    # reset b
    for i in range(b.size):
        code += reset(b[i])
    # automatic truncation/extension
    for i in range(min(a.size, b.size)):
        code += cx(a[i], b[i])
    return code

def twos_complement(value: int, bit_width: int):
    if value < 0:
        value = (1 << bit_width) + value
    else:
        value = value & ((1 << bit_width) - 1)
    return value


# a = v(immediate value)
def assign(a: memcell, v: int) -> str:
    code = []
    # reset a
    for i in range(a.size):
        code += reset(a[i])
    
    # truncation happens when converting to 2's complement
    v = twos_complement(v, a.size)

    # use little-endian representation. LSB at low offset.
    bitcnt = 0
    while v:
        if v & 1:
            code += x(a[bitcnt])
        bitcnt += 1
        v >>= 1
    return code




# convert a multi-bit value a to a single bit boolean value b.
# write the result to LSB of b.
# use OR gates to detect 1 in a. need 1 tmp bit
# b = (a1 or a2 or ... an)
def tobool(a, b) -> str:
    code = []
    # reset b
    for i in range(b.size):
        code += reset(b[i])
    
    # if a is 1 bit, just copy the bit to b's LSB.
    if a.size == 1:
        code += cx(a[0], b[0])
        return code
    
    # use tmp_reg[0] as the ancilla.
    # though I can use binary tree like method to parallize the ORs, here I'll just use sequential OR to save qubits.
    
    or_in = 'tmp_reg[0]'
    or_out = b[0]
    # make sure the final result is stored in b[0]. This depends on the parity of size.
    if a.size % 2 == 1:
        or_in = b[0]
        or_out = 'tmp_reg[0]'
    
    code += bit_or(a[0], a[1], or_out)

    for i in range(2, a.size, 1):
        # in each iteration, the role of or_in and or_out are swapped.
        or_in, or_out = or_out, or_in
        code += bit_or(a[i], or_in, or_out)
        # reset or input temp, since next iteration it will be used as or output
        code += reset(or_in)
    
    # tmp_reg[0] will be reset in the end
    return code
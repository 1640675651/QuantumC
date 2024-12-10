from IRgen import instruction, memcell

# 0. quantum gates

def x(b) -> list:
    return [f'x {b};']

def ccx(b1, b2, b3) -> list:
    return [f'ccx {b1}, {b2}, {b3};']

def cx(b1, b2) -> list:
    return [f'cx {b1}, {b2};']

def swap(b1, b2) -> list:
    return [f'swap {b1}, {b2};']

def reset(b) -> list:
    return [f'reset {b};']

# 1. single bit operations (for those with output bit, assume the bit is set to 0)

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

# 2. bit-wise operations (for those with output bits, assume the bits are set to 0)

# c = a & b
def bitwise_and(a, b, c) -> list:
    code = []
    n = a.size
    for i in range(n):
        code += ccx(a[i], b[i], c[i])
    return code

def bitwise_not(a) -> list:
    code = []
    for i in range(a.size):
        code += x(a[i])
    return code

# c = ~a
def bitwise_not_ex(a, c) -> list:
    code = []
    n = a.size
    # copy then negate
    for i in range(n):
        code += cx(a[i], c[i])
        code += x(c[i])
    return x

# c = a ^ b
def bitwise_xor(a, b, c) -> list:
    code = []
    n = a.size
    for i in range(n):
        code += xor(a[i], b[i], c[i])
    return code

# A NOR B = (~A) & (~B)
# c = a nor b
def bitwise_nor(a, b, c) -> list:
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

# a = a << 1
def lshift(a):
    code = []
    for i in range(a.size, 1, -1):
        code += swap(a[i-1], a[i-2])
    return code

# 3. arithmetic operations

# cin, a, b, cout are bits
def carry(cin: str, a: str, b: str, cout: str) -> list:
    return ccx(a, b, cout) + cx(a, b) + ccx(cin, b, cout)

def carry_dg(cin: str, a: str, b: str, cout: str) -> list:
    return ccx(cin, b, cout) + cx(a, b) + ccx(a, b, cout)

# ripple carry adder
# b = a + b
# c is carry register
# c will be 0 after the computation, so no need to reset it
def inst_add(a: memcell, b: memcell, c: memcell) -> list:
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
    code += cx(a[n-1], b[n-1])

    # calculate second-to-MSB
    code += cx(c[n-1], b[n-1])

    # Invert the carries and calculate the remaining sums.
    for i in range(n-2,-1,-1):
        code += carry_dg(c[i], a[i], b[i], c[i+1])
        code += xor(c[i], a[i], b[i])

    return code

# s = a + b
def inst_add_ex(a, b, s, c) -> list:
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
def inst_sub(a, b, c) -> list:
    code = []
    n = a.size
    
    # create b's 2's complement
    # 1) invert b
    code += bitwise_not(b)

    # 2) need to add 1 to b, but using the adder is overkill.
    # just need to add 1 to the carry register, 1 x gate is enough.
    code += x(c[0])


    # calculate all carry
    for i in range(n-1):
        code += carry(c[i], a[i], b[i], c[i+1])

    # maybe calculate overflow bit, or just drop it
    # code += carry((c.segment, c.offset+n-1), (a.segment, a.offset+n-1), (b.segment, b.offset+n-1), (o.segment, o.offset))
    code += cx(a[n-1], b[n-1])
    
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
def inst_sub_ex(a, b, s, c) -> list:
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

# a = a - b
def sub_swap(a, b, c) -> list:
    code = []
    code += bitwise_not(a)
    code += inst_add(b, a, c)
    code += bitwise_not(a)
    return code

# p = p%d
# q = p/d
def div(p, d, q) -> list:
    code = []
    n = p.size//2
    carry_reg = memcell('carry_reg', 0, 2*n)
    for i in range(n, 0, -1):
        code += lshift(p)
        code += sub_swap(p, d, carry_reg)

        code += x(p[2*n-1])
        code += cx(p[2*n-1], q[i-1])
        code += x(p[2*n-1])

        # If |p> is negative, indicated by the (i-1)th bit of |q> being 0, add D back
        # TODO: how to implement controlled add
        # now only work for positive number
        #code += x(q[i-1])
        #code += cadd(q[i-1], d, p)
        #code += x(q[i-1])
    return code

# q = p/d
# need 4*n tmp bits and the carry register
def div_ex(p, d, q) -> list:
    code = []
    n = p.size
    p_copy = memcell('tmp_reg', 0, 2*n)
    d_copy = memcell('tmp_reg', 2*n, 2*n)
    d_upper = memcell('tmp_reg', 3*n, n)
    # copy p to tmp_reg[0:2n]
    code += copy(p, p_copy)
    # copy d to tmp_reg[3n:4n]
    code += copy(d, d_upper)
    # reset d_lower (tmp_reg[2n:3n])
    for i in range(n):
        code += reset(d_copy[i])
    # reset q
    for i in range(n):
        code += reset(q[i])
    # after division, q = p / d.
    code += div(p_copy, d_copy, q)
    return code

# r = p % d
def mod_ex(p, d, r) -> list:
    code = []
    n = p.size
    p_copy = memcell('tmp_reg', 0, 2*n)
    p_upper = memcell('tmp_reg', n, n)
    d_copy = memcell('tmp_reg', 2*n, 2*n)
    d_upper = memcell('tmp_reg', 3*n, n)
    # copy p to tmp_reg[0:2n]
    code += copy(p, p_copy)
    # copy d to tmp_reg[3n:4n]
    code += copy(d, d_upper)
    # reset d_lower (tmp_reg[2n:3n])
    for i in range(n):
        code += reset(d_copy[i])
    # reset r
    for i in range(n):
        code += reset(r[i])
    # after division, p % d is in the upper half of p_copy.
    code += div(p_copy, d_copy, r)
    # copy p_copy's upper half to r
    code += copy(p_upper, r)
    return code

# 4. comparison operations
# c = (a < b)
# a, b, c must have the same size for < > <= >=
def lt(a, b, c) -> list:
    code = []
    n = a.size

    # calculate a-b, store to c
    code += inst_sub_ex(a, b, c, memcell('carry_reg', 0, n))

    # reset c's LSB
    code += reset(c[0])
    # if sign bit = 1, a - b < 0, a < b. sign bit is the return value.
    # copy c's sign bit (MSB) to its LSB. 
    code += cx(c[c.size-1], c[0])

    # reset c except LSB
    for i in range(1, c.size, 1):
        code += reset(c[i])
    
    return code

# c = (a >= b)
# negate the value of lt
def ge(a, b, c) -> list:
    code = []
    code += lt(a, b, c)
    code += x(c[0])
    return code

# c = (a > b)
def gt(a, b, c) -> list:
    code = []
    n = a.size

    # calculate b - a, store to c
    code += inst_sub_ex(b, a, c, memcell('carry_reg', 0, n))

    # reset c's LSB
    code += reset(c[0])
    # if sign bit = 1, b - a < 0, a > b. sign bit is the return value.
    # copy c's sign bit (MSB) to its LSB. 
    code += cx(c[c.size-1], c[0])

    # reset c except LSB
    for i in range(1, c.size, 1):
        code += reset(c[i])
    
    return code

# c = (a <= b)
# negate the value of gt
def le(a, b, c) -> list:
    code = []
    code += gt(a, b, c)
    code += x(c[0])
    return code

# c = (a == b)
# if a == b, a xor b = all 0. 
# if a != b, a xor b contains 1. 
# convert a xor b to bool and negate is the output.
# 2 tmp bit used.
def eq(a, b, c) -> list:
    code = []
    # reset c
    for i in range(c.size):
        code += reset(c[i])

    # c = a xor b
    code += bitwise_xor(a, b, c)

    tmp_reg = memcell('tmp_reg', 0, 2)
    # convert c to boolean, store into tmp_reg[1]
    code += tobool(c, memcell('tmp_reg', 1, 1))

    # negate tmp_reg[1]
    code += x(tmp_reg[1])

    # reset c
    for i in range(c.size):
        code += reset(c[i])

    # store tmp_reg[1] to the LSB of c
    code += cx(tmp_reg[1], c[0])

    return code

# c = (a != b)
# just need to negate the LSB of (a == b)
def ne(a, b, c) -> list:
    code = []
    code += eq(a, b, c)
    code += x(c[0])
    return code

# 5. misc operations

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

def measure(q: memcell, c: memcell):
    code = []
    n = q.size
    for i in range(n):
        code.append(f'{c[i]} = measure {q[i]};')
    return code
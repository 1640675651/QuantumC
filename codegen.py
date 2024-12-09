from IRgen import basicBlock, branchBlock, loopBlock, instruction, memcell
from ISA import *
class codegenerator():
    # convert intermediate instruction to qasm code
    def __init__(self):
        self.indent = '\t'
        self.tmp_reg_usage = 0
        self.carry_reg_usage = 0
        # do I need overflow bit
        # self.overflow_reg_usage = 0
        self.cond_reg_usage = 0

    def inst2qasm(self, inst: instruction) -> list:
        if inst.name == 'add':
            size = inst.operands[0].size
            self.carry_reg_usage = max(self.carry_reg_usage, size)
            return inst_add(inst.operands[0], inst.operands[1], memcell('carry_reg', 0, size))
        elif inst.name == 'add_ex':
            size = inst.operands[0].size
            self.carry_reg_usage = max(self.carry_reg_usage, size)
            return inst_add_ex(inst.operands[0], inst.operands[1], inst.operands[2], memcell('carry_reg', 0, size))
        if inst.name == 'sub':
            size = inst.operands[0].size
            self.carry_reg_usage = max(self.carry_reg_usage, size)
            return inst_sub(inst.operands[0], inst.operands[1], memcell('carry_reg', 0, size))
        elif inst.name == 'sub_ex':
            size = inst.operands[0].size
            self.carry_reg_usage = max(self.carry_reg_usage, size)
            return inst_sub_ex(inst.operands[0], inst.operands[1], inst.operands[2], memcell('carry_reg', 0, size))
        elif inst.name == 'copy':
            return copy(inst.operands[0], inst.operands[1])
        elif inst.name == 'assign':
            return assign(inst.operands[0], inst.operands[1])
        elif inst.name == 'tobool':
            # tobool will use 1 tmp bit
            self.tmp_reg_usage = max(self.tmp_reg_usage, 1)
            return tobool(inst.operands[0], inst.operands[1])
        elif inst.name == 'measure':
            return measure(inst.operands[0], inst.operands[1])

        return []
    
    # convert instruction list to a code block with indentation
    def code_list_to_block(self, insts: [str], depth) -> str:
        code = ''
        for i in insts:
            code += self.indent*depth + i + '\n'
        return code

    def gencode(self, blk: basicBlock, depth: int) -> str:
        def gen_basic(blk: basicBlock, depth: int) -> str:
            code = ''
            for i in blk.instructions:
                code += self.indent*depth + '//' + str(i) + '\n'
                insts = self.inst2qasm(i)
                code += self.code_list_to_block(insts, depth)
            return code

        def gen_branch(blk: branchBlock, depth: int) -> str:
            code = gen_basic(blk.firstblock, depth)
            code += self.indent*depth + 'if(cond_creg == 1)\n'
            code += self.indent*depth + '{\n'
            code += self.gencode(blk.thenblock, depth+1)
            code += self.indent*depth + '}\n'
            if blk.elseblock != None:
                code += self.indent*depth + 'else\n'
                code += self.indent*depth + '{\n'
                code += self.gencode(blk.elseblock, depth+1)
                code += self.indent*depth + '}\n'
            return code

        def gen_loop(blk: loopBlock, depth: int) -> str:
            code = gen_basic(blk.firstblock, depth)
            code += self.indent*depth + 'while(cond_creg == 1)\n'
            code += self.indent*depth + '{\n'
            code += self.gencode(blk.bodyblock, depth+1) + '\n' # add \n to denote body block and last block
            code += self.gencode(blk.lastblock, depth+1)
            code += self.indent*depth + '}\n'
            return code

        code = ''
        while blk != None:
            if type(blk) == basicBlock:
                code += gen_basic(blk, depth)
            if type(blk) == branchBlock:
                code += '\n' + gen_branch(blk, depth) # add \n to denote the start of a branch
                self.cond_reg_usage = 1
            if type(blk) == loopBlock:
                code += '\n' + gen_loop(blk, depth) # add \n to denote the start of a loop
                self.cond_reg_usage = 1
            blk = blk.next
        return code

    # generate register definition
    def gen_regdef(self, data_len: int, stack_len: int, cregs: list):
        code = ''
        if self.tmp_reg_usage > 0:
            code += f'qubit[{self.tmp_reg_usage}] tmp_reg;\n'
        if self.carry_reg_usage > 0:
            code += f'qubit[{self.carry_reg_usage}] carry_reg;\n'
        if self.cond_reg_usage > 0:
            code += f'qubit[{self.cond_reg_usage}] cond_reg;\n'

        if data_len > 0:
            code += f'qubit[{data_len}] data;\n'
        if stack_len > 0:
            code += f'qubit[{stack_len}] stack;\n'

        # always have classical condition register, to make output order consistent
        code += f'bit[1] cond_creg;\n'
        for creg in cregs:
            code += f'bit[{creg.size}] {creg.segment};\n'
        return code

    def run(self, blk: basicBlock, data_len: int, stack_len: int, cregs: list) -> str:
        # maybe generate register definition after scanning the IR,
        # to determine the size of some registers and classical registers
        header = 'OPENQASM 3.0;\ninclude "stdgates.inc";\n'

        # need to call gencode first to determine register usage
        code = self.gencode(blk, 0)
        regdef = self.gen_regdef(data_len, stack_len, cregs)

        return header + regdef + '\n' + code 

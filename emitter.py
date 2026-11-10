"""Emissão fornecida. Spills residem em memória entre instruções."""
import ir as I
from backend_api import REGISTERS

def emit_rv64(program, allocations, *, test=False):
    lines = ['.option norelax', '.text', '.globl _start', '_start:']
    names = {fn.function: f'.Lfunction_{n}' for n, fn in enumerate(program.functions)}
    main = next(s for s in names if s.name == 'main')
    lines += [f'call {names[main]}', 'addi sp, sp, -16', 'sd a0, 0(sp)']
    if test:
        lines += ['li a0, 2', 'mv a1, sp', 'li a2, 8', 'li a7, 64', 'ecall']
    lines += ['ld a0, 0(sp)', 'li a7, 93', 'ecall']
    for fn_index, fn in enumerate(program.functions):
        allocation = allocations[fn.function]
        vertices = {v for ins in fn.instructions for v in I.uses(ins) | I.defs(ins)}
        if set(allocation) != vertices or any(r is not None and r not in REGISTERS for r in allocation.values()):
            raise ValueError('alocação incompleta ou registrador inválido')
        used = [r for r in REGISTERS if r in allocation.values()]
        outgoing = max([0] + [max(0, len(ins.args)-8)*8 for ins in fn.instructions if isinstance(ins, I.Call)])
        spilled = sorted((v for v in vertices if allocation[v] is None), key=lambda v: v.id)
        slots = {v: outgoing+8*n for n, v in enumerate(spilled)}
        saved = {r: outgoing+8*len(spilled)+8*n for n, r in enumerate(used + ['ra'])}
        size = (outgoing+8*(len(spilled)+len(saved))+15)//16*16
        def add(s): lines.append(s)
        def memory(op, reg, offset):
            if -2048 <= offset <= 2047:
                add(f'{op} {reg}, {offset}(sp)')
            else:
                add(f'li t3, {offset}'); add('add t3, sp, t3'); add(f'{op} {reg}, 0(t3)')
        def read(v, temp='t0'):
            reg = allocation[v]
            if reg is None:
                memory('ld', temp, slots[v]); return temp
            return reg
        def label(l): return f'.Llabel_{fn_index}_{l.id}'
        epilogue = f'.Lreturn_{fn_index}'
        add(names[fn.function]+':')
        add(f'li t3, {size}'); add('sub sp, sp, t3')
        for reg, offset in saved.items(): memory('sd', reg, offset)
        for ins in fn.instructions:
            name = type(ins).__name__
            dst = getattr(ins, 'dst', None)
            target = allocation[dst] or 't2' if dst is not None else None
            if name == 'LabelInstr': add(label(ins.label)+':')
            elif name == 'Jump': add(f'j {label(ins.target)}')
            elif name == 'Li': add(f'li {target}, {ins.imm}')
            elif name == 'Param':
                if ins.index < 8: add(f'mv {target}, a{ins.index}')
                else: memory('ld', target, size+8*(ins.index-8))
            elif name in ('Move', 'Neg', 'Seqz', 'Snez'):
                add(f'{dict(Move="mv", Neg="neg", Seqz="seqz", Snez="snez")[name]} {target}, {read(ins.src)}')
            elif name in ('Addi', 'Slli'):
                value = ins.imm if name == 'Addi' else ins.shift
                add(f'{name.lower()} {target}, {read(ins.src)}, {value}')
            elif name in ('Add', 'Sub', 'Mul', 'Div', 'Rem', 'Slt', 'Xor'):
                a, b = read(ins.lhs), read(ins.rhs, 't1')
                add(f'{name.lower()} {target}, {a}, {b}')
            elif name in ('Beq', 'Bne', 'Blt', 'Bge', 'Beqz', 'Bnez'):
                a = read(ins.src if name.endswith('z') else ins.lhs)
                b = 'zero' if name.endswith('z') else read(ins.rhs, 't1')
                op = name[:3].lower() if name.endswith('z') else name.lower()
                add(f'{op} {a}, {b}, {label(ins.target)}')
            elif name == 'Call':
                for n, arg in enumerate(ins.args):
                    reg = read(arg)
                    if n < 8: add(f'mv a{n}, {reg}')
                    else: memory('sd', reg, 8*(n-8))
                add(f'call {names[ins.function]}')
                if target: add(f'mv {target}, a0')
            elif name == 'Return':
                if ins.value is not None: add(f'mv a0, {read(ins.value)}')
                add(f'j {epilogue}')
            elif name == 'PrintString':
                add(f'lla a1, .Lstring_{ins.string.id}')
                add(f'li a2, {len(program.strings[ins.string].encode("utf-8"))}')
                add('call .Lwrite')
            elif name in ('PrintInt', 'PrintBool'):
                add(f'mv a0, {read(ins.value)}')
                add('call .Linteger' if name == 'PrintInt' else 'call .Lboolean')
            else: raise ValueError(f'instrução desconhecida: {name}')
            if dst is not None and allocation[dst] is None: memory('sd', 't2', slots[dst])
        add(epilogue+':')
        for reg, offset in saved.items(): memory('ld', reg, offset)
        add(f'li t3, {size}'); add('add sp, sp, t3'); add('ret')
    lines += RUNTIME.splitlines()
    lines.append('.section .rodata')
    for ref, text in program.strings.items():
        lines += [f'.Lstring_{ref.id}:', '.byte '+','.join(str(b) for b in text.encode('utf-8') or b'\0')]
    return '\n'.join(lines)+'\n'

RUNTIME = '''
.Lwrite:
 li a0, 1
 li a7, 64
 ecall
 ret
.Lboolean:
 beqz a0, .Lfalse
 lla a1, .Ltrue_text
 li a2, 4
 j .Lwrite
.Lfalse:
 lla a1, .Lfalse_text
 li a2, 5
 j .Lwrite
.Linteger:
 addi sp, sp, -32
 addi t0, sp, 32
 mv t1, a0
 li t4, 10
 slt t5, a0, zero
 beqz t5, .Ldigits
 neg t1, t1
.Ldigits:
 remu t2, t1, t4
 divu t1, t1, t4
 addi t2, t2, 48
 addi t0, t0, -1
 sb t2, 0(t0)
 bnez t1, .Ldigits
 beqz t5, .Lnumber_write
 addi t0, t0, -1
 li t2, 45
 sb t2, 0(t0)
.Lnumber_write:
 mv a1, t0
 addi a2, sp, 32
 sub a2, a2, t0
 li a0, 1
 li a7, 64
 ecall
 addi sp, sp, 32
 ret
.section .rodata
.Ltrue_text: .ascii "true"
.Lfalse_text: .ascii "false"
'''

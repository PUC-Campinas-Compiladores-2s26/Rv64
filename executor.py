"""Validação e interpretação da IR, independentes do seletor."""

from dataclasses import dataclass, fields
from ast_nodes import SourceSpan
import ir as I


# Conservar os 64 bits inferiores e interpretá-los com sinal.
def signed(n):
    return ((n + (1 << 63)) % (1 << 64)) - (1 << 63)


def quotient(a, b):
    """Divida com truncamento para zero, sem conversão para ponto flutuante."""
    if b == 0:
        raise RuntimeError("divisão por zero: comportamento indefinido")
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def validate(program):
    """Confira a estrutura da IR, sem repetir a análise semântica do frontend."""
    if not isinstance(program, I.ProgramIR) or not all(
        isinstance(f, I.FunctionIR) for f in program.functions
    ):
        raise ValueError("programa inválido")
    functions = {f.function: f for f in program.functions}
    if len(functions) != len(program.functions):
        raise ValueError("função duplicada")
    for ref, text in program.strings.items():
        if (
            not isinstance(ref, I.StringRef)
            or type(ref.id) is not int
            or ref.id < 0
            or not isinstance(text, str)
        ):
            raise ValueError("pool inválido")
    for fn in program.functions:
        labels = [i.label for i in fn.instructions if isinstance(i, I.LabelInstr)]
        if any(
            not isinstance(l, I.Label)
            or l.owner is not fn.function
            or type(l.id) is not int
            or l.id < 0
            for l in labels
        ):
            raise ValueError("label inválido")
        if len(set(labels)) != len(labels):
            raise ValueError("label duplicado")
        params = []
        for index, ins in enumerate(fn.instructions):
            name = type(ins).__name__
            if name not in I.SCHEMAS or type(ins) is not getattr(I, name):
                raise ValueError("instrução inválida")
            if ins.origin is not None and not isinstance(ins.origin, SourceSpan):
                raise ValueError("origin inválido")
            if isinstance(ins, I.Call) and (
                not isinstance(ins.args, (tuple, list))
                or not all(isinstance(x, I.VReg) for x in ins.args)
            ):
                raise ValueError("argumentos inválidos")
            for operand in (*I.uses(ins), *I.defs(ins)):
                if (
                    operand.owner is not fn.function
                    or type(operand.id) is not int
                    or operand.id < 0
                ):
                    raise ValueError("VReg de outra função")
            for field_name in I.SCHEMAS[name].split():
                val = getattr(ins, field_name)
                if field_name in (
                    "dst",
                    "src",
                    "lhs",
                    "rhs",
                    "value",
                ) and not isinstance(val, I.VReg):
                    if not (
                        val is None
                        and (
                            (name == "Call" and field_name == "dst") or name == "Return"
                        )
                    ):
                        raise ValueError("operando não é VReg")
            if hasattr(ins, "target") and (
                not isinstance(ins.target, I.Label)
                or ins.target.owner is not fn.function
                or ins.target not in labels
            ):
                raise ValueError("destino ausente")
            if isinstance(ins, I.LabelInstr) and (
                not isinstance(ins.label, I.Label) or ins.label.owner is not fn.function
            ):
                raise ValueError("label inválido")
            if name in ("Li", "Addi", "Slli", "Param"):
                value = getattr(
                    ins,
                    {"Li": "imm", "Addi": "imm", "Slli": "shift", "Param": "index"}[
                        name
                    ],
                )
                lo, hi = {
                    "Li": (-(1 << 63), (1 << 63) - 1),
                    "Addi": (-2048, 2047),
                    "Slli": (0, 63),
                    "Param": (0, len(fn.function.parameter_types) - 1),
                }[name]
                if type(value) is not int or not lo <= value <= hi:
                    raise ValueError("inteiro fora dos limites")
            if isinstance(ins, I.Param):
                if index != len(params):
                    raise ValueError("Param fora do início")
                params.append(ins.index)
            if isinstance(ins, I.Call):
                if not isinstance(ins.args, (list, tuple)) or not all(
                    isinstance(x, I.VReg) for x in ins.args
                ):
                    raise ValueError("argumentos inválidos")
                if ins.function not in functions or len(ins.args) != len(
                    ins.function.parameter_types
                ):
                    raise ValueError("chamada inválida")
                if ins.function.type.value == "void" and ins.dst is not None:
                    raise ValueError("retorno void")
                if not all(isinstance(x, I.VReg) for x in ins.args):
                    raise ValueError("argumentos inválidos")
            if isinstance(ins, I.Return) and (
                (ins.value is None) != (fn.function.type.value == "void")
            ):
                raise ValueError("retorno incompatível")
            if isinstance(ins, I.PrintString) and (
                not isinstance(ins.string, I.StringRef)
                or ins.string not in program.strings
            ):
                raise ValueError("string ausente")
        if params != list(range(len(fn.function.parameter_types))):
            raise ValueError("parâmetros incompletos")


@dataclass
class ExecutionResult:
    """Saída textual, retorno integral de main e passos da execução."""

    stdout: str
    main_return: int
    steps: int


class Interpreter:
    """Executor fornecido para testar as instruções pseudoRV64 geradas."""

    def run(self, program, max_steps=100000):
        """Execute main com um limite de passos compartilhado pelas chamadas."""
        validate(program)
        functions = {f.function: f for f in program.functions}
        output, steps = [], 0

        def boolean(v):
            if v not in (0, 1):
                raise RuntimeError("bool não normalizado")
            return v

        def execute(symbol, args):
            nonlocal steps
            for value, typ in zip(args, symbol.parameter_types):
                if typ.value == "bool":
                    boolean(value)
            fn = functions[symbol]
            labels = {
                i.label: n
                for n, i in enumerate(fn.instructions)
                if isinstance(i, I.LabelInstr)
            }
            # Cada chamada cria seus próprios valores, inclusive na recursão.
            values, pc = {}, 0

            def read(v):
                if v not in values:
                    raise RuntimeError("leitura de VReg sem valor")
                return values[v]

            while pc < len(fn.instructions):
                steps += 1
                if steps > max_steps:
                    raise RuntimeError("limite de passos")
                ins = fn.instructions[pc]
                pc += 1
                n = type(ins).__name__
                if n == "LabelInstr":
                    continue
                if n == "Li":
                    result = ins.imm
                elif n == "Param":
                    result = args[ins.index]
                elif n == "Move":
                    result = read(ins.src)
                elif n == "Neg":
                    result = -read(ins.src)
                elif n == "Addi":
                    result = read(ins.src) + ins.imm
                elif n == "Slli":
                    result = read(ins.src) << ins.shift
                elif n in ("Seqz", "Snez"):
                    result = int(
                        (read(ins.src) == 0) if n == "Seqz" else (read(ins.src) != 0)
                    )
                elif n in ("Add", "Sub", "Mul", "Div", "Rem", "Slt", "Xor"):
                    a, b = read(ins.lhs), read(ins.rhs)
                    if n == "Add":
                        result = a + b
                    elif n == "Sub":
                        result = a - b
                    elif n == "Mul":
                        result = a * b
                    elif n == "Div":
                        result = quotient(a, b)
                    elif n == "Rem":
                        result = a - quotient(a, b) * b
                    elif n == "Slt":
                        result = int(a < b)
                    else:
                        result = a ^ b
                elif n == "Jump":
                    pc = labels[ins.target]
                    continue
                elif n in ("Beq", "Bne", "Blt", "Bge", "Beqz", "Bnez"):
                    a, b = (
                        (read(ins.src), 0)
                        if n.endswith("z")
                        else (read(ins.lhs), read(ins.rhs))
                    )
                    take = {
                        "Beq": a == b,
                        "Bne": a != b,
                        "Blt": a < b,
                        "Bge": a >= b,
                        "Beqz": a == b,
                        "Bnez": a != b,
                    }[n]
                    if take:
                        pc = labels[ins.target]
                    continue
                elif n == "Call":
                    result = execute(ins.function, [read(a) for a in ins.args])
                    if ins.dst is None:
                        continue
                elif n == "Return":
                    result = None if ins.value is None else read(ins.value)
                    if symbol.type.value == "bool":
                        boolean(result)
                    return result
                elif n.startswith("Print"):
                    if n == "PrintString":
                        output.append(program.strings[ins.string])
                    elif n == "PrintBool":
                        output.append("true" if boolean(read(ins.value)) else "false")
                    else:
                        output.append(str(read(ins.value)))
                    continue
                else:
                    raise RuntimeError(n)
                # As leituras ocorreram antes da escrita, mesmo se dst é entrada.
                values[ins.dst] = signed(result)
            raise RuntimeError("fim de função sem Return")

        mains = [s for s in functions if s.name == "main"]
        if len(mains) != 1:
            raise ValueError("main ausente ou duplicado")
        result = execute(mains[0], [])
        return ExecutionResult("".join(output), result, steps)

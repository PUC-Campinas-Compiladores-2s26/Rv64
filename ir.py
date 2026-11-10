"""Modelo executável pseudoRV64. Não contém tradução da AST."""

import json

import load_previous
from ast_nodes import SourceSpan
from dataclasses import dataclass, field, fields, make_dataclass


@dataclass(frozen=True)
class VReg:
    """Identidade de um registrador virtual local à função proprietária."""

    owner: object
    id: int


@dataclass(frozen=True)
class Label:
    """Identidade de um destino de controle local à função."""

    owner: object
    id: int


@dataclass(frozen=True)
class StringRef:
    """Referência ao texto decodificado no pool do programa."""

    id: int


@dataclass
class FunctionIR:
    """Símbolo original e instruções de uma função compilada."""

    function: object
    instructions: list = field(default_factory=list)


@dataclass
class ProgramIR:
    """Funções compiladas e pool de strings compartilhado entre elas."""

    functions: list = field(default_factory=list)
    strings: dict = field(default_factory=dict)


# Os esquemas fixam a ordem dos operandos nas classes de instrução.
SCHEMAS = {
    "Li": "dst imm",
    "Move": "dst src",
    "Neg": "dst src",
    **{n: "dst lhs rhs" for n in ["Add", "Sub", "Mul", "Div", "Rem", "Slt", "Xor"]},
    "Addi": "dst src imm",
    "Slli": "dst src shift",
    "Seqz": "dst src",
    "Snez": "dst src",
    "LabelInstr": "label",
    "Jump": "target",
    **{n: "lhs rhs target" for n in ["Beq", "Bne", "Blt", "Bge"]},
    "Beqz": "src target",
    "Bnez": "src target",
    "Param": "dst index",
    "Call": "dst function args",
    "Return": "value",
    "PrintInt": "value",
    "PrintBool": "value",
    "PrintString": "string",
}


def _local_check(self):
    """Valide campos locais. Referências são conferidas por executor.validate."""
    if self.origin is not None and not isinstance(self.origin, SourceSpan):
        raise ValueError("origin inválido")
    name = type(self).__name__
    if name in ("Li", "Addi", "Slli"):
        attr, lo, hi = {
            "Li": ("imm", -(1 << 63), (1 << 63) - 1),
            "Addi": ("imm", -2048, 2047),
            "Slli": ("shift", 0, 63),
        }[name]
        value = getattr(self, attr)
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError("imediato inválido")


# Cada esquema gera uma dataclass com operandos posicionais e origin opcional.
for name, schema in SCHEMAS.items():
    globals()[name] = make_dataclass(
        name,
        [(s, object) for s in schema.split()]
        + [("origin", SourceSpan | None, field(default=None, kw_only=True))],
        frozen=True,
        namespace={"__module__": __name__, "__post_init__": _local_check},
    )


def uses(ins):
    """VRegs lidos pela instrução, para validação e análises da etapa final."""
    if isinstance(ins, Call):
        return set(ins.args)
    return {
        getattr(ins, f.name)
        for f in fields(ins)
        if f.name not in ("dst", "origin") and isinstance(getattr(ins, f.name), VReg)
    }


def defs(ins):
    """VRegs escritos pela instrução, sem incluir os argumentos de Call."""
    dst = getattr(ins, "dst", None)
    return {dst} if isinstance(dst, VReg) else set()


class Context:
    """Recursos de geração de uma função. O pool pertence ao programa inteiro."""

    def __init__(self, function, program):
        self.function, self.program = function, program
        self.registers, self.labels, self.symbols = 0, 0, {}

    def temp(self):
        r = VReg(self.function.function, self.registers)
        self.registers += 1
        return r

    def label(self):
        r = Label(self.function.function, self.labels)
        self.labels += 1
        return r

    def variable(self, symbol):
        """Reutilize o VReg pelo objeto de símbolo, preservando sombreamento."""
        if symbol not in self.symbols:
            self.symbols[symbol] = self.temp()
        return self.symbols[symbol]

    def emit(self, ins):
        self.function.instructions.append(ins)

    def string(self, value):
        """Registre ou reutilize texto decodificado, inclusive a quebra final."""
        for ref, text in self.program.strings.items():
            if text == value:
                return ref
        ref = StringRef(len(self.program.strings))
        self.program.strings[ref] = value
        return ref


def format_ir(program):
    """Produza o dump de inspeção com mnemônicos próximos de RV64."""
    lines = []
    if program.strings:
        lines.append(".strings")
        for ref, text in program.strings.items():
            # Escapes mantêm cada entrada em uma linha e preservam seu conteúdo.
            literal = json.dumps(text, ensure_ascii=False)
            lines.append(f"str{ref.id}: {literal}")
        lines.append("")
    for fn in program.functions:
        lines.append(f"{fn.function.name}:")
        for ins in fn.instructions:

            def operand(x):
                if isinstance(x, VReg):
                    return f"v{x.id}"
                if isinstance(x, Label):
                    return f"L{x.id}"
                if isinstance(x, StringRef):
                    return f"str{x.id}"
                if isinstance(x, (list, tuple)):
                    return "[" + ", ".join(map(operand, x)) + "]"
                if hasattr(x, "name"):
                    return x.name
                return str(x)

            if isinstance(ins, LabelInstr):
                lines.append(operand(ins.label) + ":")
                continue
            names = {
                "Move": "mv",
                "Jump": "j",
                "PrintInt": "print_int",
                "PrintBool": "print_bool",
                "PrintString": "print_string",
            }
            mnemonic = names.get(type(ins).__name__, type(ins).__name__.lower())
            operands = [
                operand(getattr(ins, f.name)) for f in fields(ins) if f.name != "origin"
            ]
            if isinstance(ins, Return) and ins.value is None:
                operands = []
            lines.append(("  " + mnemonic + " " + ", ".join(operands)).rstrip())
    return "\n".join(lines)

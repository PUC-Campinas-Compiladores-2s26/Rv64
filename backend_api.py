"""Tipos fornecidos para as análises do backend."""
from dataclasses import dataclass, field

REGISTERS = tuple(f"s{i}" for i in range(9))

@dataclass
class BasicBlock:
    start: int
    stop: int
    predecessors: set = field(default_factory=set)
    successors: set = field(default_factory=set)

@dataclass
class CFG:
    function: object
    blocks: dict
    entry: int | None

@dataclass
class Liveness:
    live_in: dict
    live_out: dict


@dataclass
class InstructionLiveness:
    """Conjuntos de VRegs indexados pela posição na lista de instruções."""

    before: dict
    after: dict

"""Representação de regras. O algoritmo pertence ao grupo."""

import load_previous
from dataclasses import dataclass
from enum import Enum
from ast_nodes import BinaryExpr, UnaryExpr, CallExpr, IntLiteral, UnaryOperator


class ResultClass(Enum):
    """Formas de resultado da seleção, independentes dos tipos MicroC."""

    REG = "REG"
    COND = "COND"
    IMM12 = "IMM12"
    POW2 = "POW2"
    EFFECT = "EFFECT"


REG, COND, IMM12, POW2, EFFECT = ResultClass


@dataclass(frozen=True)
class Need:
    """Classe exigida na subárvore que ocupa este ponto do padrão."""

    result: ResultClass


@dataclass(frozen=True)
class Args:
    """Classe exigida em cada argumento de uma chamada de qualquer aridade."""

    result: ResultClass


@dataclass(frozen=True)
class Pattern:
    """Restrições sobre um nó da AST e padrões de seus filhos."""

    kind: type | None = None
    operator: object = None
    children: tuple = ()
    predicate: object = None


@dataclass(frozen=True)
class Rule:
    """Padrão, classe oferecida, custo próprio e identificador da ação emissora."""

    name: str
    result: ResultClass
    pattern: Pattern
    cost: int
    action: str

    def __post_init__(self):
        if type(self.cost) is not int or self.cost < 0:
            raise ValueError("custo inválido")


@dataclass
class Choice:
    """Cobertura escolhida: custo total, regra e pares (nó, classe) exigidos."""

    cost: int
    rule: Rule
    subproblems: tuple


class SelectionTable:
    """Resultados por identidade do nó e classe, sem modificar a AST."""

    def __init__(self):
        self.entries = {}
        self.nodes = {}

    def lookup(self, node, result_class):
        return self.entries.get((id(node), result_class))

    def put(self, node, result_class, choice):
        # Manter os nós vivos impede a reutilização de seus IDs nesta tabela.
        self.nodes[id(node)] = node
        self.entries[id(node), result_class] = choice


def children(node):
    """Filhos de expressão na ordem da fonte, sem criar outra árvore."""
    if isinstance(node, BinaryExpr):
        return (node.left, node.right)
    if isinstance(node, UnaryExpr):
        return (node.operand,)
    if isinstance(node, CallExpr):
        return tuple(node.arguments)
    return ()


def signed_literal(node):
    """Reconheça inteiro ou sua negação imediata, sem folding de expressões."""
    if isinstance(node, IntLiteral):
        return node.value
    if (
        isinstance(node, UnaryExpr)
        and node.operator is UnaryOperator.NEGATE
        and isinstance(node.operand, IntLiteral)
    ):
        return -node.operand.value
    return None


def imm12(node):
    """Teste o intervalo do imediato com sinal de Addi."""
    n = signed_literal(node)
    return n is not None and -2048 <= n <= 2047


def pow2(node):
    """Reconheça potências positivas de dois permitidas nos literais MicroC."""
    n = signed_literal(node)
    return n is not None and 0 < n <= (1 << 62) and n & (n - 1) == 0


def neg_imm12(node):
    """Reconheça um literal cujo oposto cabe no imediato de Addi."""
    n = signed_literal(node)
    return n is not None and -2048 <= -n <= 2047

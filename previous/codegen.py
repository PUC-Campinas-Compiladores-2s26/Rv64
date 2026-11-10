"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ir import Context, ProgramIR, FunctionIR


class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        raise NotImplementedError("implemente CodeGenerator.generate")

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        raise NotImplementedError("implemente seleção e emissão")

    def statement(self, node):
        """Traduza um comando ad hoc."""
        raise NotImplementedError("implemente comandos")

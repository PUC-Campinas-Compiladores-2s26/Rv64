from __future__ import annotations

import load_previous  # Disponibiliza os módulos das etapas anteriores.

from ast_nodes import Program
from flow_analysis import check_flow
from name_resolver import resolve_names
from type_checker import check_types


class SemanticAnalyzer:
    """Nomes → tipos → fluxo. Uma passagem com erros impede as seguintes."""

    def analyze(self, program: Program) -> Program:
        resolve_names(program)
        check_types(program)
        check_flow(program)
        return program

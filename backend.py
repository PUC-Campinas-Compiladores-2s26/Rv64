"""Coordenação e adaptação dos LRs para o emissor fornecido."""

from dataclasses import fields, replace

import ir as I
from emitter import emit_rv64
from executor import validate
from interference import build_interference
from live_ranges import build_live_ranges
from liveness import solve_instruction_liveness, solve_liveness
from regalloc import allocate
from rv_cfg import build_cfg


def _rewrite_function(function, ranges):
    rewritten = []
    for index, instruction in enumerate(function.instructions):
        operands = {}
        for field in fields(instruction):
            value = getattr(instruction, field.name)
            if isinstance(value, I.VReg):
                phase = "after" if field.name == "dst" else "before"
                operands[field.name] = ranges[index, phase, value]
        if isinstance(instruction, I.Call):
            operands["args"] = tuple(
                ranges[index, "before", value] for value in instruction.args
            )
        rewritten.append(replace(instruction, **operands))
    return replace(function, instructions=rewritten)


def compile_program(program, *, test=False, force_spills=False):
    validate(program)
    allocations = {}
    functions = []
    for function in program.functions:
        cfg = build_cfg(function)
        points = solve_instruction_liveness(cfg, solve_liveness(cfg))
        ranges = build_live_ranges(cfg, points)
        graph = build_interference(cfg, points, ranges)
        allocations[function.function] = (
            {node: None for node in graph} if force_spills else allocate(graph)
        )
        functions.append(_rewrite_function(function, ranges))
    return emit_rv64(replace(program, functions=functions), allocations, test=test)

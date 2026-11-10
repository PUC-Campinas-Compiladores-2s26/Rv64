"""Casos públicos: contratos e decisões, sem exigir cores específicas."""
import ir as I
import pytest
from rv_cfg import build_cfg
from liveness import solve_instruction_liveness, solve_liveness
from live_ranges import build_live_ranges
from interference import build_interference
from regalloc import allocate
from backend_api import REGISTERS

def graph(size, edges):
    owner = object()
    nodes = [I.VReg(owner, n) for n in range(size)]
    result = {v: set() for v in nodes}
    for a, b in edges:
        result[nodes[a]].add(nodes[b]); result[nodes[b]].add(nodes[a])
    return result

def verify(graph, pool=REGISTERS):
    before = {v: set(n) for v, n in graph.items()}
    trace = []
    result = allocate(graph, pool, trace=trace)
    assert graph == before and set(result) == set(graph)
    active = set(graph)
    assert len(trace) == len(graph)
    for v, potential in trace:
        low = {n for n in active if len(graph[n] & active) < len(pool)}
        assert v in active
        assert potential == (not low)
        assert not low or v in low
        active.remove(v)
    selected = {}
    for v, _ in reversed(trace):
        available = set(pool) - {selected.get(n) for n in graph[v]}
        assert (result[v] in available) if available else result[v] is None
        selected[v] = result[v]
    return result

@pytest.mark.parametrize('size', range(1, 11))
def test_cliques(size):
    g = graph(size, [(a,b) for a in range(size) for b in range(a)])
    assert sum(r is None for r in verify(g).values()) == max(0,size-9)

def test_candidate_is_not_spill():
    g = graph(4, [(0,1),(1,2),(2,3),(3,0)])
    assert all(r is not None for r in verify(g, ('s0','s1')).values())

def test_entry_and_move():
    owner = object()
    a,b,c = [I.VReg(owner,n) for n in range(3)]
    fn = I.FunctionIR(owner, [I.Move(c,a), I.Add(c,c,b), I.Return(c)])
    cfg = build_cfg(fn); facts = solve_liveness(cfg)
    assert facts.live_in == {0:{a,b}} and facts.live_out == {0:set()}
    points = solve_instruction_liveness(cfg, facts)
    ranges = build_live_ranges(cfg, points)
    first_c = ranges[0, "after", c]
    last_c = ranges[1, "after", c]
    assert first_c != last_c
    assert ranges[1, "before", c] == first_c
    assert ranges[2, "before", c] == last_c
    entry_a, entry_b = (ranges[0, "before", v] for v in (a, b))
    assert build_interference(cfg, points, ranges) == {
        entry_a: {entry_b},
        entry_b: {entry_a, first_c},
        first_c: {entry_b},
        last_c: set(),
    }

def test_loop_cfg():
    owner = object(); a=I.VReg(owner,0); label=I.Label(owner,0)
    fn=I.FunctionIR(owner,[I.Li(a,3),I.LabelInstr(label),I.Addi(a,a,-1),I.Bnez(a,label),I.Return(a)])
    cfg=build_cfg(fn)
    assert {k:b.successors for k,b in cfg.blocks.items()} == {0:{1},1:{1,4},4:set()}
    assert cfg.blocks[1].predecessors == {0,1}
    facts=solve_liveness(cfg)
    assert facts.live_in == {0:set(),1:{a},4:{a}}
    assert facts.live_out == {0:{a},1:{a},4:set()}

def test_dead_definition():
    owner=object(); a,b=[I.VReg(owner,n) for n in range(2)]
    cfg=build_cfg(I.FunctionIR(owner,[I.Li(a,1),I.Li(b,2),I.Return(a)]))
    points = solve_instruction_liveness(cfg, solve_liveness(cfg))
    ranges = build_live_ranges(cfg, points)
    x, y = ranges[0, "after", a], ranges[1, "after", b]
    assert build_interference(cfg, points, ranges) == {x: {y}, y: {x}}


def test_instruction_liveness_and_loop_range():
    owner = object()
    v = I.VReg(owner, 0)
    label = I.Label(owner, 0)
    fn = I.FunctionIR(owner, [
        I.Li(v, 3), I.LabelInstr(label), I.Addi(v, v, -1),
        I.Bnez(v, label), I.Return(v),
    ])
    cfg = build_cfg(fn)
    points = solve_instruction_liveness(cfg, solve_liveness(cfg))
    assert points.before == {0: set(), 1: {v}, 2: {v}, 3: {v}, 4: {v}}
    assert points.after == {0: {v}, 1: {v}, 2: {v}, 3: {v}, 4: set()}
    ranges = build_live_ranges(cfg, points)
    expected = {(i, "before", v) for i in range(1, 5)}
    expected |= {(i, "after", v) for i in range(4)}
    assert set(ranges) == expected
    assert len(set(ranges.values())) == 1


def test_separate_ranges():
    owner = object()
    v = I.VReg(owner, 0)
    fn = I.FunctionIR(owner, [I.Li(v, 1), I.PrintInt(v), I.Li(v, 2), I.Return(v)])
    cfg = build_cfg(fn)
    points = solve_instruction_liveness(cfg, solve_liveness(cfg))
    ranges = build_live_ranges(cfg, points)
    assert set(ranges) == {
        (0, "after", v), (1, "before", v), (2, "after", v), (3, "before", v),
    }
    assert ranges[0, "after", v] == ranges[1, "before", v]
    assert ranges[2, "after", v] == ranges[3, "before", v]
    assert len(set(ranges.values())) == 2


def test_copy_keeps_source_and_destination_separate():
    owner = object()
    a, b, c, d = [I.VReg(owner, n) for n in range(4)]
    fn = I.FunctionIR(owner, [
        I.Li(a, 7), I.Li(b, 2), I.Move(c, a),
        I.Add(d, a, b), I.Add(d, d, c), I.Return(d),
    ])
    cfg = build_cfg(fn)
    points = solve_instruction_liveness(cfg, solve_liveness(cfg))
    ranges = build_live_ranges(cfg, points)
    x, y, z, first, last = [
        ranges[index, "after", value]
        for index, value in enumerate([a, b, c, d, d])
    ]
    assert len({x, y, z, first, last}) == 5
    assert build_interference(cfg, points, ranges) == {
        x: {y}, y: {x, z}, z: {y, first}, first: {z}, last: set(),
    }

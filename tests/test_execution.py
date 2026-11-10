"""Testes das partes fornecidas. Alocações forçadas não avaliam qualidade."""
import ir as I
import pytest
from types import SimpleNamespace
from executor import Interpreter
from emitter import emit_rv64
from toolchain import execute

class Symbol:
    def __init__(self,name,arity=0):
        self.name=name
        self.parameter_types=[SimpleNamespace(value='int') for _ in range(arity)]
        self.type=SimpleNamespace(value='int')

@pytest.mark.parametrize('value', [0,42,-7,-(1<<63),(1<<63)-1])
@pytest.mark.parametrize('spills', [False,True])
def test_integer(value,spills):
    symbol=Symbol('main'); a,b,c=[I.VReg(symbol,n) for n in range(3)]
    fn=I.FunctionIR(symbol,[I.Li(a,value),I.Li(b,1),I.Add(c,a,b),I.PrintInt(a),I.Return(c)])
    program=I.ProgramIR([fn])
    allocation={a:None,b:None,c:None} if spills else {a:'s0',b:'s1',c:'s2'}
    expected=Interpreter().run(program)
    actual=execute(emit_rv64(program,{symbol:allocation},test=True))
    assert (actual.stdout,actual.main_return)==(expected.stdout,expected.main_return)

@pytest.mark.parametrize('arity',[0,1,8,9,12])
def test_call(arity):
    main,foo=Symbol('main'),Symbol('foo',arity)
    args=[I.VReg(main,n) for n in range(arity)]; out=I.VReg(main,arity)
    params=[I.VReg(foo,n) for n in range(arity)]; acc=I.VReg(foo,arity)
    f=I.FunctionIR(foo,[*[I.Param(v,n) for n,v in enumerate(params)],I.Li(acc,0),*[I.Add(acc,acc,v) for v in params],I.Return(acc)])
    m=I.FunctionIR(main,[*[I.Li(v,n+1) for n,v in enumerate(args)],I.Call(out,foo,args),I.Return(out)])
    program=I.ProgramIR([m,f]); allocations={}
    for fn in program.functions:
        allocations[fn.function]={v:None for ins in fn.instructions for v in I.uses(ins)|I.defs(ins)}
    assert execute(emit_rv64(program,allocations,test=True)).main_return==arity*(arity+1)//2

@pytest.mark.parametrize('count',[3,300])
def test_large_frame_and_loop(count):
    s=Symbol('main'); values=[I.VReg(s,n) for n in range(count)]
    acc=I.VReg(s,count); label=I.Label(s,0)
    code=[*[I.Li(v,n+1) for n,v in enumerate(values)],I.Li(acc,0)]
    code += [I.Add(acc,acc,v) for v in values]
    code += [I.LabelInstr(label),I.Addi(values[0],values[0],-1),I.Bnez(values[0],label),I.Return(acc)]
    program=I.ProgramIR([I.FunctionIR(s,code)])
    allocation={v:None for v in [*values,acc]}
    assert execute(emit_rv64(program,{s:allocation},test=True)).main_return==count*(count+1)//2

def test_recursion_and_output():
    main,rec=Symbol('main'),Symbol('rec',1)
    n,one,smaller,result,total=[I.VReg(rec,k) for k in range(5)]
    end=I.Label(rec,0);a,b=[I.VReg(main,k) for k in range(2)]
    text=I.StringRef(0)
    fn=I.FunctionIR(rec,[I.Param(n,0),I.Beqz(n,end),I.Li(one,1),I.Sub(smaller,n,one),I.Call(result,rec,[smaller]),I.Add(total,result,n),I.Return(total),I.LabelInstr(end),I.Return(n)])
    m=I.FunctionIR(main,[I.Li(a,8),I.Call(b,rec,[a]),I.PrintString(text),I.PrintInt(b),I.Li(a,1),I.PrintBool(a),I.Return(b)])
    program=I.ProgramIR([m,fn],{text:'ação\n'})
    allocations={f.function:{v:None for ins in f.instructions for v in I.uses(ins)|I.defs(ins)} for f in program.functions}
    expected=Interpreter().run(program)
    actual=execute(emit_rv64(program,allocations,test=True))
    assert (actual.stdout,actual.main_return)==(expected.stdout,expected.main_return)

def test_callee_saved_and_alignment():
    main,foo=Symbol('main'),Symbol('foo')
    a,b=I.VReg(main,0),I.VReg(foo,0)
    program=I.ProgramIR([I.FunctionIR(main,[I.Call(a,foo,[]),I.Return(a)]),I.FunctionIR(foo,[I.Li(b,42),I.Return(b)])])
    assembly=emit_rv64(program,{main:{a:'s0'},foo:{b:'s8'}},test=True)
    setup='\n'.join(f'li s{n}, {100+n}' for n in range(9))
    checks='\n'.join(f'li t0, {100+n}\nbne s{n}, t0, .Labi_error' for n in range(9))
    assembly=assembly.replace('call .Lfunction_0',setup+'\ncall .Lfunction_0\n'+checks,1)
    for n in range(2):
        label=f'.Lfunction_{n}:'
        assembly=assembly.replace(label,label+'\nandi t6, sp, 15\nbnez t6, .Labi_error')
    assembly+='\n.text\n.Labi_error:\nli a0, 99\nli a7, 93\necall\n'
    assert execute(assembly).main_return==42

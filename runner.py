"""Frontend completo, inspeção e execução do backend."""
import load_previous
import argparse
from pathlib import Path
from Lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGenerator
from executor import Interpreter
from ir import format_ir
from backend import compile_program
from toolchain import build, execute

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--dump-ir', action='store_true')
    modes.add_argument('--run-ir', action='store_true')
    modes.add_argument('--emit-asm', type=Path)
    modes.add_argument('--build', type=Path)
    modes.add_argument('--run', action='store_true')
    args = p.parse_args()
    try:
        ast = Parser(Lexer(args.source.read_text()).scan()).parse()
        SemanticAnalyzer().analyze(ast)
        program = CodeGenerator().generate(ast)
        if args.run_ir:
            print(Interpreter().run(program).stdout, end='')
        elif args.run:
            print(execute(compile_program(program, test=True)).stdout, end='')
        elif args.emit_asm:
            args.emit_asm.write_text(compile_program(program))
        elif args.build:
            build(compile_program(program), args.build)
        else:
            print(format_ir(program))
    except NotImplementedError as e:
        p.exit(3, str(e)+'\n')
    except Exception as e:
        p.exit(1, str(e)+'\n')

if __name__ == '__main__':
    main()

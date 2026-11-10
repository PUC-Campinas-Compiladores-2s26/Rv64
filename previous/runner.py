from __future__ import annotations

import load_previous  # Disponibiliza os módulos das etapas anteriores.

import argparse
from pathlib import Path

from Lexer import Lexer, LexerError
from cfg import format_cfg
from cfg_builder import CFGBuilder
from name_resolver import resolve_names
from parser import Parser, ParserError
from semantic import SemanticAnalyzer
from semantic_errors import SemanticError
from type_checker import check_types


def main(argv: list[str] | None = None) -> int:
    argument_parser = argparse.ArgumentParser(
        description="Execute a Análise Semântica 2 da MicroC."
    )
    argument_parser.add_argument("source", type=Path, metavar="arquivo.mc")
    modes = argument_parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--cfg-only", action="store_true",
        help="construa e mostre os CFGs, após validar nomes e tipos",
    )
    modes.add_argument(
        "--dump-cfg", action="store_true",
        help="mostre os CFGs após a validação semântica completa",
    )
    args = argument_parser.parse_args(argv)

    try:
        source = args.source.read_text(encoding="utf-8")
        program = Parser(Lexer(source).scan()).parse()
        if args.cfg_only:
            resolve_names(program)
            check_types(program)
            for function in program.functions:
                print(format_cfg(CFGBuilder().build(function)))
            print("CFG construído. A análise de fluxo não foi executada.")
            return 0

        SemanticAnalyzer().analyze(program)
        if args.dump_cfg:
            for function in program.functions:
                print(format_cfg(function.metadata["cfg"]))
    except (OSError, UnicodeError) as error:
        argument_parser.error(f"erro ao ler {str(args.source)!r}: {error}")
        return 2
    except (LexerError, ParserError, SemanticError) as error:
        argument_parser.exit(1, f"{error}\n")
        return 1
    except NotImplementedError as error:
        argument_parser.exit(3, f"scaffold incompleto: {error}\n")
        return 3

    print("programa válido na Análise Semântica 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

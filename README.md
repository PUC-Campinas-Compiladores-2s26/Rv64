# Projeto MicroC — Etapa 7

Leia [ENUNCIADO.pdf](ENUNCIADO.pdf). A entrega é em **29/11/2026, às 23h59**, no horário de Brasília, em trios.

Complete `rv_cfg.py`, `liveness.py`, `live_ranges.py`, `interference.py` e `regalloc.py`. A vivacidade deve ser calculada por bloco e por instrução. Os LRs globais agrupam pontos da função e são a unidade de alocação. A API e os tipos estão no enunciado e em `backend_api.py`. O coletor opcional de remoções serve aos testes. Não há relatório.

Recupere seu frontend e o gerador anterior diretamente em `previous/`. Copie os arquivos dessa pasta da Etapa 6 primeiro. Depois copie seus `codegen.py`, `selector.py`, `catalogue.py` e `patterns.py` para ela. Preserve os carregadores e os módulos fornecidos na raiz. Não copie Git, caches ou ambientes virtuais.

```sh
docker build -t microc-rv64 .
docker run --rm -v "$PWD":/work microc-rv64 python run_tests.py
docker run --rm -v "$PWD":/work microc-rv64 python -m pytest -q tests/test_execution.py
docker run --rm -v "$PWD":/work microc-rv64 python runner.py examples/integrado.mc --run
```

Os 19 testes em `test_execution.py` verificam partes fornecidas e devem passar antes da implementação. Os testes de análise e alocação falham enquanto houver métodos pendentes. Nenhum teste deve ser ocultado com skip ou xfail. O interpretador permanece disponível com `--run-ir`. A emissão usa `--emit-asm programa.S`, e a construção usa `--build programa`.

Os testes do backend recebem IR fornecida e não dependem da implementação anterior. A execução dos exemplos MicroC depende do frontend e do gerador recuperados. Os testes ocultos aplicam os mesmos critérios do enunciado a outros casos.

O launcher aceita `--implementation`, `--closed` (somente na distribuição docente), `--collect-only` e `--report`.

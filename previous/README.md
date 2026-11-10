# Frontend das etapas anteriores

Todos os módulos anteriores ficam diretamente nesta pasta, incluindo lexer, parser, AST, símbolos, nomes, tipos e fluxo.

Para recuperar a Semântica 2:

1. Copie os módulos e pacotes auxiliares que estavam em `previous/` da Semântica 2 para esta pasta.
2. Copie os módulos e pacotes auxiliares da raiz da Semântica 2 para esta mesma pasta. Em conflitos, prevalece essa versão mais recente, incluindo `semantic.py` e `semantic_errors.py`.
3. Preserve os carregadores `load_previous.py` fornecidos nesta etapa. Não copie a pasta `previous/` como subdiretório, arquivos Git, ambientes virtuais ou caches.

Os imports continuam usando nomes como `ast_nodes`, `symbols` e `semantic`. Execute o backend pelo runner da raiz do starter. Não altere suas classes nem os contratos das etapas anteriores.

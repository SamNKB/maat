# maat — contexto para o Claude

Biblioteca de análise descritiva de dados sobre **pandas e PySpark** com a mesma API, guiada pela taxonomia de variáveis. Repo público: https://github.com/SamNKB/maat · Página viva: https://samnkb.github.io/maat/fluxo-interativo.html

## Como trabalhar neste projeto

- **Construção conjunta**: o dono do projeto (Sam) decide o design. Consultar **a cada decisão de design** — apresentar opções com exemplos concretos e aguardar escolha antes de consolidar em código ou doc. Nunca definir unilateralmente.
- Documentar sempre com **exemplos concretos** (colunas reais: sexo, e-mail, cidade, data_pedido).
- Commitar e dar push a cada bloco de trabalho concluído.
- Responder em português brasileiro.

## Documentos centrais

- `docs/fluxo-de-analises.md` — o mapa conceitual (tipos, regimes, análises por cenário, questões em aberto na seção 7). **Ler antes de qualquer trabalho de design.**
- `docs/identidade-visual.md` — paleta Blade Runner + fontes aprovadas (Rajdhani / Space Grotesk / JetBrains Mono). Tokens em `assets/design-tokens.css`.
- `datasets/README.md` — manifesto dos 40 datasets de benchmark: 30 do Kaggle + 10 de dados abertos do governo brasileiro (dados só locais, fora do git; re-download via `python scripts/download_datasets.py` e `python scripts/download_gov_datasets.py`). Números reais para exemplos: `python scripts/benchmark_examples.py`.

## Decisões já tomadas (não rediscutir sem o Sam pedir)

- Taxonomia: qualitativa (nominal/ordinal/binária), quantitativa (discreta/contínua), **temporal como tipo de primeira classe** (instante/duração) que se decompõe em derivadas.
- **Regimes de cardinalidade** na nominal: categórico / cauda longa / textual — limiares são parâmetros do usuário (`maat.Config`), incluindo amostra de inferência.
- Princípios: "a inferência propõe, o usuário dispõe" · "o maat descreve, não julga" · duas camadas de perfil (essencial + completa) · custo no backend, visual só recebe agregados.
- Subtipo `rank`: será criado, mas **aguarda validação em datasets reais** (rank vs id sequencial são estatisticamente idênticos).
- Regimes na ordinal: **adiado** até casos reais.

## Estado (2026-08-16, fim do dia)

Estrutura e taxonomia implementadas; inferência, backends e análises ainda são stubs (`NotImplementedError`). **Binária consolidada** (seção 2.5 do fluxo: tabela de frequência com ausentes na essencial; dominante + razão na completa; sem IC, sem par semântico, sem alertas por limiar). Fila de discussão escolhida pelo Sam: **quantitativas primeiro** (discreta → contínua), depois cauda longa, ordinal, textual, temporal. Depois: implementar `core/inference.py` + `PandasBackend` e rodar o benchmark nos 40 datasets. Ideia aceita em avaliação: rodar ydata-profiling (concorrente mais próximo) nos 40 como baseline de comparação.

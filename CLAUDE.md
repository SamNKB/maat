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
- `datasets/README.md` — manifesto dos 30 datasets de benchmark do Kaggle (dados só locais, fora do git; re-download via `python scripts/download_datasets.py`).

## Decisões já tomadas (não rediscutir sem o Sam pedir)

- Taxonomia: qualitativa (nominal/ordinal/binária), quantitativa (discreta/contínua), **temporal como tipo de primeira classe** (instante/duração) que se decompõe em derivadas.
- **Regimes de cardinalidade** na nominal: categórico / cauda longa / textual — limiares são parâmetros do usuário (`maat.Config`), incluindo amostra de inferência.
- Princípios: "a inferência propõe, o usuário dispõe" · "o maat descreve, não julga" · duas camadas de perfil (essencial + completa) · custo no backend, visual só recebe agregados.
- Subtipo `rank`: será criado, mas **aguarda validação em datasets reais** (rank vs id sequencial são estatisticamente idênticos).
- Regimes na ordinal: **adiado** até casos reais.

## Estado (2026-08-16)

Estrutura e taxonomia implementadas; inferência, backends e análises ainda são stubs (`NotImplementedError`). Próximo passo combinado: discutir as análises por tipo (mais simples primeiro: binária → nominal categórica), depois implementar `core/inference.py` + `PandasBackend` e rodar o benchmark nos 30 datasets.

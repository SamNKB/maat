# maat — contexto para o Claude

Biblioteca de análise descritiva de dados sobre **pandas e PySpark** com a mesma API, guiada pela taxonomia de variáveis. Repo público: https://github.com/SamNKB/maat · Página viva: https://samnkb.github.io/maat/fluxo-interativo.html

## Como trabalhar neste projeto

- **Construção conjunta**: o dono do projeto (Sam) decide o design. Consultar **a cada decisão de design** — apresentar opções com exemplos concretos e aguardar escolha antes de consolidar em código ou doc. Nunca definir unilateralmente.
- Documentar sempre com **exemplos concretos** (colunas reais: sexo, e-mail, cidade, data_pedido).
- Commitar e dar push a cada bloco de trabalho concluído.
- Responder em português brasileiro.

## Documentos centrais

- `docs/fluxo-de-analises.md` — o mapa conceitual (tipos, regimes, análises por cenário, narrativas na seção 7, questões em aberto na seção 8). **Ler antes de qualquer trabalho de design.**
- `docs/identidade-visual.md` — paleta Blade Runner + fontes aprovadas (Rajdhani / Space Grotesk / JetBrains Mono). Tokens em `assets/design-tokens.css`.
- `docs/tipos/*.html` — subpáginas detalhadas por tipo (servidas no GitHub Pages), abertas ao clicar no nó correspondente do grafo interativo. Modelo: `binaria.html`. Criar a subpágina de cada tipo **quando ele for consolidado**, com números reais do benchmark.
- `datasets/README.md` — manifesto dos 40 datasets de benchmark: 30 do Kaggle + 10 de dados abertos do governo brasileiro (dados só locais, fora do git; re-download via `python scripts/download_datasets.py` e `python scripts/download_gov_datasets.py`). Números reais para exemplos: `python scripts/benchmark_examples.py`.

## Decisões já tomadas (não rediscutir sem o Sam pedir)

- Taxonomia: qualitativa (nominal/ordinal/binária), quantitativa (discreta/contínua), **temporal como tipo de primeira classe** (instante/duração) que se decompõe em derivadas.
- **Regimes de cardinalidade** na nominal: categórico / cauda longa / textual — limiares são parâmetros do usuário (`maat.Config`), incluindo amostra de inferência.
- Princípios: "a inferência propõe, o usuário dispõe" · "o maat descreve, não julga" · duas camadas de perfil (essencial + completa) · custo no backend, visual só recebe agregados.
- Subtipo `rank`: será criado, mas **aguarda validação em datasets reais** (rank vs id sequencial são estatisticamente idênticos).
- Regimes na ordinal: **adiado** até casos reais.
- **Quantitativa discreta consolidada** (2026-08-16): inteiros são sempre discreta — o k escolhe o regime (**tabela**: frequência por valor; **histograma**: bins inteiros). Essencial: tabela + mín/máx + moda + **média e mediana**; completa: dp, quartis, % de zeros, ECDF. **Soma total: fora** (leitura de negócio, não de distribuição). Contínua = numérico com casas decimais. Regime histograma inclui **tabela de extremos de frequência** (5 mais + 5 menos frequentes; `discrete_extremes_levels`; empates na menor freq → valores mais extremos primeiro; valores do meio do ranking só via opt-in `discrete_extremes_include_middle`).
- **Quantitativa contínua consolidada** (2026-08-16): essencial = resumo de cinco números + média (mín, q1, mediana, média, q3, máx) + histograma + **tabela de extremos de valor** (5 maiores/5 menores com contagem; `continuous_extremes_levels`); completa = quantis de cauda, dp, IQR, CV, assimetria, curtose, **atípicos 1,5×IQR** (descritos, nunca julgados), ECDF, boxplot. Narrativa traduz forma em palavras. Pegadinha registrada: nyc `price` é inteiro → reclassificação para contínua.
- **Narrativas (data-to-text)**: núcleo de templates determinísticos pt-BR/en (tom acadêmico no MVP) + plug opcional de LLM **local e gratuito** (Ollama; nunca API de nuvem por padrão) que só reformula/traduz texto pronto, com **trava de números** (validação determinística pós-geração). Subpáginas aprovadas para tipos **e regimes**.

## Estado (2026-08-16, fim do dia)

Estrutura e taxonomia implementadas; inferência, backends e análises ainda são stubs (`NotImplementedError`). **Binária, discreta e contínua consolidadas** (§2.5, §3.1 e §3.2 do fluxo, cada uma com subpágina em docs/tipos/). Fila de discussão: **nominal cauda longa** é a próxima, depois ordinal, textual, temporal. Depois: implementar `core/inference.py` + `PandasBackend` e rodar o benchmark nos 40 datasets. Ideia aceita em avaliação: rodar ydata-profiling (concorrente mais próximo) nos 40 como baseline de comparação.

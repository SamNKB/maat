# maat — contexto permanente do projeto

Biblioteca de **análise descritiva de dados** sobre **pandas e PySpark** com a mesma API, guiada pela taxonomia de variáveis. Objetivo declarado pelo dono: *"ajudar qualquer pessoa no mundo a fazer análises descritivas"*.

- Repositório público: https://github.com/SamNKB/maat (conta `SamNKB`)
- Página viva (GitHub Pages, serve `docs/`): https://samnkb.github.io/maat/fluxo-interativo.html
- Diretório local: `C:\projetos\maat` — **fora do OneDrive** (movido em 2026-08-16 por causa dos ~3,5 GB de datasets)

---

## 1. Como trabalhar neste projeto

- **Implementar junto, nunca em lote assíncrono** *(decisão de 2026-08-16)*. O Sam prefere estar presente em cada obstáculo, um de cada vez, a revisar uma fila de decisões acumuladas: *"eu dedicado e analisando cada um dos obstáculos que vão surgindo, individualmente, acredito ser mais eficiente do que tomar amanhã 50 decisões sem poder me aprofundar em cada uma"*. Vale também para a implementação — ela gera dezenas de micro-decisões (binning do histograma, coluna toda nula, erro de parse) que moldam o produto tanto quanto as grandes. **Não implementar módulos inteiros autonomamente**; avançar em incrementos pequenos durante a sessão, parando no obstáculo para discutir.
- **Construção conjunta, não entrega pronta.** O Sam (dono) decide o design. Consultar **a cada decisão de design**: apresentar opções com exemplos concretos e aguardar a escolha antes de consolidar em código ou documentação. Ele já pediu isso explicitamente ("ainda não saia fazendo nenhuma definição, estamos construindo juntos"). Usar `AskUserQuestion` para as escolhas.
- **Ele pergunta quando não entende um termo** ("o que você entende por soma total?", "de qual variável você está falando?") — antecipar explicando o conceito com número real antes de perguntar.
- **Exemplos concretos sempre.** Nada de "uma variável categórica": usar `Churn` do telco, `SibSp` do titanic, `price` do nyc. Ele reclamou explicitamente da falta de exemplos.
- **Siglas devem estar explicadas** onde aparecem (`k` = nº de valores distintos; `n` = nº de linhas). Ele reclamou disso no grafo interativo.
- **Verificar números antes de citar.** Já publiquei uma tabela errada (afirmei 11 nulos em `Churn`; os 11 em branco estão em `TotalCharges`). Rodar `python scripts/benchmark_examples.py` ou um cálculo direto antes de escrever qualquer número na documentação.
- **Commit + push a cada bloco concluído.** Mensagem em pt-BR, com o "porquê" da decisão.
- **Responder em português brasileiro**, com acentuação correta.
- **Auditar TODA a documentação a cada consolidação** (aprendizado de 2026-08-16, quando README e docstrings ficaram defasados). Checklist obrigatório ao consolidar um tipo:
  1. `docs/fluxo-de-analises.md` — a seção do tipo + `maat.Config` (§1.2) + heurísticas (§1)
  2. `docs/tipos/<tipo>.html` — nova subpágina com números reais
  3. `docs/fluxo-interativo.html` — tooltip do nó + `h:"tipos/<tipo>.html"` para o clique
  4. `README.md` — taxonomia e status
  5. `src/maat/analysis/*.py` — docstring do stub reflete a decisão
  6. `src/maat/core/taxonomy.py` — enums, se houver regime novo
  7. Este `CLAUDE.md` — decisão + estado

---

## 2. Onde as coisas moram

| Caminho | O que é |
|---|---|
| `docs/fluxo-de-analises.md` | **O mapa conceitual — ler antes de qualquer trabalho de design.** §0 princípios · §1 fluxo + `maat.Config` · §2 qualitativas · §3 quantitativas · §4 temporais · §5 bivariadas · §6 contrato de saída · §7 narrativas · §8 questões em aberto |
| `docs/fluxo-interativo.html` | Grafo arrastável (22 nós). Hover = resumo; clique = subpágina. HTML autocontido, sem build |
| `docs/tipos/*.html` | Subpágina por tipo **consolidado** (modelo: `binaria.html`). Criar junto da consolidação |
| `docs/identidade-visual.md` | Paleta + tipografia; tokens em `assets/design-tokens.css`, amostra em `assets/palette.svg` |
| `datasets/README.md` | Manifesto dos 40 datasets (dados fora do git) |
| `scripts/benchmark_examples.py` | Reproduz todos os números citados na documentação |
| `scripts/download_datasets.py` / `download_gov_datasets.py` | Re-download do benchmark |
| `src/maat/` | `core/` (taxonomy, inference, profile) · `backends/` (base, pandas, spark) · `analysis/` · `viz/` |

---

## 3. Princípios (decididos, valem para tudo)

1. **A inferência propõe, o usuário dispõe** — todo tipo é sobrescrevível; ambiguidades são marcadas, nunca decididas em silêncio.
2. **O maat descreve, não julga** — mostra o que o dado revela agora: contagens, proporções, amostras. Sem quality gates, sem limiares de alerta, sem policiar a codificação do usuário. *(Decisão do Sam: "não somos responsáveis por como o usuário define os dados dele"; "o que fazer com esse resultado é a cargo do usuário".)*
   - **Corolário — mostrar é obrigação, agir é do usuário**: "não julgar" ≠ "esconder". Se o dado tem problema visível, o maat mostra o **fato** e o usuário decide se corrige; omitir deixaria um dataset ruim passar. Condição: toda detecção usa **critério determinístico e explícito, declarado junto do resultado** — nunca inferência difusa ou semelhança aproximada.
3. **Duas camadas em todo perfil** — **essencial** (qualquer pessoa lê) e **completa** (profundidade estatística). Medidas que exigem contexto estatístico (razões, entropia, curtose) moram na completa. *(Motivo dado pelo Sam: "pessoal de produtos tem dificuldade de fazer uma divisão".)*
4. **O custo mora no backend** — agregações no motor (pandas/Spark); a camada visual recebe só dados pré-agregados. No Spark: `approxQuantile` com erro reportado; amostragem para visuais de dispersão.
5. **Narrativas com números garantidos** — templates determinísticos; LLM só reformula, sob trava de validação.

---

## 4. Decisões consolidadas (não rediscutir sem o Sam pedir)

### Taxonomia e classificação
- Qualitativa (nominal / ordinal / binária) · Quantitativa (discreta / contínua) · **Temporal como tipo de primeira classe** (instante / duração) que **se decompõe** em derivadas qualitativas (mês, dia da semana, hora) e quantitativas. *(Motivo: data é eixo contínuo + componentes cíclicos categóricos ao mesmo tempo — o Sam nunca conseguiu encaixá-la em quali/quanti, e essa é a resposta do projeto.)*
- **Regimes de cardinalidade** — modificador que escolhe a estratégia **dentro** do tipo, não um tipo novo. Nominal: `categórico` / `cauda longa` / `textual`. Discreta: `tabela` / `histograma`.
- **Limiares são parâmetros do usuário** (`maat.Config`), incluindo `inference_sample_size`. A amostra decide a **rota**; as contagens finais vêm da base inteira. *(Decisão do Sam: "o usuário pode especificar quantos níveis quer que a aplicação valide antes de decidir o que é alto ou baixo".)*

### Binária — consolidada 2026-08-16 (§2.5)
- **Essencial**: tabela de frequência com o ausente como linha própria (absoluto, % do total, % dos válidos). *(O Sam pediu tabela de frequência com valores absolutos e lembrou dos nulos.)*
- **Completa**: nível dominante + razão de balanceamento.
- **Fora**: intervalo de confiança (é inferência, não descrição); detecção de par semântico e checagem de codificação (o maat não julga codificação); alertas por limiar (quality gate é outra ferramenta).
- Um 3º valor distinto não gera aviso — a coluna deixa de ser binária e vira nominal. É rota, não alerta.

### Nominal em regime cauda longa — consolidada 2026-08-16 (§2.2)
- **Essencial**: **top-10 + linha "Outros"** (`long_tail_top_n`, e a linha declara quantos níveis agrega); **concentração** (níveis para 50%/80%/95% — "36 de 221 bairros concentram 80%"); k, singletons e **contagem de grupos de variantes de grafia**.
- **Completa**: Herfindahl, entropia normalizada, lista dos grupos de variantes, cauda completa sob demanda.
- **Variantes de grafia: o maat MOSTRA** (Câmara: `UBER…LTDA.` 10.267 + `Uber…Ltda.` 8). *(Princípio dado pelo Sam: "se o dataframe está ruim, você mostra e o usuário toma uma ação em cima de corrigir ou não" — com a condição de **critérios claros**.)* Critério determinístico e declarado: minúsculas + sem acentos + espaços colapsados + bordas aparadas. **Sem semelhança aproximada.** O maat nunca une, corrige nem sugere correção.

### Ordinal — consolidada 2026-08-16 (§2.3)
- **Tipo próprio que herda toda a análise da nominal** (inclusive regimes); sem ordem, degrada para nominal e informa.
- **O que a ordem habilita, honestamente**: só duas medidas — **acumulada na ordem natural** ("46,5% dos vinhos até nota 5") e **categoria mediana/quartis** (wine: moda 5, **mediana 6**). Tabela ordenada é **cosmética**. **Média é inválida**, mesmo com níveis numéricos. *(O Sam desafiou: "qual métrica dependeria de fato da ordenação?" — a lista curta é a resposta.)*
- Não confundir a acumulada ordinal (pela escala, "quanto está abaixo daqui?") com o acumulado do Pareto na cauda longa (por frequência, "quantos níveis dominam?").
- **Ordem só por caminhos determinísticos**: declarada em `ordinal_levels`, ou número inicial no rótulo (`5-14 years`). **Fora**: dicionário de escalas e coluna irmã numérica (adult `education.num`) — risco de erro silencioso por idioma/cultura, desproporcional para duas medidas.

### Quantitativa discreta — consolidada 2026-08-16 (§3.1)
- **Inteiros são sempre discreta**, independente da cardinalidade; o `k` escolhe o **regime**: `tabela` (k ≤ `max_discrete_levels`, frequência por valor exato) ou `histograma` (bins inteiros).
- **Essencial**: tabela + mín/máx + moda + **média e mediana** (o par revela assimetria sem jargão).
- **Completa**: desvio padrão, quartis, % de zeros, ECDF.
- **Fora**: **soma total** — significativa, mas é leitura de negócio, não de distribuição.
- Regime histograma tem **tabela de extremos de frequência**: `discrete_extremes_levels` (default 5) mais frequentes + mesmos menos frequentes; empates na menor frequência desempatados pelos **valores mais extremos**. Valores do meio do ranking só via opt-in `discrete_extremes_include_middle` (o histograma já retrata o corpo).

### Quantitativa contínua — consolidada 2026-08-16 (§3.2)
- Classificação: numérico **com casas decimais**.
- **Essencial**: resumo de cinco números + média (mín, q1, mediana, média, q3, máx) + histograma + **tabela de extremos de valor** (`continuous_extremes_levels`, n maiores e n menores com contagem de ocorrências).
- **Completa**: quantis de cauda (p1/p5/p95/p99), dp, IQR, CV, assimetria, curtose, **atípicos pela regra 1,5×IQR** (descritos, nunca chamados de erro), ECDF, boxplot.
- Narrativa traduz a forma em palavras; quando média ≫ mediana, sugere escala logarítmica.

### Narrativas (data-to-text) — decidida 2026-08-16 (§7)
- **Núcleo**: templates determinísticos em **pt-BR e inglês**, tom **acadêmico** no MVP (caso motivador: quem escreve TCC).
- **Plug opcional**: LLM **local e gratuito** (Ollama — Llama 3.2 3B, Gemma 3 4B, Qwen 2.5 3B). **Nunca API de nuvem por padrão** — o dado não sai da máquina. *(Escolha explícita do Sam: "quero usando modelos gratuitos localmente".)*
- O LLM **não gera análise**: só reformula/traduz texto já pronto — foi assim que resolvemos o problema de idiomas que o Sam levantou.
- **Trava de números**: após reformular, validar que todos os números do original aparecem intactos; se mudou, descartar e usar o template com aviso.

### Documentação e identidade
- **Subpáginas por tipo e por regime** (aprovado), com selo de status, camadas, "fora por decisão" com porquês, narrativa de exemplo e galeria de casos reais do benchmark.
- **Identidade Blade Runner**: void navy `#0A0E1A`, panel `#101828`, **neon cyan `#00E5FF` (a cor do maat)**, ice `#E6F7FF`; secundárias magenta `#FF2E88` (movimento/arestas), violet `#9D4EDD` (decisões), steel/mist (neutros); terciárias **só semânticas** — amber `#FFB03A` (aviso), mint `#3DF5C6` (sucesso), red `#FF4757` (erro).
- **Fontes aprovadas**: Rajdhani (títulos/diagramas) + Space Grotesk (corpo) + JetBrains Mono (código/dados); Share Tech Mono como acento opcional.

---

## 5. Pendências e questões em aberto

- **Próxima na fila de discussão: nominal em regime textual** (§2.4) — `name` do nyc (k/n=0,98), SMS spam, descrições do wine-reviews. Decisões previstas: quais checagens de regex entram no MVP (questão nº 6), tamanho das amostras dirigidas, e se a máscara de caractere fica na essencial.
- Depois: **temporal** (instante e duração); então bivariadas.
- **Subtipo `rank`** (ordinal com k ≈ n, ex.: colocação de maratona): decidido criar, mas **aguarda datasets reais**. Desafio central: rank e id sequencial são estatisticamente idênticos — o desempate teria de vir do nome da coluna, e na dúvida marcar como suspeita.
- **Regimes de cardinalidade na ordinal**: adiado até casos reais.
- Questões 2, 3, 4 e 6 da §8 do fluxo seguem abertas (ordem das ordinais, erro do `approxQuantile`, formato do relatório, bateria de regex do textual).
- **Implementação**: `core/inference.py`, backends e análises ainda são stubs `NotImplementedError`. Plano combinado: implementar inferência + `PandasBackend`, rodar nos 40 datasets, e usar os resultados para resolver o `rank` e calibrar limiares.
- Ideia aceita, ainda não executada: rodar **ydata-profiling** nos 40 datasets como baseline de comparação.

---

## 6. Concorrência (levantada em 2026-08-16)

O mais próximo é **ydata-profiling** (ex-pandas-profiling): perfil por coluna, ausentes, distribuições, relatório HTML, suporte parcial a Spark — cobre ~70% da ideia. Vizinhos: Sweetviz (comparação de datasets), DataPrep.EDA (velocidade), D-Tale (GUI), AutoViz/Lux. Deequ e Great Expectations são *quality gates* — exatamente o que decidimos **não** ser.

**Diferenciais do maat** (os 30% que ninguém cobre): regimes de cardinalidade com **perfil textual** (máscaras, regex de sujeira, amostras de ofensores) em vez de truncar alta cardinalidade; **temporal como tipo de primeira classe** com decomposição cíclica; **camada essencial** legível por não-técnicos; **narrativas prontas** para trabalho acadêmico; filosofia descreve-não-julga.

---

## 7. Ambiente e armadilhas operacionais (Windows)

- **Shell**: PowerShell. `&&` não funciona; usar `;` ou `if ($?)`. Mensagens de commit multilinha via here-string `@'...'@` com `'@` na coluna 0. **Nunca usar aspas duplas dentro da mensagem de commit** — o PowerShell 5.1 re-quebra o argumento ao passar para o git e o commit falha com `pathspec ... did not match`.
- **`gh` não está no PATH** desta sessão: chamar `& "C:\Program Files\GitHub CLI\gh.exe"`. Autenticado como `SamNKB`.
- **Python 3.12** com **pandas 3.0.5** instalado. **pytest NÃO está instalado** (`pip install -e ".[pandas,dev]"` para testar).
- **Kaggle**: cliente via `python -m kaggle`; autenticação OAuth já feita (`kaggle auth login`). Alguns datasets retornam 403 na API e exigem espelho alternativo (aconteceu com Pima Diabetes e FIFA 19).
- **API SGS do Banco Central**: séries diárias exigem janela `dataInicial`/`dataFinal` (senão HTTP 406). A série 432 (meta Selic diária) falha mesmo com janela — usar a **4390** (mensal).
- **Datasets nunca entram no git**: `datasets/` está no `.gitignore` (só o README sobe). Três arquivos passam de 100 MB — o limite do GitHub — incluindo um de 677 MB.
- **Testar HTML localmente**: `.claude/launch.json` define o servidor `maat-docs` (porta 8777, serve `docs/`). `preview_start` com `{name: "maat-docs"}` e navegar para `http://localhost:8777/...`. Abrir por `file://` renderiza só snapshot estático.
- **Mermaid**: os `<br/>` nos rótulos estão corretos (sintaxe do mermaid, não HTML quebrado) — o Sam já estranhou isso uma vez.
- **Arquivos-chave do benchmark** (nomes não óbvios): telco `WA_Fn-UseC_-Telco-Customer-Churn.csv` · titanic `Titanic-Dataset.csv` · adult `adult.csv` · nyc `AB_NYC_2019.csv` · netflix `netflix_titles.csv` · ecommerce `data.csv` (encoding `latin-1`) · wine `winequality-red.csv` · kc `kc_house_data.csv` · stroke `healthcare-dataset-stroke-data.csv`.

---

## 8. Números reais mais usados nos exemplos

| Coluna | Dataset | Fatos |
|---|---|---|
| `Churn` | telco | n=7.043 · No 5.174 (73,5%) · Yes 1.869 (26,5%) · sem nulos · razão 2,8:1 |
| `TotalCharges` | telco | contínua presa em string — 11 valores em branco |
| `MonthlyCharges` | telco | mediana 70,35 · média 64,76 · q1 35,50 · q3 89,85 · assimetria -0,22 · zero atípicos |
| `SibSp` | titanic | k=7 · 68,2% zeros · média 0,52 · mediana 0 · dp 1,10 · sem valores 6 e 7 |
| `Parch` | titanic | 76,1% zeros |
| `PassengerId` | titanic | k = n = 891 (identificador) |
| `Quantity` | ecommerce | k=722 · mediana 3 · média 9,6 · 1,96% negativos · mín/máx ±80.995 · top: 1 (27,4%), 2 (15,1%), **12 (11,3%)** |
| `price` | nyc-airbnb | n=48.895 · mediana 106 · média 152,72 · máx 10.000 (×3) · **0 (×11)** · assimetria 19,1 · atípicos 6,08% · **é inteiro → reclassificar para contínua** |
| `name` | nyc-airbnb | k/n = 0,98 · comprimento mediana 37, máx 179 (regime textual) |
| `neighbourhood` | nyc-airbnb | k=221 · 36 bairros somam 80% (cauda longa) |
| `quality` | wine | inteiro k=6 (3…8), moda 5 (42,6%) — **é Likert, reclassificar para ordinal** |
| `education` / `native.country` | adult | k=16 (categórico) / k=42, dominante 89,6% |
| `date_added` | netflix | string, 99,9% parseia · 2008 → 2021 |
| `zipcode` | kc-house | int64 k=70 · média 98.078 (número sem sentido — suspeita) |

---

## 9. Histórico da construção (2026-08-16, sessão única)

1. Estrutura do projeto, taxonomia e primeiro `fluxo-de-analises.md`.
2. Sam introduz a ideia de **regimes por cardinalidade** e o perfil textual com regex → vira conceito central.
3. Publicação no GitHub; benchmark de 30 datasets do Kaggle.
4. Identidade visual Blade Runner; escolha das fontes (opção A).
5. Grafo interativo (`fluxo-interativo.html`) + GitHub Pages.
6. Princípios "descreve, não julga" e "duas camadas" nascem das correções do Sam sobre a binária.
7. 10 datasets de governo BR; exemplos da documentação passam a usar números reais verificados.
8. Subpáginas por tipo (modelo aprovado com a binária).
9. Arquitetura de narrativas (templates + Ollama local + trava de números).
10. Discreta e contínua consolidadas; auditoria que corrigiu README, enums e docstrings defasados.
11. `CLAUDE.md` vira registro completo (decisões, porquês, ambiente, histórico).
12. Cauda longa consolidada — o corolário "mostrar é obrigação, agir é do usuário" nasce da posição do Sam sobre variantes de grafia.
13. Links de origem (Kaggle e fontes de governo) no manifesto e nas subpáginas.
14. Ordinal consolidada — o Sam desafia "qual métrica depende de fato da ordem?" e a resposta honesta (duas medidas) define um desenho enxuto.

**Consolidados até aqui**: binária (§2.5) · cauda longa (§2.2) · **ordinal (§2.3)** · discreta (§3.1) · contínua (§3.2) — cada um com subpágina em `docs/tipos/`.

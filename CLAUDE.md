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
  7. `tests/` — cada decisão consolidada tem teste que a protege, citando a seção
  8. Este `CLAUDE.md` — decisão + estado

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
| `scripts/run_ydata_baseline.py` / `comparar_com_ydata.py` | Baseline competitivo (exige ambiente isolado) |
| `scripts/custo_bateria_textual.py` / `sinais_temporais.py` | Medições que embasaram as decisões |
| `scripts/gera_explorador.py` | Explorador navegável do repositório |
| `src/maat/` | ver §2b — a organização real do código |
| `tests/fixtures/` | fatias reais do benchmark (114 KB versionados) que preservam a sujeira do mundo real |

---

## 2b. Como o código está organizado (implementado em 2026-08-23)

| Módulo | Papel |
|---|---|
| `core/config.py` | ~20 parâmetros do usuário, com defaults. Nada de limiar fixo no código |
| `core/meta.py` | `ColumnMeta`: os sinais que o backend calcula (densidade, monotonia, dígito verificador, evidência de formato de data) |
| `core/signals.py` | Detecções determinísticas **compartilhadas** pelos dois backends: CPF/CNPJ, normalização de variantes, as 15 checagens de texto, sentinelas de data |
| `core/inference.py` | O roteamento da §1 — **código puro** sobre `ColumnMeta`, sem pandas nem Spark |
| `backends/` | `base.py` é o contrato; pandas e Spark implementam. Todo custo mora aqui |
| `analysis/` | Uma função por tipo consolidado; recebe agregados, devolve `ColumnProfile` |
| `narrative/` | Templates pt-BR/en + a trava de números (`numeros_preservados`) |
| `render.py` | Os 4 formatos sobre a estrutura em memória |

**Diferenças reais entre os backends** (descobertas rodando, não previstas):
- pandas 3.x usa **PyArrow** para strings, e o motor RE2 **não suporta retrovisor** — `(.){3,}` precisa de fallback para o `re` do Python (`PandasBackend._contains`).
- Spark 4 usa **modo ANSI** por padrão: `to_timestamp` **levanta exceção** em valor malformado. Usar `try_to_timestamp` + `coalesce` de formatos.
- Spark também recusa retrovisor e lookahead: as checagens `repeticao` e `misto_alfabeto` têm variante própria ou são puladas.
- `approxQuantile` gera divergência esperada: no titanic, 118 atípicos no Spark contra 116 no pandas. O campo `quantile_error` reporta isso.

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

### Contrato de saída — consolidada 2026-08-17 (§6)
- **O contrato é a estrutura em memória; formatos são renderizadores.** Encerra a questão nº 4 (aberta desde o dia 1): nem HTML nem JSON primeiro — `DatasetProfile`/`ColumnProfile` primeiro.
- `ColumnProfile`: name · inferred_type · quality · **essencial** · **completa** (camadas são campos, não opção de exibição) · checks · viz_suggestions · notes · narrative. `Check` carrega o **critério em palavras** junto do resultado (exigência do §0.2).
- **4 formatos no MVP como métodos dedicados** (escolha do Sam, pelo autocomplete), todos com parâmetro `camada`: `to_json` (0,63× tokens, compacto por padrão), `to_yaml` (0,73×), `to_markdown` (**0,30×**, default `camada="essencial"` — caso de uso: mandar para agente de IA), `to_html`.
- **Medição que corrigiu a hipótese**: o Sam supôs YAML mais barato que JSON; com tiktoken real, **JSON compacto (0,63×) ganha do YAML (0,73×)**; Markdown esmaga ambos. Ressalva registrada: o Markdown é seletivo, parte da economia é por ser mais enxuto.
- **Adiados com a porta aberta**: perfil como tabela Parquet (destrava comparar perfis no tempo → drift), esquema interoperável (Frictionless/dbt — viraria insumo de pipeline), SQLite, CSV longo (medido: não economiza nada).

### Temporal — consolidada 2026-08-17 (§4)
- **Ambiguidade dd/mm × mm/dd é o problema central**, descoberto medindo: 39% a 50% dos valores de uma coluna `A/B/AAAA` são individualmente ambíguos. A prova vem da minoria com campo > 12 (`ecommerce`: mm/dd provado por 308.950 valores; `bcb/dolar` e `tesouro`: dd/mm provado). Quatro estados: provado dd/mm, provado mm/dd, **misturados** (provas dos dois lados = corrompido) e **indecidível**.
- **Indecidível → reporta e não escolhe**: declara o impasse e **suspende as análises que dependem do dia** até `date_format`. O pandas escolhe em silêncio; nós dizemos que não dá para saber.
- **Futuro é fato, nunca erro**: `tesouro/Data Vencimento` tem 39,43% no futuro **e está correto**. Substituímos "datas biologicamente impossíveis" (que exige semântica) pela **distribuição de horizonte** (`date_horizons`: 10/20/30/40/50/100 anos) — ideia do Sam, melhor que a alternativa. **Bidirecional desde 2026-08-23** (o Sam notou que só cobria o passado): reporta `passado >N anos` e `futuro >N anos`. No Tesouro isso revela 1.540 vencimentos a mais de 50 anos à frente.
- **Quebras de calendário/dtype** (levantadas pelo Sam, e nenhuma ferramenta examinada reporta): **rebase do Spark** (datas antes de 1582-10-15 mudam de valor entre calendário híbrido e proléptico ao ler Parquet/Avro), **lacuna gregoriana** (05–14/10/1582 não existem), **fora do datetime64[ns]** (antes de 1677-09-21 ou após 2262-04-11 — `1500-01-01` levanta OutOfBoundsDatetime no pandas mas o Spark cobre ano 1–9999), horário inexistente por DST e datas impossíveis (31/02).
- Também: falha de parse, nulos na origem, granularidade real (netflix e BCB são diários disfarçados), datas-sentinela (1900-01-01, epoch, 9999-12-31), amostra dos extremos.
- **Duração** (§4.2): herda a §3.2; unidade inteligente, mediana como resumo principal, negativas reportadas como fato; derivada de duas datas herda a incerteza da origem.
- Medido por `scripts/sinais_temporais.py`.

### Nominal em regime textual — consolidada 2026-08-17 (§2.4)
- **15 checagens de sujeira** + **interface de extensão** (`textual_extra_checks`) desde o MVP. Sugestões do Sam que entraram: `url`, `markdown`, `pix_brcode` (caso real dele em produção: payload PIX em campo de complemento), `base64_longo`, `json_embutido`, `cpf_cnpj_mascara`.
- **Lista de palavrões: RECUSADA** — é juízo de conteúdo, não descrição, e depende de idioma. No lugar entrou `placeholder` (asdasd, xxx, 123123, null): sinal de qualidade sem juízo moral.
- **Amostras dirigidas**: mais curtas, mais longas **e aleatórias** (`textual_sample_size`) — a aleatória mostra o caso típico.
- **Padrão dominante**: aderência **e** amostra das violações juntas. *("contaminações eu gostaria que surgissem nesses relatórios")*. Máscara de caractere na completa.
- **Execução sempre na base inteira** — o Sam rejeitou a alternativa de duas fases (amostra detecta, base conta) mesmo sendo **6× mais rápida** (4,0 s vs 24,2 s em 2,08 mi): ela poderia perder sujeira rara. Exatidão acima de velocidade.
- **Custo medido** (`scripts/custo_bateria_textual.py`): ~11 µs/string; máscara custa 1/3; amostras desprezíveis. Regex única combinada rende só 1,2× — medido e descartado.
- Achados reais: `markdown` disparou 71× em **nomes** do nyc; CPF/CNPJ apareceu 2× em campo de **fornecedor**; 89 URLs no SMS spam.

### Ordinal — consolidada 2026-08-16 (§2.3)
- **Tipo próprio que herda toda a análise da nominal** (inclusive regimes); sem ordem, degrada para nominal e informa.
- **O que a ordem habilita, honestamente**: só duas medidas — **acumulada na ordem natural** ("46,5% dos vinhos até nota 5") e **categoria mediana/quartis** (wine: moda 5, **mediana 6**). Tabela ordenada é **cosmética**. **Média é inválida**, mesmo com níveis numéricos. *(O Sam desafiou: "qual métrica dependeria de fato da ordenação?" — a lista curta é a resposta.)*
- Não confundir a acumulada ordinal (pela escala, "quanto está abaixo daqui?") com o acumulado do Pareto na cauda longa (por frequência, "quantos níveis dominam?").
- **Ordem só por caminhos determinísticos**: declarada em `ordinal_levels`, ou número inicial no rótulo (`5-14 years`). **Fora**: dicionário de escalas e coluna irmã numérica (adult `education.num`) — risco de erro silencioso por idioma/cultura, desproporcional para duas medidas.

### Identificador, código e rank — consolidada 2026-08-17 (§3.3)
- **Três rotas** para números que não são quantidades: **chave** (k≈n → unicidade/colisões), **código** (identifica entidade e se repete: CNPJ, `CO_MUN`, `ideCadastro` → cardinalidade como nominal, **nunca média**) e **rank** (posição).
- **Dicionário de nomes de coluna: RECUSADO** pelo Sam — "inferir nome da coluna é algo sem noção demais, os contextos regionais interferem". Todos os sinais são determinísticos e independentes de idioma.
- **5 sinais no MVP** (+ razão de repetição): dígito verificador CPF/CNPJ (cvm: 100%, controles: 0%), zeros à esquerda, comprimento fixo, densidade `k/(máx−mín+1)` (nyc id: 0,0013), monotonia máxima |Spearman| (videogame Rank × Global_Sales: −0,9996). Medidos por `scripts/sinais_nao_quantidades.py`.
- **Rank**: provado que **nenhum sinal estatístico o separa de id sequencial** (mall/CustomerID tem assinatura idêntica ao Rank do videogame); a exatidão também falhou nos dois sentidos. Decisão: classifica como rank se **|Spearman| ≥ 0,99** (`rank_monotonia_minima`), aceitando o falso positivo do mall. **Mitigação obrigatória por construção**: `VariableType` rejeita RANK sem `rank_reference` — o perfil sempre nomeia a coluna de referência para o engano ficar visível.

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
- 🚧 **Plug de LLM: EM CONSTRUÇÃO, não use como pronto.** O parâmetro `Config.narrative_llm` existe mas **nada o consome** — passar um valor hoje não faz nada. A trava de números (`narrative/numbers.py`) está implementada e testada; falta o cliente.
  - Decisão original: LLM **local e gratuito**, nunca API de nuvem por padrão — o dado não sai da máquina. *(Escolha explícita do Sam: "quero usando modelos gratuitos localmente".)*
  - **Problema levantado pelo Sam em 2026-08-23**: exigir instalação do Ollama contradiz "ajudar qualquer pessoa no mundo" — `pip install` não traz um binário externo + serviço + GB de pesos. Direção proposta (não decidida): contrato **agnóstico**, em que `narrative_llm` aceita qualquer função texto→texto e o maat nunca instala nem gerencia modelo.
  - **Cuidado com licenças**: Llama usa licença própria da Meta (teto de 700M MAU, proibição de treinar concorrentes) — é "open-weights", não open source. No Qwen 2.5, **o 3B e o 72B têm licença própria**; os demais tamanhos (0.5B, 1.5B, 7B, 14B, 32B) são Apache 2.0. O Sam está avaliando o Qwen.
  - **Insight registrado**: os templates inteiros têm ~8 KB (≈50 frases por idioma). Traduzir para um idioma novo pode ser mais simples e melhor que gerar em runtime — determinístico, instantâneo, revisável por falante nativo.
- O LLM **não gera análise**: só reformula/traduz texto já pronto — foi assim que resolvemos o problema de idiomas que o Sam levantou.
- **Trava de números**: após reformular, validar que todos os números do original aparecem intactos; se mudou, descartar e usar o template com aviso.

### Documentação e identidade
- **Subpáginas por tipo e por regime** (aprovado), com selo de status, camadas, "fora por decisão" com porquês, narrativa de exemplo e galeria de casos reais do benchmark.
- **Identidade Blade Runner**: void navy `#0A0E1A`, panel `#101828`, **neon cyan `#00E5FF` (a cor do maat)**, ice `#E6F7FF`; secundárias magenta `#FF2E88` (movimento/arestas), violet `#9D4EDD` (decisões), steel/mist (neutros); terciárias **só semânticas** — amber `#FFB03A` (aviso), mint `#3DF5C6` (sucesso), red `#FF4757` (erro).
- **Fontes aprovadas**: Rajdhani (títulos/diagramas) + Space Grotesk (corpo) + JetBrains Mono (código/dados); Share Tech Mono como acento opcional.

---

## 4b. Fila de decisões que a implementação levantou (2026-08-23)

Enfileiradas em vez de decididas sozinho, conforme combinado. Evidência completa em `docs/limites-da-inferencia.md`.

1. **Chaves estrangeiras** — o maior gap aberto. `movies/userId` (k=346, 87 linhas por valor), `movies/movieId`, `gov-camara/nuDeputadoId` (319 linhas por valor) e `nyc/host_id` são identificadores que **se repetem** e caem em `discreta`. Média de `nuDeputadoId` é tão sem sentido quanto média de CEP, mas nenhum sinal determinístico os separa de uma contagem legítima. Opções: (a) aceitar como limite declarado; (b) admitir um sinal mais fraco (inteiro esparso de magnitude alta com repetição), pegando mais casos ao custo de falsos positivos.
2. **Ano** — `avocado/year`, `netflix/release_year`, `suicide-rates/year` caem em discreta. É ambiguidade genuína (temporal, ordinal ou discreta conforme a pergunta). Manter em discreta e deixar o usuário reclassificar, ou marcar como suspeita?
3. **Data quebrada em colunas** — `hotel-bookings` tem `arrival_date_year` + `_month` + `_day_of_month`. A natureza temporal some. Reconstruir exigiria inferência entre colunas (território das bivariadas, adiadas).
4. **Epoch como inteiro** — `creditcard-fraud/Time` (segundos decorridos) vira discreta. Um timestamp Unix também viraria. Detectar faixas plausíveis de epoch ou deixar?
5. **Exatidão × velocidade no Spark** — a decisão "sempre na base inteira" (§2.4) custa caro em milhões de linhas. A alternativa de duas fases foi medida em 6× mais rápida e **rejeitada** por poder perder sujeira rara. Vale revisitar com o custo medido em mãos?

## 5. Pendências e questões em aberto

- ✅ **TODO o design está fechado** (2026-08-17): tipos, princípios, narrativas e contrato de saída. O que resta é **implementação**.
- **Bivariadas e multivariadas: ADIADAS para o beta** (decisão de 2026-08-17). Motivo medido: explosão combinatória — fifa19 tem 3.916 pares sozinho, os 39 datasets somam 9.412; um relatório assim é ilegível por construção e contradiz a camada essencial. Direção registrada para o beta: **modelo híbrido com IA selecionando os pares pertinentes** (ranqueamento a partir de nomes e perfis univariados) e o **maat calculando deterministicamente** os escolhidos — mesma divisão das narrativas, que mantém os números fora do alcance do modelo. A matriz tipo × tipo da §5 já está desenhada; falta decidir o critério de seleção.
- Depois: implementação (`core/inference.py` + `PandasBackend`), **em incrementos com o Sam presente**.
- **Regimes de cardinalidade na ordinal**: adiado até casos reais.
- Questões 2, 3, 4 e 6 da §8 do fluxo seguem abertas (ordem das ordinais, erro do `approxQuantile`, formato do relatório, bateria de regex do textual).
- **Implementação: FEITA** (2026-08-23). O núcleo roda em pandas **e PySpark**, validado sobre 38 datasets e 609 colunas reais. Único stub restante: `analysis/bivariate.py`, adiado por decisão.
- **Ambiente**: pandas 3.0.5, numpy 2.5.2, pyspark 4.2.0, OpenJDK 17 (`C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot`). O pacote está instalado em modo editável (`pip install -e ".[dev]"`), então `import maat` funciona de qualquer lugar e o `PYTHONPATH` não é mais necessário.
- **ydata-profiling quebrou** com as versões novas (o numba dele exige numpy ≤ 2.3). O baseline já rodou e está salvo em `benchmarks/ydata/`; para refazer, use ambiente isolado (`pip install 'maat[baseline]'` em outro venv).
- ~~Rodar ydata-profiling como baseline~~ → **feito em 2026-08-17**, ver `docs/comparacao-ydata.md`. Resultados locais em `benchmarks/ydata/` (fora do git; refazer com `scripts/run_ydata_baseline.py` + `scripts/comparar_com_ydata.py`).
- **Verificar antes de implementar o regime textual**: o ydata tem análise Unicode de texto (extra opcional) que pode cobrir parte do que planejamos na §2.4 — comparar item a item para não reinventar.

---

## 5b. Retomada — por onde começar na próxima sessão

Duas frentes possíveis; o Sam escolhe:

- **(a) Decisão madura na mesa**: o subtipo `rank`. O benchmark trouxe a evidência que faltava (`videogame-sales/Rank` k=16.598 e `world-happiness/Happiness.Rank` k=155 caem em "identificador" pelas regras atuais). Discussão curta, destrava a questão nº 8.
- **(b) Continuar o design**: regime textual (§2.4) — mas **antes**, comparar item a item com a análise Unicode do ydata (`benchmarks/ydata/*.html`) para não reinventar. Ou temporal (§4), o tipo que motivou o projeto.
- **(c) Implementar**: `core/inference.py` + `PandasBackend`, **em incrementos, com o Sam presente** (ver §1 — nunca em lote).

## 6. Concorrência (levantada em 2026-08-16, medida em 2026-08-17)

O mais próximo é **ydata-profiling** (ex-pandas-profiling): perfil por coluna, ausentes, distribuições, relatório HTML, suporte parcial a Spark — cobre ~70% da ideia. Vizinhos: Sweetviz (comparação de datasets), DataPrep.EDA (velocidade), D-Tale (GUI), AutoViz/Lux. Deequ e Great Expectations são *quality gates* — exatamente o que decidimos **não** ser.

**Medido em 2026-08-17** (`docs/comparacao-ydata.md`): sobre 625 colunas reais, o ydata usa **6 tipos** e nossas regras produzem **9 rotas**. As 301 colunas `Numeric` dele viram 130 discretas-histograma + 126 contínuas + 24 discretas-tabela + **21 identificadores**; as 121 `Text` viram 82 cauda longa + 39 textuais. **Sem moat técnico**: ele tem análise Unicode, correlações, alertas e maturidade de casos-limite. O único ponto sem equivalente no mercado é a **narrativa acadêmica em pt-BR com trava de números**. A aposta é de posicionamento (não-estatísticos, português, texto pronto, descreve-não-julga), não de tecnologia.

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
9. Arquitetura de narrativas (templates + trava de números; o plug de LLM segue em construção).
10. Discreta e contínua consolidadas; auditoria que corrigiu README, enums e docstrings defasados.
11. `CLAUDE.md` vira registro completo (decisões, porquês, ambiente, histórico).
12. Cauda longa consolidada — o corolário "mostrar é obrigação, agir é do usuário" nasce da posição do Sam sobre variantes de grafia.
13. Links de origem (Kaggle e fontes de governo) no manifesto e nas subpáginas.
14. Ordinal consolidada — o Sam desafia "qual métrica depende de fato da ordem?" e a resposta honesta (duas medidas) define um desenho enxuto.
20. **2026-08-17** — §6 (contrato de saída) consolidada. **Design completo; começa a implementação.**
19. **2026-08-17** — bivariadas adiadas para o beta com a explosão combinatória medida; direção do modelo híbrido com IA registrada.
18. **2026-08-17** — §4 (temporal) consolidada: a ambiguidade dd/mm é medida e o indecidível passa a ser declarado; entram as quebras de calendário do Spark. **Design de todos os tipos fechado.**
17. **2026-08-17** — §2.4 (textual) consolidada: 15 checagens medidas em dados reais, palavrões recusados, execução sempre na base inteira.
16. **2026-08-17** — §3.3 consolidada: identificador vira três rotas (chave/código/rank); o dicionário de nomes é recusado e a decisão passa a apoiar-se em sinais medidos.
15. **2026-08-17** — baseline competitivo executado: ydata-profiling sobre 39 datasets, 625 colunas comparadas (`docs/comparacao-ydata.md`). Um erro de metodologia (modo mínimo desativa inferência de datas) quase virou conclusão falsa a nosso favor e foi corrigido antes de publicar.

**Consolidados até aqui**: binária (§2.5) · **categórico (§2.1)** · cauda longa (§2.2) · ordinal (§2.3) · textual (§2.4) · discreta (§3.1) · contínua (§3.2) · identificador/código/rank (§3.3) · temporal (§4) — todos com subpágina em `docs/tipos/` — cada um com subpágina em `docs/tipos/`.

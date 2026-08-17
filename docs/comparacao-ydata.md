# Baseline competitivo: maat × ydata-profiling

Rodamos o **ydata-profiling 4.18.4** — a ferramenta de mercado mais próxima do que o maat propõe — sobre os 40 datasets do benchmark, para trocar opinião por evidência. Resultados locais em `benchmarks/ydata/` (fora do git); reproduza com:

```bash
python scripts/run_ydata_baseline.py
python scripts/comparar_com_ydata.py
```

**Cobertura**: 39 datasets perfilados (o do IBGE é JSON, sem CSV), **625 colunas** classificadas pelas duas taxonomias.

---

## Metodologia — e um erro que quase virou conclusão falsa

A primeira rodada usou o **modo mínimo** do ydata em bases grandes (acima de 30 mil linhas), por causa do tempo de execução. Isso produziu um resultado sedutor e **errado**: apenas 6 colunas detectadas como data, com o ydata aparentemente falhando em ISO 8601 (`2025-06-03` no CVM) e no formato brasileiro (`datEmissao`), enquanto acertava `September 25, 2021` do netflix.

Testando o mesmo dado nos dois modos, a causa apareceu: **o modo mínimo desativa a inferência de datas**. Em modo completo o ydata acerta os dois formatos. Era limitação da nossa configuração, não da ferramenta.

A comparação final, portanto, **não usa o tipo do relatório**: reinferimos o tipo de todas as 625 colunas com o `ProfilingTypeSet` completo, igual para todos. Depois de corrigir, as datas detectadas subiram de 6 para 19.

> Lição registrada: qualquer afirmação competitiva precisa passar por um teste que possa refutá-la. Esta quase não passou.

---

## Resultado: quantos baldes cada um usa

| ydata-profiling (6 tipos) | | maat (9 rotas, regras da §1 e §2.0) | |
|---|---|---|---|
| Numeric | 301 | discreta[histograma] | 130 |
| Categorical | 171 | continua | 126 |
| Text | 121 | nominal[categórico] | 91 |
| DateTime | 19 | nominal[cauda-longa] | 87 |
| Boolean | 12 | binária | 54 |
| Unsupported | 1 | discreta[tabela] | 53 |
| | | nominal[textual] | 39 |
| | | temporal-instante | 23 |
| | | identificador | 21 |

### Onde o ydata agrupa e o maat separa

**`Numeric` (301 colunas) → 4 rotas distintas no maat:**

| Rota do maat | Colunas | O que muda na prática |
|---|---|---|
| discreta[histograma] | 130 | contagem com muitos valores → bins inteiros + tabela de extremos |
| contínua | 126 | medição → cinco números + extremos de valor |
| discreta[tabela] | 24 | contagem com poucos valores → frequência por valor exato, revelando buracos |
| **identificador** | 21 | `id`, `PassengerId`, `CustomerID` → fora das estatísticas; média de id não significa nada |

O ydata calcula média, desvio e histograma igualmente para os 301 — inclusive para as 21 colunas de identificador.

**`Text` (121 colunas) → 2 rotas:** 82 caem em cauda longa (frequência ainda informativa: `neighbourhood`, fornecedores) e 39 em regime textual (frequência inútil, `k ≈ n`: nomes, e-mails). São análises opostas sob o mesmo rótulo.

**`Categorical` (171) → 5 rotas**, incluindo 42 binárias (que ganham saída enxuta) e 29 contagens inteiras de baixa cardinalidade.

---

## O que o ydata tem e nós não

Honestidade na direção contrária, para não construirmos sobre uma comparação vaidosa:

- **Análise Unicode de texto** (extra opcional) — cobre parte do que planejamos no regime textual (§2.4). Precisamos verificar item a item **antes** de implementar o nosso, para não reinventar.
- **Seção de Alerts** — alta correlação, assimetria, zeros, constantes, ausentes. Nós **recusamos** isso por princípio (§0.2). É posicionamento oposto, não lacuna: parte dos usuários quer o alerta pronto.
- **Correlações e interações** entre colunas, prontas. Nossas bivariadas (§5) ainda são projeto.
- **Anos de tratamento de casos-limite**, amostras de linhas, duplicatas, missing diagrams. Competir em amplitude é jogo perdido.

---

## O que o benchmark nos ensinou sobre o próprio maat

**1. A questão do subtipo `rank` apareceu sozinha nos dados** (§8, item 8 — estava esperando exatamente isto):

| Coluna | k | O que nossas regras atuais dizem |
|---|---|---|
| `videogame-sales / Rank` | 16.598 | identificador |
| `world-happiness / Happiness.Rank` | 155 | identificador |

São colocações — **rank de verdade**, classificadas como identificador porque são inteiros densos e únicos. É a confirmação empírica de que a distinção precisa vir de fora da distribuição (o nome da coluna diz "Rank"). **Decisão pendente para o Sam**, não tomada aqui.

**2. Identificadores são 3,4% das colunas do benchmark** (21 de 625) — pequeno o bastante para não dominar o relatório, frequente o bastante para justificar a rota própria.

**3. Contagem × medição divide as numéricas quase ao meio** (154 discretas contra 126 contínuas), o que sustenta a decisão da §3.1 de tratá-las com saídas diferentes.

---

## Conclusão honesta

Não temos moat técnico. O ydata-profiling é maduro, tem features que não temos e cobre casos-limite que ainda vamos descobrir. O que temos é **granularidade taxonômica** (9 rotas contra 6 baldes, com consequências reais no que se calcula), **duas camadas de leitura**, e — o único ponto onde não encontramos equivalente no mercado — **narrativa acadêmica em português com trava de números**.

A aposta continua sendo de posicionamento, não de tecnologia: análise descritiva para quem não é estatístico, em português, que entrega o texto pronto e mostra a sujeira do dado sem dar veredito.

---

## Limitações desta comparação

- Amostra de até 100 mil linhas por dataset; o objetivo é comparar comportamento por coluna, não escala.
- As rotas do maat foram obtidas **aplicando mecanicamente as regras documentadas** (`scripts/comparar_com_ydata.py`) — o maat ainda não está implementado, então isto é um ensaio das nossas heurísticas, não a saída do produto.
- Instalar o ydata-profiling **rebaixou o pandas de 3.0.5 para 2.3.3** (ele ainda não suporta pandas 3.x).
- Comparamos **classificação de tipos**, que é só a porta de entrada. A qualidade das análises e da apresentação — onde apostamos nosso diferencial — não é medida aqui.

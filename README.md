# maat

> Análise descritiva de dados para qualquer pessoa, em qualquer escala.

**maat** é uma biblioteca de análise descritiva que opera sobre **pandas** (dados locais) e **PySpark** (dados distribuídos) com a mesma API. O nome vem de Maat, a deusa egípcia da verdade, do equilíbrio e da ordem — o que uma boa análise descritiva deve revelar nos dados.

🖥️ **Documentação viva**: [grafo interativo do fluxo de classificação](https://samnkb.github.io/maat/fluxo-interativo.html) — arraste os nós, passe o mouse para ver exemplos reais, clique para abrir a página detalhada de cada tipo.

```python
import maat

profile = maat.describe(df)               # pandas ou PySpark, mesma API
profile.to_markdown(camada="essencial")   # para um agente de IA ou para o TCC
profile.to_html("relatorio.html")         # para ler
```

O que sai, sem você escrever nada:

> A variável **Fare** é quantitativa contínua, observada em 891 registros, sem valores ausentes, variando de 0,00 a 512,33. A média (32,20) supera a mediana (14,45), indicando distribuição assimétrica à direita — valores extremos elevam a média, e a mediana representa melhor o caso típico. Pela regra de 1,5×IQR, 116 observações (13,0%) são atípicas.

## Por que existe

Ferramentas de perfilamento agrupam colunas em poucos baldes. Medindo 625 colunas reais, o `ydata-profiling` usa **6 tipos** e o maat produz **9 rotas** — e a diferença muda o que se calcula ([comparação completa](docs/comparacao-ydata.md)):

- As 301 colunas que ele chama de `Numeric` viram, aqui, 130 contagens de alta cardinalidade, 126 medições contínuas, 24 contagens de baixa cardinalidade e **21 identificadores** — para os quais média e histograma não significam nada.
- As 121 colunas `Text` viram 82 em **cauda longa** (onde a frequência ainda informa) e 39 em **regime textual** (onde `k ≈ n` torna a frequência inútil e a string vira o objeto de análise).

## Filosofia

Toda análise parte de uma pergunta: **que tipo de variável é essa?**

```
Variável
├── Qualitativa (categórica)
│   ├── Nominal   — sem ordem; regimes: categórico / cauda longa / textual
│   ├── Ordinal   — com ordem natural (escolaridade, faixa etária)
│   ├── Binária   — exatamente 2 níveis (sim/não, 0/1)
│   └── Rank      — colocação, sempre nomeando a coluna de referência
├── Quantitativa (numérica)
│   ├── Discreta  — contagens (inteiros); regimes: tabela / histograma
│   └── Contínua  — medições com casas decimais (renda, preço)
├── Temporal (tipo de primeira classe, que se decompõe)
│   ├── Instante  — pontos no tempo (data da venda)
│   └── Duração   — intervalos (tempo de entrega)
└── Identificador — números que não são quantidades
    ├── Chave     — identifica a linha (PassengerId)
    └── Código    — identifica uma entidade e repete (CNPJ, código IBGE)
```

Datas não cabem em qualitativa nem em quantitativa porque são **as duas coisas ao mesmo tempo**: um eixo contínuo que carrega componentes cíclicos categóricos. Por isso são tipo de primeira classe que **se decompõe** — mês, dia da semana e hora viram ordinais cíclicas.

**Cinco princípios** (discussão completa em [docs/fluxo-de-analises.md](docs/fluxo-de-analises.md)):

1. **A inferência propõe, o usuário dispõe** — todo tipo é sobrescrevível; ambiguidades são marcadas, nunca decididas em silêncio.
2. **O maat descreve, não julga** — contagens, proporções e amostras; sem quality gates nem vereditos. *Corolário: mostrar é obrigação, agir é do usuário* — se o dado tem problema visível, o maat mostra o fato com o critério declarado junto, e você decide se corrige.
3. **Duas camadas em todo perfil** — essencial (legível por qualquer pessoa) e completa (profundidade estatística).
4. **O custo mora no backend** — agregações no motor; o visual recebe só dados pré-agregados.
5. **Narrativas com números garantidos** — prosa acadêmica por templates determinísticos, com LLM local opcional apenas para reformular, sob trava de validação numérica.

## O que ele detecta que outros não detectam

Tudo determinístico e independente de idioma — nunca inferência difusa:

| Detecção | Exemplo real do benchmark |
|---|---|
| **Dígito verificador de CPF/CNPJ** | `CNPJ_FUNDO_CLASSE` da CVM: 100% válido → é código, não número |
| **Variantes de grafia** | `UBER DO BRASIL LTDA.` (10.267) convivendo com `Uber Do Brasil Ltda.` (8) na cota parlamentar |
| **Ambiguidade dd/mm × mm/dd** | 39% a 50% dos valores são ambíguos; a prova vem da minoria com campo > 12. Quando **nada** desambigua, o maat declara o impasse em vez de escolher em silêncio |
| **Rebase de calendário do Spark** | datas antes de 1582-10-15 mudam de valor ao ler Parquet/Avro |
| **Limites do dtype** | antes de 1677 ou após 2262 o pandas não representa, mas o Spark sim |
| **15 checagens de sujeira em texto** | `markdown` disparou 71× em **nomes** do nyc-airbnb; CPF/CNPJ apareceu em campo de **fornecedor** |

## Instalação

```bash
pip install -e ".[pandas]"        # local
pip install -e ".[spark]"         # distribuído
pip install -e ".[pandas,yaml,dev]"
```

O núcleo não tem dependências: taxonomia, inferência e renderizadores são código puro. Cada backend traz a sua.

## Uso

```python
import maat

profile = maat.describe(df)
profile.schema                    # tipo inferido de cada coluna
profile["renda"]                  # perfil: camadas, checagens, viz e narrativa

# quatro renderizadores sobre a mesma estrutura em memória
profile.to_json(compact=True)              # máquina (0,63× os tokens do JSON indentado)
profile.to_yaml()                          # edição à mão (0,73×)
profile.to_markdown(camada="essencial")    # agente de IA e trabalho acadêmico (0,30×)
profile.to_html("relatorio.html")          # leitura humana
```

Tudo é parametrizável — a inferência propõe, você dispõe:

```python
profile = maat.describe(df, maat.Config(
    max_categorical_levels=30,                       # limiar do regime categórico
    ordinal_levels={"quality": [3, 4, 5, 6, 7, 8]},  # declara a ordem
    date_format={"data": "dd/mm"},                   # resolve a ambiguidade
    language="pt-BR",                                # ou "en"
    narrative_llm=None,                              # "ollama/llama3.2:3b" opcional
))
```

## Estrutura do projeto

```
maat/
├── docs/
│   ├── fluxo-de-analises.md    # o mapa conceitual: tipos, regimes, decisões e porquês
│   ├── fluxo-interativo.html   # o grafo arrastável (GitHub Pages)
│   ├── tipos/                  # página detalhada por tipo, com números reais
│   ├── comparacao-ydata.md     # baseline competitivo medido
│   └── identidade-visual.md    # paleta e tipografia
├── src/maat/
│   ├── core/                   # config, meta, signals, inference, profile, taxonomy
│   ├── backends/               # contrato + pandas + PySpark
│   ├── analysis/               # uma análise por ramo da taxonomia
│   ├── narrative/              # templates pt-BR/en + trava de números
│   └── render.py               # JSON, YAML, Markdown, HTML
├── tests/
│   ├── fixtures/               # fatias reais do benchmark (114 KB, versionadas)
│   └── test_*.py               # 53 testes, cada um ligado a uma decisão documentada
├── datasets/                   # 40 datasets de benchmark (locais, fora do git)
└── scripts/                    # download, medições e comparação competitiva
```

## Testes

```bash
pytest
```

Os testes rodam sobre **fatias reais do benchmark** versionadas em `tests/fixtures/` — 114 KB que preservam a sujeira do mundo real: as variantes de grafia da Câmara, datas indecidíveis do e-commerce, caracteres invisíveis do nyc-airbnb, CNPJ válido da CVM. Cada asserção cita a seção da documentação que ela protege, então uma quebra aponta para a decisão que mudou.

## Status

🚧 **Alpha funcional.** O núcleo roda em pandas e PySpark, com 8 tipos consolidados, narrativas em dois idiomas e quatro formatos de saída. Validado sobre 38 datasets e 609 colunas reais.

Fora do MVP, com direção registrada: **bivariadas** (adiadas pela explosão combinatória — 9.412 pares no benchmark; a direção é seleção dos pares por IA com cálculo determinístico) e as **visualizações** renderizadas.

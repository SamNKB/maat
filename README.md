# maat

> Análise descritiva de dados para qualquer pessoa, em qualquer escala.

**maat** é uma biblioteca de análise exploratória/descritiva de dados que opera sobre **pandas** (dados locais) e **PySpark** (dados distribuídos) com a mesma API. O nome vem de Maat, a deusa egípcia da verdade, do equilíbrio e da ordem — o que uma boa análise descritiva deve revelar nos dados.

🖥️ **Documentação viva**: [grafo interativo do fluxo de classificação](https://samnkb.github.io/maat/fluxo-interativo.html) — arraste os nós, passe o mouse para exemplos reais, clique para as páginas detalhadas de cada tipo.

## Filosofia

Toda análise no maat parte de uma pergunta: **que tipo de variável é essa?**

```
Variável
├── Qualitativa (categórica)
│   ├── Nominal   — sem ordem natural; regimes: categórico / cauda longa / textual
│   ├── Ordinal   — com ordem natural (escolaridade, faixa etária)
│   └── Binária   — exatamente 2 níveis (sim/não, 0/1)          ✅ consolidada
├── Quantitativa (numérica)
│   ├── Discreta  — contagens (inteiros); regimes: tabela / histograma  ✅ consolidada
│   └── Contínua  — medições com casas decimais (renda, preço)  ✅ consolidada
└── Temporal (datas e timestamps)
    ├── Instante  — pontos no tempo (data da venda)
    └── Duração   — intervalos (tempo de entrega)
```

Datas não se encaixam nem em qualitativa nem em quantitativa porque são **as duas coisas ao mesmo tempo**: uma linha contínua que carrega componentes cíclicos categóricos. Por isso o maat as trata como **tipo de primeira classe**.

Princípios (discussão completa em [docs/fluxo-de-analises.md](docs/fluxo-de-analises.md)):

1. **A inferência propõe, o usuário dispõe** — todo tipo inferido é sobrescrevível; ambiguidades são marcadas, nunca decididas em silêncio.
2. **O maat descreve, não julga** — contagens, proporções e amostras; sem quality gates nem vereditos.
3. **Duas camadas em todo perfil** — essencial (legível por qualquer pessoa) e completa (profundidade estatística).
4. **O custo mora no backend** — agregações no motor; o visual recebe só dados pré-agregados.
5. **Narrativas com números garantidos** — prosa acadêmica por templates determinísticos (pt-BR/en), com LLM local opcional só para reformular/traduzir, sob trava de números.

## Estrutura do projeto

```
maat/
├── docs/
│   ├── fluxo-de-analises.md    # o mapa conceitual: tipos, regimes, análises, decisões
│   ├── fluxo-interativo.html   # o grafo arrastável (GitHub Pages)
│   ├── tipos/                  # subpáginas detalhadas por tipo consolidado
│   └── identidade-visual.md    # paleta Blade Runner + tipografia
├── assets/                     # design tokens (CSS) e paleta (SVG)
├── src/maat/
│   ├── core/                   # taxonomia, inferência, contrato ColumnProfile
│   ├── backends/               # contrato abstrato + pandas + PySpark
│   ├── analysis/               # análises por ramo da taxonomia
│   └── viz/                    # visualizações (fase 2)
├── datasets/                   # 40 datasets de benchmark (locais, fora do git)
│   └── README.md               # manifesto: 30 do Kaggle + 10 de dados abertos do governo BR
├── scripts/
│   ├── download_datasets.py        # baixa os 30 do Kaggle
│   ├── download_gov_datasets.py    # baixa os 10 do governo
│   └── benchmark_examples.py       # reproduz os números citados na documentação
└── tests/
```

## Uso pretendido (visão de API)

```python
import maat

profile = maat.describe(df)      # pandas.DataFrame ou pyspark.sql.DataFrame
profile.schema                   # tipo inferido de cada coluna
profile["renda"]                 # perfil completo: camadas, viz e narrativa
profile.report("html")           # relatório navegável
```

Limiares e comportamentos são parametrizáveis via `maat.Config` (níveis de regime, amostra de inferência, tamanho das tabelas de extremos, idioma e tom da narrativa).

## Status

🚧 Em construção por design conjunto — as decisões de análise são discutidas e registradas antes do código. Consolidados até agora: **binária, quantitativa discreta e quantitativa contínua** (cada uma com [subpágina detalhada](https://samnkb.github.io/maat/tipos/binaria.html) usando números reais do benchmark), a arquitetura de **narrativas** e a **identidade visual**. Próximo: nominal cauda longa → ordinal → textual → temporal; depois, implementação da inferência + backend pandas e benchmark nos 40 datasets.

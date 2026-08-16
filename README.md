# maat

> Análise descritiva de dados para qualquer pessoa, em qualquer escala.

**maat** é uma biblioteca de análise exploratória/descritiva de dados que opera sobre **pandas** (dados locais) e **PySpark** (dados distribuídos) com a mesma API. O nome vem de Maat, a deusa egípcia da verdade, do equilíbrio e da ordem — o que uma boa análise descritiva deve revelar nos dados.

## Filosofia

Toda análise no maat parte de uma pergunta: **que tipo de variável é essa?**

A resposta determina quais estatísticas fazem sentido calcular e quais visualizações fazem sentido desenhar. A taxonomia usada é:

```
Variável
├── Qualitativa (categórica)
│   ├── Nominal   — sem ordem natural (cidade, cor, sexo)
│   ├── Ordinal   — com ordem natural (escolaridade, faixa etária)
│   └── Binária   — caso especial com 2 níveis (sim/não, ativo/inativo)
├── Quantitativa (numérica)
│   ├── Discreta  — contagens, valores inteiros (nº de filhos, nº de compras)
│   └── Contínua  — medições em escala real (renda, altura, temperatura)
└── Temporal (datas e timestamps)
    ├── Instante  — pontos no tempo (data da venda, timestamp do evento)
    └── Duração   — intervalos (tempo de entrega, tempo de sessão)
```

Datas não se encaixam nem em qualitativa nem em quantitativa porque são **as duas coisas ao mesmo tempo**: uma linha contínua (eixo do tempo) que carrega componentes cíclicos categóricos (mês, dia da semana, hora). Por isso o maat as trata como um **tipo de primeira classe**. A discussão completa está em [docs/fluxo-de-analises.md](docs/fluxo-de-analises.md).

## Estrutura do projeto

```
maat/
├── docs/
│   └── fluxo-de-analises.md   # documento de referência: o que cada tipo de variável
│                              # pode gerar de análise (resumos + visualizações)
├── src/maat/
│   ├── core/
│   │   ├── taxonomy.py        # a taxonomia de variáveis (enums e metadados)
│   │   └── inference.py       # inferência automática do tipo de cada coluna
│   ├── backends/
│   │   ├── base.py            # contrato abstrato que pandas e spark implementam
│   │   ├── pandas_backend.py  # implementação pandas
│   │   └── spark_backend.py   # implementação PySpark
│   ├── analysis/
│   │   ├── qualitative.py     # análises de variáveis qualitativas
│   │   ├── quantitative.py    # análises de variáveis quantitativas
│   │   ├── temporal.py        # análises de variáveis temporais
│   │   └── bivariate.py       # análises cruzadas (tipo × tipo)
│   └── viz/                   # geração de visualizações (fase 2)
└── tests/
```

## Uso pretendido (visão de API)

```python
import maat

# funciona igual com pandas.DataFrame ou pyspark.sql.DataFrame
profile = maat.describe(df)

profile.schema          # tipo inferido de cada coluna
profile["renda"]        # análise completa da coluna (resumo + sugestões de visual)
profile.report("html")  # relatório navegável
```

## Status

🚧 Estrutura inicial. O próximo passo é discutir e consolidar o [fluxo de análises](docs/fluxo-de-analises.md) antes de implementar os backends.

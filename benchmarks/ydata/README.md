# Baseline: ydata-profiling sobre o benchmark

Resultados do **ydata-profiling 4.18.4** rodado sobre os 40 datasets do benchmark, para comparação com o maat. É a ferramenta de mercado mais próxima do que estamos propondo — conhecer o incumbente por dentro afia o nosso diferencial em vez de nos intimidar.

Gerado por `python scripts/run_ydata_baseline.py`. **Os relatórios não são versionados** (ver `.gitignore`) — apenas este README e a análise comparativa em [`docs/comparacao-ydata.md`](../../docs/comparacao-ydata.md).

## O que tem aqui

| Arquivo | Conteúdo |
|---|---|
| `<dataset>.html` | Relatório navegável do ydata — abra no navegador para inspeção humana |
| `<dataset>.json` | Descrição estruturada da mesma análise, para comparação automática |
| `_resumo.csv` | Uma linha por coluna: dataset, coluna, tipo detectado, distintos, % distintos, ausentes |
| `_execucao.csv` | Uma linha por dataset: arquivo lido, linhas, colunas, modo, nº de alertas, tempo, status |

## Como foi rodado

- **Amostra de até 100.000 linhas** por dataset — o objetivo é comparar comportamento por coluna, não medir escala.
- **Modo mínimo** (sem correlações e interações) acima de 30.000 linhas ou 40 colunas, para o tempo de execução ficar viável.
- Maior CSV de cada pasta, com detecção automática de encoding (utf-8 → latin-1) e separador (`,` → `;`).

## Nota de ambiente

Instalar o `ydata-profiling` **rebaixou o pandas de 3.0.5 para 2.3.3** (ele ainda não suporta pandas 3.x). O pacote também está migrando para `fg-data-profiling` / `import data_profiling`.

"""Análises de variáveis quantitativas (seção 3 do fluxo de análises)."""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableType


def analyze_discrete(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Contagens — seção 3.1 do fluxo (consolidada).

    Regime TABLE (k ≤ max_discrete_levels): frequência por valor exato.
    Regime HISTOGRAM: bins inteiros + tabela de extremos de frequência
    (n mais e n menos frequentes; empates na menor frequência desempatados
    pelos valores mais extremos).

    Essencial: tabela, mínimo, máximo, moda, média e mediana.
    Completa: desvio padrão, quartis, % de zeros, ECDF.
    Fora por decisão: soma total (leitura de negócio, não de distribuição).
    """
    raise NotImplementedError


def analyze_continuous(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Medições — seção 3.2 do fluxo (consolidada).

    Essencial: resumo de cinco números + média (mín, q1, mediana, média, q3,
    máx), histograma e tabela de extremos de valor (n maiores e n menores
    observados, com contagem quando o valor se repete).
    Completa: quantis de cauda, desvio padrão, IQR, CV, assimetria, curtose,
    contagem de atípicos pela regra 1,5×IQR (descritos, nunca julgados),
    ECDF e boxplot.
    """
    raise NotImplementedError

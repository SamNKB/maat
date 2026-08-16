"""Análises de variáveis qualitativas (seção 2 do fluxo de análises).

Recebe agregados do backend (value_counts) e produz o ColumnProfile —
nunca toca nos dados brutos.
"""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableType


def analyze_nominal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Frequências, moda, cardinalidade, desbalanceamento, entropia, raras."""
    raise NotImplementedError


def analyze_ordinal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Tudo da nominal + acumuladas na ordem natural, categoria mediana."""
    raise NotImplementedError


def analyze_binary(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Proporção de cada nível + IC da proporção. Saída enxuta."""
    raise NotImplementedError

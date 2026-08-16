"""Análises de variáveis quantitativas (seção 3 do fluxo de análises)."""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableType


def analyze_discrete(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Frequências por valor, posição/dispersão, % de zeros."""
    raise NotImplementedError


def analyze_continuous(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Posição, dispersão, forma, outliers (1.5×IQR) e diagnósticos
    (assimetria → sugerir log; valores redondos → arredondamento na coleta)."""
    raise NotImplementedError

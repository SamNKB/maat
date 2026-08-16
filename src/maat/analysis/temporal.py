"""Análises de variáveis temporais (seção 4 do fluxo de análises).

O tipo temporal se decompõe: gera derivadas qualitativas (mês, dia da
semana, hora — ordinais cíclicas) e quantitativas (posição na linha do
tempo, durações), e cada derivada herda o fluxo de análise do seu tipo.
"""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableType


def analyze_instant(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Cobertura, granularidade detectada, contagem por período, gaps,
    perfis cíclicos (mês/dia da semana/hora) e checagens de qualidade
    (datas futuras, anteriores a limiar plausível)."""
    raise NotImplementedError


def analyze_duration(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Herda a análise contínua, com unidade de exibição inteligente,
    mediana como resumo principal e checagem de durações negativas."""
    raise NotImplementedError

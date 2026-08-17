"""Contrato de saída das análises (seção 6 do fluxo de análises).

Toda análise, em qualquer backend, devolve estas estruturas — assim a camada
de visualização e o relatório nunca dependem de pandas ou Spark.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maat.core.taxonomy import VariableType


@dataclass
class VizSuggestion:
    """Sugestão de visualização com os dados já pré-agregados pelo backend."""

    chart: str  # ex.: "bar", "histogram", "boxplot", "timeline"
    data: dict[str, Any]  # dados agregados, prontos para plotar (nunca dados brutos)
    reason: str  # por que este gráfico foi sugerido


@dataclass
class ColumnProfile:
    """Resultado completo da análise de uma coluna."""

    name: str
    inferred_type: VariableType
    quality: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    viz_suggestions: list[VizSuggestion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Prosa gerada por template determinístico (seção 7 do fluxo de análises);
    # reformulação via LLM local opcional nunca altera números (trava validada).
    narrative: str | None = None


@dataclass
class DatasetProfile:
    """Resultado da análise do DataFrame inteiro."""

    n_rows: int
    columns: dict[str, ColumnProfile] = field(default_factory=dict)

    def __getitem__(self, name: str) -> ColumnProfile:
        return self.columns[name]

    @property
    def schema(self) -> dict[str, VariableType]:
        return {name: col.inferred_type for name, col in self.columns.items()}

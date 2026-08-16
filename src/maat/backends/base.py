"""Contrato abstrato dos backends.

O princípio de projeto: todo o custo computacional (agregações, quantis,
amostragem) fica no backend; os módulos de análise e visualização trabalham
apenas com os agregados que o backend devolve. É isso que permite que o
mesmo código de análise sirva para pandas (local) e Spark (distribuído).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Backend(ABC):
    """Operações primitivas que cada motor de dados precisa oferecer."""

    @abstractmethod
    def columns_meta(self) -> dict[str, dict]:
        """Metadados baratos por coluna, insumo da inferência de tipos.

        Ver maat.core.inference.infer_schema para o formato esperado.
        """

    @abstractmethod
    def value_counts(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        """Frequência por valor — base das análises qualitativas."""

    @abstractmethod
    def numeric_summary(self, column: str) -> dict[str, float]:
        """Posição, dispersão e forma — base das análises quantitativas.

        Quantis podem ser aproximados (Spark); o resultado deve incluir a
        chave ``quantile_error`` informando o erro (0.0 quando exato).
        """

    @abstractmethod
    def histogram(self, column: str, bins: int) -> dict[str, list[float]]:
        """Contagens por bin, calculadas no motor — nunca traz dados brutos."""

    @abstractmethod
    def temporal_summary(self, column: str) -> dict[str, Any]:
        """Cobertura, granularidade, gaps e perfis cíclicos de uma coluna temporal."""

    @abstractmethod
    def sample(self, columns: list[str], n: int) -> list[dict[str, Any]]:
        """Amostra para visuais que exigem pontos individuais (dispersão)."""

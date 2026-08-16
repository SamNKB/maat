"""Backend PySpark — dados distribuídos, agregações no cluster.

Diferenças de contrato em relação ao pandas (ver docs/fluxo-de-analises.md):
- quantis via ``approxQuantile`` (o erro usado é reportado em ``quantile_error``);
- visuais de dispersão sempre com amostragem ou pré-agregação (hexbin) —
  nunca coletar o DataFrame inteiro para o driver.
"""

from __future__ import annotations

from typing import Any

from maat.backends.base import Backend

# Erro relativo padrão do approxQuantile — questão em aberto nº 3 do fluxo.
DEFAULT_QUANTILE_ERROR = 0.01


class SparkBackend(Backend):
    def __init__(self, df: Any) -> None:  # pyspark.sql.DataFrame (import tardio)
        self.df = df

    def columns_meta(self) -> dict[str, dict]:
        raise NotImplementedError

    def value_counts(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        raise NotImplementedError

    def numeric_summary(self, column: str) -> dict[str, float]:
        raise NotImplementedError

    def histogram(self, column: str, bins: int) -> dict[str, list[float]]:
        raise NotImplementedError

    def temporal_summary(self, column: str) -> dict[str, Any]:
        raise NotImplementedError

    def sample(self, columns: list[str], n: int) -> list[dict[str, Any]]:
        raise NotImplementedError

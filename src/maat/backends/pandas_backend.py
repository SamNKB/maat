"""Backend pandas — dados locais, resultados exatos."""

from __future__ import annotations

from typing import Any

from maat.backends.base import Backend


class PandasBackend(Backend):
    def __init__(self, df: Any) -> None:  # pandas.DataFrame (import tardio)
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

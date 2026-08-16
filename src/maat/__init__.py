"""maat — análise descritiva de dados sobre pandas e PySpark."""

from __future__ import annotations

from typing import Any

from maat.core.profile import ColumnProfile, DatasetProfile
from maat.core.taxonomy import VariableClass, VariableSubtype, VariableType

__version__ = "0.1.0"

__all__ = [
    "describe",
    "DatasetProfile",
    "ColumnProfile",
    "VariableClass",
    "VariableSubtype",
    "VariableType",
]


def describe(
    df: Any,
    overrides: dict[str, VariableType] | None = None,
) -> DatasetProfile:
    """Ponto de entrada principal do maat.

    Detecta o motor do DataFrame (pandas ou PySpark), infere o tipo de cada
    coluna e despacha as análises adequadas. ``overrides`` permite corrigir
    a classificação de colunas específicas (ex.: declarar uma ordinal e sua
    ordem de níveis).
    """
    backend = _resolve_backend(df)
    raise NotImplementedError("Implementar após consolidar o fluxo de análises")


def _resolve_backend(df: Any):
    """Escolhe o backend pelo tipo do DataFrame, com imports tardios para
    não exigir pandas e pyspark instalados ao mesmo tempo."""
    module = type(df).__module__
    if module.startswith("pandas"):
        from maat.backends.pandas_backend import PandasBackend

        return PandasBackend(df)
    if module.startswith("pyspark"):
        from maat.backends.spark_backend import SparkBackend

        return SparkBackend(df)
    raise TypeError(
        f"DataFrame não suportado: {type(df).__name__}. "
        "O maat aceita pandas.DataFrame e pyspark.sql.DataFrame."
    )

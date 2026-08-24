"""maat — análise descritiva de dados sobre pandas e PySpark.

O nome vem de Maat, a deusa egípcia da verdade, do equilíbrio e da ordem —
o que uma boa análise descritiva deve revelar nos dados.

    import maat
    profile = maat.describe(df)          # pandas ou PySpark, mesma API
    profile.to_markdown(camada="essencial")
"""

from __future__ import annotations

from typing import Any

from maat.core.config import Check, Config
from maat.core.inference import infer_schema
from maat.core.profile import ColumnProfile, DatasetProfile
from maat.core.taxonomy import (
    CardinalityRegime,
    VariableClass,
    VariableSubtype,
    VariableType,
)

__version__ = "0.1.0"

__all__ = [
    "describe",
    "Config",
    "Check",
    "DatasetProfile",
    "ColumnProfile",
    "VariableClass",
    "VariableSubtype",
    "VariableType",
    "CardinalityRegime",
]


def describe(
    df: Any,
    config: Config | None = None,
) -> DatasetProfile:
    """Ponto de entrada principal do maat.

    Detecta o motor do DataFrame (pandas ou PySpark), infere o tipo de cada
    coluna e despacha as análises adequadas. `config.overrides` permite
    corrigir a classificação de colunas específicas — a inferência propõe,
    o usuário dispõe (§0.1).
    """
    from maat.analysis import despachar

    config = config or Config()
    backend = _resolve_backend(df, config)

    schema = infer_schema(backend.columns_meta(), config)
    perfil = DatasetProfile(n_rows=backend.n_rows(), source=getattr(df, "name", None))

    try:
        for coluna, vtype in schema.items():
            perfil.columns[coluna] = despachar(backend, coluna, vtype)
    finally:
        liberar = getattr(backend, "liberar_cache", None)
        if liberar:
            liberar()

    if config.mask_pii:
        from maat.privacy import mascarar_perfil

        mascarar_perfil(perfil, config)
    return perfil


def _resolve_backend(df: Any, config: Config):
    """Escolhe o backend pelo tipo do DataFrame, com imports tardios para
    não exigir pandas e pyspark instalados ao mesmo tempo."""
    modulo = type(df).__module__
    if modulo.startswith("pandas"):
        from maat.backends.pandas_backend import PandasBackend

        return PandasBackend(df, config)
    if modulo.startswith("pyspark"):
        from maat.backends.spark_backend import SparkBackend

        return SparkBackend(df, config)
    raise TypeError(
        f"DataFrame não suportado: {type(df).__name__}. "
        "O maat aceita pandas.DataFrame e pyspark.sql.DataFrame."
    )

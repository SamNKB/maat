"""Inferência automática do tipo de cada coluna.

As heurísticas seguem a tabela de docs/fluxo-de-analises.md (seção 1).
O usuário sempre pode sobrescrever o resultado via ``overrides``.
"""

from __future__ import annotations

from maat.core.taxonomy import VariableType

# Limiares iniciais — em aberto na questão 1 do fluxo de análises.
MAX_CATEGORICAL_LEVELS = 50
MAX_CATEGORICAL_RATIO = 0.20  # cardinalidade / n acima disso → id ou texto livre
MAX_DISCRETE_LEVELS = 30  # inteiros com até N valores distintos → discreta


def infer_schema(
    columns_meta: dict[str, dict],
    overrides: dict[str, VariableType] | None = None,
) -> dict[str, VariableType]:
    """Infere o tipo de cada coluna a partir de metadados extraídos pelo backend.

    ``columns_meta`` mapeia nome da coluna para um dict com, no mínimo:
    ``dtype`` (str normalizado pelo backend), ``n``, ``n_distinct``,
    ``all_integer`` (bool, só para numéricas) e ``parse_date_rate``
    (float, só para strings).

    Backends coletam esses metadados do jeito mais barato possível no seu
    motor (pandas: direto; Spark: um job de agregação) e a inferência em si
    é código puro e compartilhado.
    """
    raise NotImplementedError("Implementar após consolidar o fluxo de análises")

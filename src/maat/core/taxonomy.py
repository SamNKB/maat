"""Taxonomia de variáveis do maat.

A classificação de cada coluna determina quais análises e visualizações
fazem sentido. Ver docs/fluxo-de-analises.md para a discussão completa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VariableClass(str, Enum):
    """Classe principal da variável."""

    QUALITATIVE = "qualitative"
    QUANTITATIVE = "quantitative"
    TEMPORAL = "temporal"
    IDENTIFIER = "identifier"  # excluída das análises (ids, chaves)
    UNSUPPORTED = "unsupported"  # texto livre, structs etc. (fora do MVP)


class CardinalityRegime(str, Enum):
    """Regime de cardinalidade — modificador que seleciona a estratégia de
    análise dentro de um tipo (seção 2.0 do fluxo de análises).

    Não é um tipo: uma nominal em regime CATEGORICAL ganha tabela de
    frequências completa; em LONG_TAIL, top-N + Pareto; em TEXTUAL, perfil
    da string (forma, padrão e sujeira via regex) com amostras dirigidas.
    """

    # Regimes da qualitativa nominal
    CATEGORICAL = "categorical"  # k pequeno — todos os níveis no resumo
    LONG_TAIL = "long_tail"  # k médio com repetição — top-N + "Outros"
    TEXTUAL = "textual"  # k ≈ n — a string em si vira o objeto de análise
    # Regimes da quantitativa discreta (seção 3.1 do fluxo de análises)
    TABLE = "table"  # k ≤ limiar — frequência por valor exato
    HISTOGRAM = "histogram"  # k alto — bins inteiros + tabela de extremos de frequência


class VariableSubtype(str, Enum):
    """Subtipo dentro de cada classe."""

    # Qualitativas
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    BINARY = "binary"
    # Quantitativas
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    # Temporais
    INSTANT = "instant"
    DURATION = "duration"


# Subtipos válidos por classe — usado para validar reclassificações do usuário.
VALID_SUBTYPES: dict[VariableClass, frozenset[VariableSubtype]] = {
    VariableClass.QUALITATIVE: frozenset(
        {VariableSubtype.NOMINAL, VariableSubtype.ORDINAL, VariableSubtype.BINARY}
    ),
    VariableClass.QUANTITATIVE: frozenset(
        {VariableSubtype.DISCRETE, VariableSubtype.CONTINUOUS}
    ),
    VariableClass.TEMPORAL: frozenset(
        {VariableSubtype.INSTANT, VariableSubtype.DURATION}
    ),
    VariableClass.IDENTIFIER: frozenset(),
    VariableClass.UNSUPPORTED: frozenset(),
}


@dataclass
class VariableType:
    """Tipo completo de uma coluna, com metadados da inferência."""

    var_class: VariableClass
    subtype: VariableSubtype | None = None
    # Regime de cardinalidade — relevante para qualitativas e quantitativas
    # discretas; inferido a partir de k (n_distinct) e n, sobrescrevível.
    regime: CardinalityRegime | None = None
    # Confiança da inferência em [0, 1]; 1.0 quando declarado pelo usuário.
    confidence: float = 1.0
    # Ordem dos níveis, obrigatória para ordinais (ex.: ["baixo", "médio", "alto"]).
    ordered_levels: list[str] | None = None
    # Avisos da inferência (ex.: "número com cara de código — confira se é quantitativa").
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        valid = VALID_SUBTYPES[self.var_class]
        if self.subtype is not None and self.subtype not in valid:
            raise ValueError(
                f"Subtipo {self.subtype.value!r} inválido para a classe "
                f"{self.var_class.value!r}"
            )
        if self.subtype is VariableSubtype.ORDINAL and not self.ordered_levels:
            self.warnings.append(
                "Ordinal sem ordem declarada — análises de ordem ficarão indisponíveis"
            )

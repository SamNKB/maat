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
    # Rank: posição/colocação. Família ordinal (a natureza do dado é ordem),
    # mas identificado por monotonia com outra coluna — ver seção 3.3.
    RANK = "rank"
    # Quantitativas
    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    # Temporais
    INSTANT = "instant"
    DURATION = "duration"
    # Identificadores (seção 3.3): números que não são quantidades
    KEY = "key"  # identifica a linha, k ≈ n — unicidade e colisões
    CODE = "code"  # identifica uma entidade e se repete — cardinalidade, nunca média


# Subtipos válidos por classe — usado para validar reclassificações do usuário.
VALID_SUBTYPES: dict[VariableClass, frozenset[VariableSubtype]] = {
    VariableClass.QUALITATIVE: frozenset(
        {
            VariableSubtype.NOMINAL,
            VariableSubtype.ORDINAL,
            VariableSubtype.BINARY,
            VariableSubtype.RANK,
        }
    ),
    VariableClass.QUANTITATIVE: frozenset(
        {VariableSubtype.DISCRETE, VariableSubtype.CONTINUOUS}
    ),
    VariableClass.TEMPORAL: frozenset(
        {VariableSubtype.INSTANT, VariableSubtype.DURATION}
    ),
    VariableClass.IDENTIFIER: frozenset({VariableSubtype.KEY, VariableSubtype.CODE}),
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
    # Só para RANK: coluna com que a monotonia foi detectada e o Spearman medido.
    # Obrigatório — é a mitigação do falso positivo (seção 3.3): nomear a
    # referência torna um engano visível na primeira leitura.
    rank_reference: str | None = None
    rank_spearman: float | None = None

    def __post_init__(self) -> None:
        valid = VALID_SUBTYPES[self.var_class]
        if self.subtype is not None and self.subtype not in valid:
            raise ValueError(
                f"Subtipo {self.subtype.value!r} inválido para a classe "
                f"{self.var_class.value!r}"
            )
        if self.subtype is VariableSubtype.RANK and not self.rank_reference:
            raise ValueError(
                "RANK exige rank_reference: a coluna com que a monotonia foi "
                "detectada. Nomear a referência é a mitigação do falso positivo "
                "(seção 3.3 do fluxo de análises)."
            )
        if self.subtype is VariableSubtype.ORDINAL and not self.ordered_levels:
            self.warnings.append(
                "Ordinal sem ordem declarada — análises de ordem ficarão indisponíveis"
            )


# Tokens de granularidade temporal emitidos pelos backends. O token é o valor
# estável do contrato (JSON/YAML); o rótulo é o que vai para olho humano —
# sem o mapa, a narrativa escrevia "granularidade diaria" e "at diaria
# granularity".
GRANULARIDADE_LEGIVEL: dict[str, dict[str, str]] = {
    "mensal": {"pt": "mensal", "en": "monthly"},
    "diaria": {"pt": "diária", "en": "daily"},
    "minuto": {"pt": "de minuto", "en": "minute"},
    "segundo": {"pt": "de segundo", "en": "second"},
    "com_hora": {"pt": "com hora", "en": "sub-daily"},
}


def granularidade_legivel(token: str | None, idioma: str = "pt-BR") -> str:
    """Rótulo humano de um token de granularidade; devolve o token se não mapeado."""
    if not token:
        return "—"
    chave = "en" if idioma == "en" else "pt"
    return GRANULARIDADE_LEGIVEL.get(token, {}).get(chave, token)

"""Inferência do tipo de cada coluna — o roteamento da seção 1 do fluxo.

Código puro sobre `ColumnMeta`: nenhum acesso a dados, nenhuma dependência
de pandas ou Spark. Os backends produzem os metadados; a decisão é
compartilhada.

Princípio §0.1 — **a inferência propõe, o usuário dispõe**: todo tipo é
sobrescrevível via `Config.overrides`, e as ambiguidades viram observações
em `VariableType.warnings` em vez de decisões silenciosas.
"""

from __future__ import annotations

from maat.core.config import Config
from maat.core.meta import ColumnMeta, DateFormatEvidence, DtypeKind
from maat.core.taxonomy import (
    CardinalityRegime,
    VariableClass,
    VariableSubtype,
    VariableType,
)


def infer_schema(
    metas: dict[str, ColumnMeta],
    config: Config | None = None,
) -> dict[str, VariableType]:
    """Infere o tipo de cada coluna a partir dos metadados do backend."""
    config = config or Config()
    schema: dict[str, VariableType] = {}
    for nome, meta in metas.items():
        if nome in config.overrides:
            declarado = config.overrides[nome]
            declarado.confidence = 1.0
            schema[nome] = declarado
            continue
        schema[nome] = infer_column(meta, config)
    return schema


def infer_column(meta: ColumnMeta, config: Config) -> VariableType:
    """Roteia uma coluna. Ver o fluxograma da §1."""
    # Ordem declarada vence tudo e vale para qualquer dtype: o caso motivador
    # é `quality` do wine — inteiro de 3 a 8 que é escala Likert, não contagem.
    if meta.name in config.ordinal_levels and meta.n_valid:
        return VariableType(
            VariableClass.QUALITATIVE,
            VariableSubtype.ORDINAL,
            regime=_regime_nominal(meta, config),
            ordered_levels=[str(v) for v in config.ordinal_levels[meta.name]],
        )

    if meta.n_valid == 0:
        return VariableType(
            VariableClass.UNSUPPORTED,
            confidence=1.0,
            warnings=["Coluna sem valores válidos"],
        )

    if meta.dtype_kind is DtypeKind.BOOL:
        return VariableType(VariableClass.QUALITATIVE, VariableSubtype.BINARY)

    if meta.dtype_kind is DtypeKind.DATETIME:
        return _temporal_instant(meta, config)

    if meta.dtype_kind is DtypeKind.TIMEDELTA:
        return VariableType(VariableClass.TEMPORAL, VariableSubtype.DURATION)

    if meta.dtype_kind is DtypeKind.NUMERIC:
        return _numeric(meta, config)

    if meta.dtype_kind is DtypeKind.STRING:
        return _string(meta, config)

    return VariableType(
        VariableClass.UNSUPPORTED,
        warnings=[f"dtype não suportado no MVP: {meta.dtype_kind.value}"],
    )


# --------------------------------------------------------------------------
# rota numérica (§3.1, §3.2, §3.3)
# --------------------------------------------------------------------------


def _numeric(meta: ColumnMeta, config: Config) -> VariableType:
    # 1. código — identifica entidade e se repete (CNPJ, CO_MUN, ideCadastro)
    if meta.looks_like_code:
        avisos = []
        if meta.check_digit_rate >= 0.9:
            avisos.append(
                f"{meta.check_digit_rate:.1%} dos valores passam no dígito "
                f"verificador de {meta.check_digit_kind}"
            )
        elif meta.has_leading_zeros:
            avisos.append("zeros à esquerda preservados — número descarta, código não")
        else:
            avisos.append(
                f"comprimento fixo e {meta.repetition_ratio:.0f} linhas por valor"
            )
        return VariableType(
            VariableClass.IDENTIFIER,
            VariableSubtype.CODE,
            confidence=0.9,
            warnings=avisos,
        )

    if meta.n_distinct == 2:
        return VariableType(VariableClass.QUALITATIVE, VariableSubtype.BINARY)

    # 2. denso e único: rank ou chave — nenhum sinal estatístico os separa.
    # Exige inteiros: toda medição contínua é única por natureza, e sem esta
    # condição qualquer float de uma base pequena viraria identificador.
    unico = meta.n_distinct == meta.n_valid
    if unico and meta.all_integer and meta.n_valid >= config.identifier_min_rows:
        denso = meta.density >= 0.9
        monotonico = (
            meta.max_spearman is not None
            and abs(meta.max_spearman) >= config.rank_monotonia_minima
            and meta.spearman_reference is not None
        )
        if denso and monotonico:
            return VariableType(
                VariableClass.QUALITATIVE,
                VariableSubtype.RANK,
                confidence=0.7,
                rank_reference=meta.spearman_reference,
                rank_spearman=meta.max_spearman,
                warnings=[
                    "Rank e id sequencial têm assinatura estatística idêntica; "
                    f"classificado como rank por ser monotônico com "
                    f"'{meta.spearman_reference}' (Spearman {meta.max_spearman:+.4f})"
                ],
            )
        return VariableType(
            VariableClass.IDENTIFIER,
            VariableSubtype.KEY,
            confidence=0.9 if not denso else 0.75,
            warnings=(
                []
                if not denso
                else ["Denso e único começando perto de 1 — pode ser colocação; "
                      "declare o tipo se for rank"]
            ),
        )

    # 3. contagem × medição
    if meta.all_integer:
        regime = (
            CardinalityRegime.TABLE
            if meta.n_distinct <= config.max_discrete_levels
            else CardinalityRegime.HISTOGRAM
        )
        return VariableType(
            VariableClass.QUANTITATIVE, VariableSubtype.DISCRETE, regime=regime
        )

    return VariableType(VariableClass.QUANTITATIVE, VariableSubtype.CONTINUOUS)


# --------------------------------------------------------------------------
# rota string (§2)
# --------------------------------------------------------------------------


def _string(meta: ColumnMeta, config: Config) -> VariableType:
    # 1. data disfarçada de texto
    if meta.parse_date_rate >= config.date_parse_min_rate:
        return _temporal_instant(meta, config)

    # 2. código em texto (CNPJ mascarado, CEP com zero à esquerda)
    if meta.check_digit_rate >= 0.9:
        return VariableType(
            VariableClass.IDENTIFIER,
            VariableSubtype.CODE,
            confidence=0.95,
            warnings=[
                f"{meta.check_digit_rate:.1%} dos valores passam no dígito "
                f"verificador de {meta.check_digit_kind}"
            ],
        )

    if meta.n_distinct == 2:
        return VariableType(VariableClass.QUALITATIVE, VariableSubtype.BINARY)

    # 3. ordinal — a ordem declarada já foi tratada em infer_column;
    # aqui resta o número inicial no rótulo
    if meta.leading_number_order:
        return VariableType(
            VariableClass.QUALITATIVE,
            VariableSubtype.ORDINAL,
            regime=_regime_nominal(meta, config),
            confidence=0.85,
            ordered_levels=[str(v) for v in meta.leading_number_order],
            warnings=["Ordem extraída do número inicial dos rótulos"],
        )

    # 4. nominal — o regime decide a estratégia
    regime = _regime_nominal(meta, config)
    avisos = []
    if regime is CardinalityRegime.CATEGORICAL and meta.n_distinct > 2:
        avisos.append(
            "Possível ordinal: declare a ordem dos níveis para habilitar "
            "acumulada e categoria mediana"
        )
    return VariableType(
        VariableClass.QUALITATIVE,
        VariableSubtype.NOMINAL,
        regime=regime,
        warnings=avisos,
    )


def _regime_nominal(meta: ColumnMeta, config: Config) -> CardinalityRegime:
    """Categórico / cauda longa / textual — §2.0."""
    if meta.n_distinct <= config.max_categorical_levels:
        return CardinalityRegime.CATEGORICAL
    if meta.unique_ratio > config.textual_unique_ratio:
        return CardinalityRegime.TEXTUAL
    return CardinalityRegime.LONG_TAIL


# --------------------------------------------------------------------------
# temporal (§4.1)
# --------------------------------------------------------------------------


def _temporal_instant(meta: ColumnMeta, config: Config) -> VariableType:
    avisos: list[str] = []
    confianca = 1.0
    ev = meta.date_format_evidence

    if meta.name in config.date_format:
        avisos.append(f"Formato declarado pelo usuário: {config.date_format[meta.name]}")
    elif ev is DateFormatEvidence.UNDECIDABLE:
        confianca = 0.6
        avisos.append(
            "Formato indecidível entre dd/mm e mm/dd: nenhum valor desambigua "
            f"({meta.ambiguous_dates} ambíguos). Análises que dependem do dia "
            "ficam suspensas — declare em Config.date_format"
        )
    elif ev is DateFormatEvidence.MIXED:
        confianca = 0.5
        avisos.append(
            f"Formatos misturados na mesma coluna: {meta.dmy_proofs} valores só "
            f"casam com dd/mm e {meta.mdy_proofs} só com mm/dd — dado corrompido"
        )
    elif ev is DateFormatEvidence.DMY:
        avisos.append(f"Formato dd/mm provado por {meta.dmy_proofs} valores")
    elif ev is DateFormatEvidence.MDY:
        avisos.append(f"Formato mm/dd provado por {meta.mdy_proofs} valores")

    return VariableType(
        VariableClass.TEMPORAL,
        VariableSubtype.INSTANT,
        confidence=confianca,
        warnings=avisos,
    )

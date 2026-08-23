"""Despacho das análises por tipo inferido.

Cada ramo da taxonomia tem sua função; este módulo só escolhe qual chamar e
anexa a narrativa gerada.
"""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableClass, VariableSubtype, VariableType


def despachar(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Roteia a coluna para a análise do seu tipo e anexa a narrativa."""
    from maat.analysis import qualitative, quantitative, temporal
    from maat.narrative import gerar_narrativa

    sub = vtype.subtype
    if vtype.var_class is VariableClass.QUALITATIVE:
        if sub is VariableSubtype.BINARY:
            perfil = qualitative.analyze_binary(backend, column, vtype)
        elif sub is VariableSubtype.ORDINAL:
            perfil = qualitative.analyze_ordinal(backend, column, vtype)
        elif sub is VariableSubtype.RANK:
            perfil = qualitative.analyze_rank(backend, column, vtype)
        else:
            perfil = qualitative.analyze_nominal(backend, column, vtype)
    elif vtype.var_class is VariableClass.QUANTITATIVE:
        if sub is VariableSubtype.DISCRETE:
            perfil = quantitative.analyze_discrete(backend, column, vtype)
        else:
            perfil = quantitative.analyze_continuous(backend, column, vtype)
    elif vtype.var_class is VariableClass.TEMPORAL:
        if sub is VariableSubtype.DURATION:
            perfil = temporal.analyze_duration(backend, column, vtype)
        else:
            perfil = temporal.analyze_instant(backend, column, vtype)
    elif vtype.var_class is VariableClass.IDENTIFIER:
        perfil = qualitative.analyze_identifier(backend, column, vtype)
    else:
        perfil = ColumnProfile(
            name=column, inferred_type=vtype, notes=list(vtype.warnings)
        )

    try:
        perfil.narrative = gerar_narrativa(perfil, backend.config.language)
    except Exception as e:  # noqa: BLE001 — narrativa não deve derrubar o perfil
        perfil.notes.append(f"Narrativa não gerada: {type(e).__name__}")
    return perfil


__all__ = ["despachar"]

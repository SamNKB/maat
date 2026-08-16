"""Testes da taxonomia — a única parte já implementada."""

import pytest

from maat.core.taxonomy import VariableClass, VariableSubtype, VariableType


def test_subtipo_valido():
    vt = VariableType(VariableClass.QUANTITATIVE, VariableSubtype.CONTINUOUS)
    assert vt.subtype is VariableSubtype.CONTINUOUS


def test_subtipo_invalido_para_classe():
    with pytest.raises(ValueError):
        VariableType(VariableClass.QUALITATIVE, VariableSubtype.CONTINUOUS)


def test_ordinal_sem_ordem_gera_aviso():
    vt = VariableType(VariableClass.QUALITATIVE, VariableSubtype.ORDINAL)
    assert vt.warnings


def test_ordinal_com_ordem_nao_gera_aviso():
    vt = VariableType(
        VariableClass.QUALITATIVE,
        VariableSubtype.ORDINAL,
        ordered_levels=["baixo", "médio", "alto"],
    )
    assert not vt.warnings

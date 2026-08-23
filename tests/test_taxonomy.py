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


def test_rank_exige_referencia():
    """A mitigação do falso positivo (§3.3) é obrigatória por construção."""
    with pytest.raises(ValueError, match="rank_reference"):
        VariableType(VariableClass.QUALITATIVE, VariableSubtype.RANK)


def test_rank_com_referencia():
    vt = VariableType(
        VariableClass.QUALITATIVE,
        VariableSubtype.RANK,
        rank_reference="Global_Sales",
        rank_spearman=-0.9996,
    )
    assert vt.rank_reference == "Global_Sales"


def test_identificador_aceita_chave_e_codigo():
    for sub in (VariableSubtype.KEY, VariableSubtype.CODE):
        assert VariableType(VariableClass.IDENTIFIER, sub).subtype is sub


def test_identificador_nao_aceita_subtipo_de_outra_classe():
    with pytest.raises(ValueError):
        VariableType(VariableClass.IDENTIFIER, VariableSubtype.CONTINUOUS)

"""Testes da inferência de tipos sobre fixtures reais do benchmark.

Cada teste corresponde a uma decisão registrada em docs/fluxo-de-analises.md —
o número da seção está no docstring. Se um destes quebrar, ou o código
regrediu ou a decisão mudou; nos dois casos a documentação precisa ser
revisitada junto.
"""

from __future__ import annotations

import pytest

from conftest import carregar_fixture
from maat.core.taxonomy import (
    CardinalityRegime,
    VariableClass,
    VariableSubtype,
)


def tipos(df, config=None):
    import maat

    return maat.describe(df, config).schema


# --------------------------------------------------------------------------
# §2 qualitativas
# --------------------------------------------------------------------------


def test_binaria_detecta_dois_niveis():
    """§2.5: exatamente 2 valores distintos, em qualquer codificação."""
    esquema = tipos(carregar_fixture("titanic"))
    assert esquema["Survived"].subtype is VariableSubtype.BINARY  # inteiro 0/1
    assert esquema["Sex"].subtype is VariableSubtype.BINARY  # string male/female


def test_regime_categorico_para_poucos_niveis():
    """§2.0: k pequeno → todos os níveis no resumo."""
    esquema = tipos(carregar_fixture("titanic"))
    assert esquema["Embarked"].regime is CardinalityRegime.CATEGORICAL


def test_regime_textual_quando_quase_tudo_e_unico():
    """§2.0: k ≈ n → a frequência é inútil, a string vira o objeto."""
    esquema = tipos(carregar_fixture("titanic"))
    assert esquema["Name"].regime is CardinalityRegime.TEXTUAL


def test_ordinal_por_numero_inicial_no_rotulo():
    """§2.3: única inferência automática de ordem aceita."""
    esquema = tipos(carregar_fixture("faixas_etarias"))
    vt = esquema["age"]
    assert vt.subtype is VariableSubtype.ORDINAL
    assert vt.ordered_levels[0].startswith("5-14")
    assert vt.ordered_levels[-1].startswith("75+")


def test_ordinal_declarada_pelo_usuario():
    """§2.3: a ordem declarada sempre vence a heurística."""
    import maat

    df = carregar_fixture("wine_quality")
    cfg = maat.Config(ordinal_levels={"quality": [3, 4, 5, 6, 7, 8]})
    vt = tipos(df, cfg)["quality"]
    assert vt.subtype is VariableSubtype.ORDINAL
    assert vt.ordered_levels == ["3", "4", "5", "6", "7", "8"]


def test_sem_ordem_declarada_wine_quality_e_discreta():
    """§2.3: sem ordem confiável, degrada — a inferência não adivinha."""
    vt = tipos(carregar_fixture("wine_quality"))["quality"]
    assert vt.var_class is VariableClass.QUANTITATIVE
    assert vt.subtype is VariableSubtype.DISCRETE


# --------------------------------------------------------------------------
# §3 quantitativas
# --------------------------------------------------------------------------


def test_inteiros_sao_sempre_discreta():
    """§3.1: contagem é contagem; o k só escolhe o regime."""
    esquema = tipos(carregar_fixture("titanic"))
    assert esquema["SibSp"].subtype is VariableSubtype.DISCRETE
    assert esquema["SibSp"].regime is CardinalityRegime.TABLE


def test_casas_decimais_sao_continua():
    """§3.2: mede, não conta."""
    assert tipos(carregar_fixture("titanic"))["Fare"].subtype is (
        VariableSubtype.CONTINUOUS
    )


def test_float_unico_nao_vira_identificador():
    """Regressão: toda medição contínua é única por natureza; sem exigir
    inteiros, qualquer float de base pequena virava identificador."""
    esquema = tipos(carregar_fixture("wine_quality"))
    assert esquema["alcohol"].var_class is VariableClass.QUANTITATIVE


# --------------------------------------------------------------------------
# §3.3 identificador, código e rank
# --------------------------------------------------------------------------


def test_chave_primaria_vira_identificador():
    """§3.3: k ≈ n sem monotonia → chave, fora das estatísticas."""
    vt = tipos(carregar_fixture("titanic"))["PassengerId"]
    assert vt.var_class is VariableClass.IDENTIFIER
    assert vt.subtype is VariableSubtype.KEY


def test_cnpj_valido_vira_codigo():
    """§3.3: o dígito verificador é o sinal mais forte, e independe de idioma."""
    vt = tipos(carregar_fixture("camara_fornecedores"))["txtCNPJCPF"]
    assert vt.var_class is VariableClass.IDENTIFIER
    assert vt.subtype is VariableSubtype.CODE
    assert any("dígito verificador" in a for a in vt.warnings)


def test_rank_nomeia_sempre_a_coluna_de_referencia():
    """§3.3: a mitigação do falso positivo — o engano fica visível."""
    vt = tipos(carregar_fixture("rank_videogame"))["Rank"]
    assert vt.subtype is VariableSubtype.RANK
    assert vt.rank_reference is not None
    assert abs(vt.rank_spearman) >= 0.99


def test_falso_positivo_conhecido_do_rank():
    """§3.3: `CustomerID` do mall é classificado como rank — decisão
    consciente, com o custo aceito e mitigado pela referência nomeada."""
    vt = tipos(carregar_fixture("rank_falso_positivo"))["CustomerID"]
    assert vt.subtype is VariableSubtype.RANK
    assert vt.rank_reference == "Annual Income (k$)"


# --------------------------------------------------------------------------
# §4 temporais
# --------------------------------------------------------------------------


def test_data_por_extenso_e_temporal():
    """§4.1: string que parseia em alta taxa vira temporal."""
    vt = tipos(carregar_fixture("datas_extenso"))["date_added"]
    assert vt.var_class is VariableClass.TEMPORAL
    assert vt.subtype is VariableSubtype.INSTANT


def test_formato_mmdd_provado_pelos_dados():
    """§4.1: a prova vem da minoria com o 2º campo > 12."""
    vt = tipos(carregar_fixture("datas_mmdd"))["InvoiceDate"]
    assert vt.var_class is VariableClass.TEMPORAL
    assert any("mm/dd provado" in a for a in vt.warnings)


def test_formato_indecidivel_e_declarado_nao_adivinhado():
    """§4.1: o pandas escolhe em silêncio; o maat diz que não dá para saber."""
    vt = tipos(carregar_fixture("datas_indecidiveis"))["InvoiceDate"]
    assert vt.var_class is VariableClass.TEMPORAL
    assert any("indecidível" in a for a in vt.warnings)
    assert vt.confidence < 1.0


# --------------------------------------------------------------------------
# §0 princípios
# --------------------------------------------------------------------------


def test_override_do_usuario_vence_a_inferencia():
    """§0.1: a inferência propõe, o usuário dispõe."""
    import maat
    from maat.core.taxonomy import VariableType

    df = carregar_fixture("titanic")
    declarado = VariableType(
        VariableClass.QUALITATIVE,
        VariableSubtype.ORDINAL,
        ordered_levels=["1", "2", "3"],
    )
    esquema = tipos(df, maat.Config(overrides={"Pclass": declarado}))
    assert esquema["Pclass"].subtype is VariableSubtype.ORDINAL
    assert esquema["Pclass"].confidence == 1.0


def test_limiar_de_regime_e_parametrizavel():
    """§1.2: os limiares são do usuário, não constantes do maat."""
    import maat

    df = carregar_fixture("titanic")
    assert tipos(df, maat.Config(max_categorical_levels=1))["Embarked"].regime is not (
        CardinalityRegime.CATEGORICAL
    )
    assert tipos(df, maat.Config(max_categorical_levels=30))["Embarked"].regime is (
        CardinalityRegime.CATEGORICAL
    )

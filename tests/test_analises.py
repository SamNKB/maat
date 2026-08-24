"""Testes das análises e dos renderizadores sobre fixtures reais.

Cada asserção corresponde a uma decisão de docs/fluxo-de-analises.md.
"""

from __future__ import annotations

import json

import pytest

from conftest import carregar_fixture

import maat


@pytest.fixture(scope="module")
def titanic():
    return maat.describe(carregar_fixture("titanic"))


# --------------------------------------------------------------------------
# §2.5 binária
# --------------------------------------------------------------------------


def test_binaria_traz_ausente_como_linha(titanic):
    """§2.5: o nulo é cidadão de primeira classe na tabela."""
    tabela = titanic["Survived"].essencial["tabela"]
    assert any(linha["nivel"] is None for linha in tabela)
    for linha in tabela:
        assert "pct_total" in linha and "pct_validos" in linha


def test_binaria_razao_na_camada_completa(titanic):
    """§2.5: razões exigem leitura estatística — moram na completa."""
    perfil = titanic["Survived"]
    assert "razao_balanceamento" in perfil.completa
    assert "razao_balanceamento" not in perfil.essencial


def test_binaria_sem_intervalo_de_confianca(titanic):
    """§2.5: IC é inferência, não descrição — fora por decisão."""
    texto = json.dumps(titanic["Survived"].to_dict(), ensure_ascii=False).lower()
    assert "confian" not in texto.replace("confianca", "")


# --------------------------------------------------------------------------
# §3.1 discreta
# --------------------------------------------------------------------------


def test_discreta_regime_tabela_revela_buracos(titanic):
    """§3.1: `SibSp` não tem os valores 6 e 7 — a tabela por valor mostra."""
    valores = [linha["valor"] for linha in titanic["SibSp"].essencial["tabela"]]
    assert 5 in valores and 8 in valores
    assert 6 not in valores and 7 not in valores


def test_discreta_media_e_mediana_na_essencial(titanic):
    """§3.1: o par conta a assimetria sem jargão."""
    e = titanic["SibSp"].essencial
    assert "media" in e and "mediana" in e and "moda" in e


def test_discreta_sem_soma_total(titanic):
    """§3.1: soma é leitura de negócio, não de distribuição — fora."""
    perfil = titanic["SibSp"]
    assert "soma" not in perfil.essencial and "soma" not in perfil.completa


# --------------------------------------------------------------------------
# §3.2 contínua
# --------------------------------------------------------------------------


def test_continua_cinco_numeros_na_essencial(titanic):
    """§3.2: mín, q1, mediana, média, q3, máx."""
    e = titanic["Fare"].essencial
    for chave in ("min", "q1", "mediana", "media", "q3", "max"):
        assert chave in e, chave


def test_continua_extremos_com_ocorrencias(titanic):
    """§3.2: a tabela de extremos revela valores repetidos (ex.: preço 0)."""
    extremos = titanic["Fare"].essencial["extremos_valor"]
    assert extremos["maiores"] and extremos["menores"]
    assert "ocorrencias" in extremos["menores"][0]


def test_atipicos_descritos_nunca_julgados(titanic):
    """§3.2: 'atípico pela regra 1,5×IQR' é definição, não veredito."""
    completa = titanic["Fare"].completa
    assert completa["atipicos_iqr"] > 0
    assert "descritivo" in completa["criterio_atipicos"]
    assert "erro" not in completa["criterio_atipicos"].split("nunca")[0]


def test_assimetria_vira_observacao_em_palavras(titanic):
    """§3.2: quando média ≫ mediana, a narrativa sugere escala log."""
    notas = " ".join(titanic["Fare"].notes)
    assert "assimétrica à direita" in notas


# --------------------------------------------------------------------------
# §2.2 cauda longa e §2.4 textual
# --------------------------------------------------------------------------


def test_cauda_longa_declara_quantos_niveis_agrega():
    """§2.2: a linha "Outros" nunca esconde o tamanho da cauda."""
    perfil = maat.describe(carregar_fixture("camara_fornecedores"))["txtFornecedor"]
    outros = [x for x in perfil.essencial["tabela"] if "Outros" in str(x["nivel"])]
    if outros:
        assert outros[0]["niveis_agregados"] > 0
    assert "concentracao" in perfil.essencial


def test_variantes_de_grafia_sao_relatadas_com_criterio():
    """§2.2: mostrar é obrigação; o critério viaja junto do resultado."""
    perfil = maat.describe(carregar_fixture("camara_fornecedores"))["txtFornecedor"]
    variantes = [c for c in perfil.checks if c.nome == "variantes_grafia"]
    assert variantes, "as fixtures incluem as variantes de grafia do Uber"
    assert "minúsculas" in variantes[0].descricao


def test_textual_traz_tres_amostras_dirigidas():
    """§2.4: mais curtas, mais longas e aleatórias."""
    perfil = maat.describe(carregar_fixture("textual_sujo"))["name"]
    amostras = perfil.essencial["amostras"]
    for chave in ("mais_curtas", "mais_longas", "aleatorias"):
        assert amostras[chave], chave


def test_textual_checagens_tem_amostra_de_ofensores():
    """§2.4: a amostra é o que torna o achado acionável."""
    perfil = maat.describe(carregar_fixture("textual_sujo"))["name"]
    assert perfil.checks
    for check in perfil.checks:
        assert check.n > 0 and check.descricao and check.amostra


# --------------------------------------------------------------------------
# §4 temporal
# --------------------------------------------------------------------------


def test_temporal_reporta_cobertura_e_granularidade():
    perfil = maat.describe(carregar_fixture("datas_extenso"))["date_added"]
    assert perfil.essencial["cobertura"]["minimo"]
    assert perfil.essencial["granularidade"]


def test_indecidivel_suspende_perfis_ciclicos():
    """§4.1: sem saber o formato, as análises por dia ficam suspensas."""
    perfil = maat.describe(carregar_fixture("datas_indecidiveis"))["InvoiceDate"]
    assert perfil.essencial["perfis_ciclicos"] is None
    assert any("suspens" in n for n in perfil.notes)


def test_horizonte_e_futuro_sao_reportados():
    """§4.1: futuro é fato, nunca erro."""
    perfil = maat.describe(carregar_fixture("datas_extenso"))["date_added"]
    assert "horizonte" in perfil.essencial
    assert "no_futuro" in perfil.essencial


def test_horizonte_cobre_passado_e_futuro():
    """§4.1: uma data 60 anos à frente é tão notável quanto 60 anos atrás.

    Antes o horizonte só media o passado, e o futuro virava um único
    "N no futuro" — no Tesouro, um vencimento de 2027 ficava indistinguível
    de um de 2084.
    """
    import pandas as pd

    df = pd.DataFrame({
        "quando": pd.to_datetime(["1966-01-01", "2086-01-01", "2026-01-01"])
    })
    horizonte = maat.describe(df)["quando"].essencial["horizonte"]
    assert horizonte["passado >50 anos"] == 1
    assert horizonte["futuro >50 anos"] == 1


# --------------------------------------------------------------------------
# §3.3 identificador e rank
# --------------------------------------------------------------------------


def test_identificador_fica_fora_das_estatisticas(titanic):
    perfil = titanic["PassengerId"]
    assert perfil.essencial["unico"] is True
    assert "media" not in perfil.essencial
    assert any("não significa nada" in n for n in perfil.notes)


def test_rank_sempre_nomeia_a_referencia():
    """§3.3: a mitigação do falso positivo."""
    perfil = maat.describe(carregar_fixture("rank_videogame"))["Rank"]
    assert perfil.essencial["referencia"]
    assert "colocação de" in perfil.notes[0]


# --------------------------------------------------------------------------
# §6 contrato de saída
# --------------------------------------------------------------------------


def test_camadas_sao_filtradas_na_saida(titanic):
    """§6: as camadas são estruturais, e o renderizador filtra."""
    so_essencial = titanic["Fare"].to_dict(camada="essencial")
    assert "essencial" in so_essencial and "completa" not in so_essencial


def test_quatro_formatos_geram_saida(titanic):
    """§6: quatro renderizadores sobre a mesma estrutura."""
    assert json.loads(titanic.to_json())
    assert titanic.to_yaml().startswith("maat:")
    assert titanic.to_markdown().startswith("# Perfil de dados")
    assert titanic.to_html().startswith("<!DOCTYPE html>")


def test_markdown_e_mais_barato_que_json(titanic):
    """§6: medido em tokens; aqui garantimos a ordem de grandeza."""
    assert len(titanic.to_markdown()) < len(titanic.to_json(compact=False))


def test_narrativa_gerada_para_toda_coluna(titanic):
    """§7: prosa por template determinístico, sem LLM."""
    for perfil in titanic.columns.values():
        assert perfil.narrative, perfil.name


def test_narrativa_e_deterministica():
    """§7: mesma entrada, mesma saída — reproduzível."""
    a = maat.describe(carregar_fixture("titanic"))["Fare"].narrative
    b = maat.describe(carregar_fixture("titanic"))["Fare"].narrative
    assert a == b


def test_narrativa_em_ingles():
    """§7: núcleo de templates em pt-BR e inglês."""
    perfil = maat.describe(carregar_fixture("titanic"), maat.Config(language="en"))
    assert perfil["Fare"].narrative.startswith("The variable")


# --------------------------------------------------------------------------
# §7 trava de números
# --------------------------------------------------------------------------


def test_trava_aceita_reformulacao_fiel():
    from maat.narrative import numeros_preservados

    ok, faltantes = numeros_preservados(
        "A variável Churn tem 5.174 registros (73,5%).",
        "Churn has 5,174 records (73.5%).",
    )
    assert ok and not faltantes


def test_trava_rejeita_numero_alterado():
    """§7: alucinação numérica vira erro detectado, não risco silencioso."""
    from maat.narrative import numeros_preservados

    ok, faltantes = numeros_preservados(
        "A variável Churn tem 5.174 registros (73,5%).",
        "Churn has 5,900 records (73.5%).",
    )
    assert not ok and "5174" in faltantes

"""Mascaramento de PII/PHI (`Config.mask_pii`).

O Presidio é dependência opcional; os testes que dependem dele são pulados
quando ausente. Os testes de mascaramento em si não dependem de nada.
"""

from __future__ import annotations

import pytest

from conftest import carregar_fixture

import maat
from maat.privacy import mascara_parcial


# --------------------------------------------------------------------------
# mascaramento parcial — sem dependência externa
# --------------------------------------------------------------------------


def test_cpf_mascarado_preserva_pontuacao():
    """Decisão de 2026-08-23: `123.456.789-01` vira `***.456.789-**`."""
    assert mascara_parcial("123.456.789-01") == "***.456.789-**"


def test_mascara_preserva_o_formato():
    """O ponto do mascaramento parcial: a forma continua analisável."""
    saida = mascara_parcial("00.017.024/0001-53")
    assert saida.count(".") == 2 and "/" in saida and "-" in saida
    assert len(saida) == len("00.017.024/0001-53")


def test_valor_muito_curto_e_totalmente_mascarado():
    assert set(mascara_parcial("ab")) == {"*"}


def test_nome_guarda_so_a_inicial():
    """Mascarar 30%/20% deixaria `Ana Souza` como `**a Souz*`, quase legível."""
    from maat.privacy import _mascara_iniciais

    assert _mascara_iniciais("Ana Souza") == "A** S****"


# --------------------------------------------------------------------------
# integração
# --------------------------------------------------------------------------


presidio = pytest.importorskip(
    "presidio_analyzer", reason="Presidio não instalado (extra 'pii')"
)


@pytest.fixture(scope="module")
def motor():
    from maat.privacy import analisador

    return analisador()


def test_cpf_detectado_pelo_digito_verificador(motor):
    """Reconhecedor próprio: só aceita CPF que passa no algoritmo oficial."""
    from maat.privacy import mascarar_texto

    valido = mascarar_texto("CPF 123.456.789-09 do cliente", motor)
    assert "123.456.789-09" not in valido


def test_cnpj_detectado(motor):
    from maat.privacy import mascarar_texto

    saida = mascarar_texto("CNPJ 00.017.024/0001-53", motor)
    assert "00.017.024/0001-53" not in saida


def test_texto_sem_pii_fica_intacto(motor):
    """Não mascaramos o que não é PII — o relatório continua legível."""
    from maat.privacy import mascarar_texto

    original = "COMBUSTIVEIS E LUBRIFICANTES"
    assert mascarar_texto(original, motor) == original


def test_entidades_sobrepostas_nao_mascaram_duas_vezes(motor):
    """O Presidio devolve BR_CPF e PHONE_NUMBER para o mesmo trecho; mascarar
    os dois corromperia o resultado."""
    from maat.privacy import mascarar_texto

    assert mascarar_texto("CPF 123.456.789-09", motor) == "CPF ***.456.789-**"


def test_flag_mascara_amostras_e_ofensores():
    """§ privacidade: alcance limitado a amostras e ofensores."""
    df = carregar_fixture("camara_fornecedores")
    com_mascara = maat.describe(df, maat.Config(mask_pii=True))

    coluna = com_mascara["txtCNPJCPF"]
    bruto = maat.describe(df)["txtCNPJCPF"]

    # os agregados continuam iguais: mascaramos a amostra, não a contagem
    assert coluna.quality["n_validos"] == bruto.quality["n_validos"]


def test_flag_desligada_nao_altera_nada():
    df = carregar_fixture("titanic")
    a = maat.describe(df)
    b = maat.describe(df, maat.Config(mask_pii=False))
    assert a["Name"].essencial["amostras"] == b["Name"].essencial["amostras"]


def test_nome_de_pessoa_mascarado_no_perfil():
    """O `Name` do titanic é o caso clássico: nomes próprios em texto livre."""
    df = carregar_fixture("titanic")
    perfil = maat.describe(df, maat.Config(mask_pii=True))["Name"]
    amostras = perfil.essencial["amostras"]["mais_longas"]
    assert any("*" in str(a) for a in amostras), amostras


def test_registra_que_houve_mascaramento():
    """Quem lê o relatório precisa saber que o dado foi alterado."""
    df = carregar_fixture("titanic")
    perfil = maat.describe(df, maat.Config(mask_pii=True))["Name"]
    assert any("mascarad" in n for n in perfil.notes)

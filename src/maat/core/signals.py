"""Detecções determinísticas compartilhadas pelos backends.

Todas as regras aqui são **determinísticas e independentes de idioma** —
exigência registrada em §0.2: "critério determinístico e explícito,
declarado junto do resultado, nunca inferência difusa".

Cada função vale para um valor único; os backends as aplicam de forma
vetorizada (pandas) ou distribuída (Spark, via regex/UDF).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# --------------------------------------------------------------------------
# dígito verificador (§3.3) — o sinal mais forte para código
# --------------------------------------------------------------------------

_SO_DIGITOS = re.compile(r"\D")


def valida_cnpj(valor: Any) -> bool:
    """Algoritmo oficial do CNPJ. Medido: 100% no `cvm/CNPJ_FUNDO_CLASSE`,
    0% nos controles."""
    d = _SO_DIGITOS.sub("", str(valor))
    if len(d) != 14 or len(set(d)) == 1:
        return False
    for tam, pesos in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        soma = sum(int(d[i]) * pesos[i] for i in range(tam))
        resto = soma % 11
        if int(d[tam]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


def valida_cpf(valor: Any) -> bool:
    """Algoritmo oficial do CPF."""
    d = _SO_DIGITOS.sub("", str(valor))
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for tam in (9, 10):
        soma = sum(int(d[i]) * (tam + 1 - i) for i in range(tam))
        if int(d[tam]) != (soma * 10) % 11 % 10:
            return False
    return True


# --------------------------------------------------------------------------
# normalização para variantes de grafia (§2.2)
# --------------------------------------------------------------------------

_ESPACOS = re.compile(r"\s+")


def normaliza_nivel(valor: Any) -> str:
    """Critério declarado: minúsculas + sem acentos + espaços colapsados +
    bordas aparadas. Sem semelhança aproximada, sem distância de edição.

    É o que revela `UBER DO BRASIL TECNOLOGIA LTDA.` (10.267) convivendo com
    `Uber Do Brasil Tecnologia Ltda.` (8) na cota parlamentar.
    """
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return _ESPACOS.sub(" ", texto)


CRITERIO_VARIANTES = (
    "níveis idênticos ao converter para minúsculas, remover acentos, "
    "colapsar espaços internos e aparar as bordas"
)


# --------------------------------------------------------------------------
# bateria do regime textual (§2.4) — 15 checagens
# --------------------------------------------------------------------------

CHECAGENS_TEXTO: list[tuple[str, str, str]] = [
    ("espaco_borda", r"^\s|\s$", "espaço no início ou fim"),
    ("espaco_duplo", r"\s{2,}", "espaços consecutivos"),
    ("invisivel", "[​-‏ -‮﻿\xa0]", "zero-width, NBSP ou BOM"),
    ("nao_imprimivel", r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "caractere de controle"),
    ("repeticao", r"(.)\1{3,}", "4 ou mais caracteres iguais seguidos"),
    ("mojibake", r"Ã[\x80-\xbf]|â€|Â[\x80-\xbf]", "dupla codificação UTF-8/Latin-1"),
    ("html_residual", r"&[a-z]{2,6};|<[a-z/][^>]{0,40}>", "entidade ou tag HTML"),
    ("url", r"https?://|www\.[a-z0-9-]+\.", "URL embutida"),
    (
        "markdown",
        r"\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|^#{1,6}\s|```",
        "sintaxe markdown",
    ),
    (
        "pix_brcode",
        r"br\.gov\.bcb\.pix|^000201.*6304[0-9A-Fa-f]{4}$",
        "payload PIX copia-e-cola",
    ),
    ("base64_longo", r"[A-Za-z0-9+/]{60,}={0,2}", "possível payload codificado"),
    ("json_embutido", r"^\s*[\{\[].*[\}\]]\s*$", "JSON ou lista dentro da célula"),
    (
        "cpf_cnpj_mascara",
        r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
        "CPF ou CNPJ mascarado",
    ),
    (
        "placeholder",
        r"(?i)^\s*(?:teste?|test|asd+|qwe+|x{3,}|abc+|123123|0{3,}|n/?a|"
        r"nao se aplica|sem informa|nenhum|vazio|null|none|-{2,}|\.{2,})\s*$",
        "preenchimento de teste ou vazio disfarçado",
    ),
    (
        "misto_alfabeto",
        r"(?=.*[a-zA-Z])(?=.*[Ѐ-ӿͰ-Ͽ])",
        "alfabeto latino misturado com cirílico ou grego",
    ),
]

# --------------------------------------------------------------------------
# padrões dominantes (§2.4, frente 2)
# --------------------------------------------------------------------------

PADROES_DOMINANTES: list[tuple[str, str]] = [
    ("email", r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"),
    ("url", r"^https?://\S+$"),
    ("uuid", r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
             r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"),
    ("cep", r"^\d{5}-?\d{3}$"),
    ("telefone_br", r"^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$"),
    ("cpf", r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$"),
    ("cnpj", r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$"),
]


def mascara_caractere(valor: Any) -> str:
    """Abstrai `"Rua X, 123"` em `"Aaa A, 999"` — revela os formatos que
    convivem no campo sem precisar ler as strings (§2.4, camada completa)."""
    saida = []
    for ch in str(valor):
        if ch.isdigit():
            saida.append("9")
        elif ch.isalpha():
            saida.append("A" if ch.isupper() else "a")
        else:
            saida.append(ch)
    return "".join(saida)


# --------------------------------------------------------------------------
# datas (§4.1)
# --------------------------------------------------------------------------

RE_DATA_AB = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")

# Sentinelas: significam "vazio", não um instante real.
DATAS_SENTINELA: dict[str, str] = {
    "1900-01-01": "zero do Excel / sentinela clássica",
    "1899-12-30": "zero real do Excel",
    "1970-01-01": "epoch Unix — costuma ser 0 convertido",
    "0001-01-01": "mínimo do tipo datetime",
    "9999-12-31": "máximo do tipo — usado como 'sem fim'",
    "2999-12-31": "sentinela de 'nunca expira'",
}

# Rebase do Spark: datas antes do corte mudam de valor entre o calendário
# híbrido (Juliano + Gregoriano) e o Proléptico Gregoriano ao ler Parquet/Avro.
CORTE_GREGORIANO = "1582-10-15"
LACUNA_GREGORIANA = ("1582-10-05", "1582-10-14")

# Limites do datetime64[ns] do pandas — o Spark cobre ano 1 a 9999.
LIMITE_PANDAS_MIN = "1677-09-21"
LIMITE_PANDAS_MAX = "2262-04-11"


def evidencia_formato_data(valores: list[str]) -> tuple[int, int, int]:
    """Conta provas de dd/mm, provas de mm/dd e valores ambíguos.

    Um valor com o primeiro campo > 12 só pode ser dia (prova dd/mm); com o
    segundo campo > 12, prova mm/dd. Medido: 39% a 50% dos valores de uma
    coluna real são individualmente ambíguos — a prova vem da minoria.
    """
    dmy = mdy = ambiguos = 0
    for v in valores:
        m = RE_DATA_AB.match(str(v))
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12 and b <= 12:
            dmy += 1
        elif b > 12 and a <= 12:
            mdy += 1
        elif a <= 12 and b <= 12:
            ambiguos += 1
    return dmy, mdy, ambiguos


RE_NUMERO_INICIAL = re.compile(r"^\s*(\d+)")


def ordem_por_numero_inicial(niveis: list[Any]) -> list[Any] | None:
    """Ordena rótulos pelo número que os abre: `5-14 years` < `15-24 years`.

    Única inferência automática de ordem aceita (§2.3) — determinística e
    sem ambiguidade. Devolve None se algum rótulo não começar com número.
    """
    pares = []
    for nivel in niveis:
        m = RE_NUMERO_INICIAL.match(str(nivel))
        if not m:
            return None
        pares.append((int(m.group(1)), nivel))
    if len({p[0] for p in pares}) != len(pares):
        return None  # empate no número inicial não define ordem
    return [nivel for _, nivel in sorted(pares)]

"""Trava de números — o que torna o LLM seguro para trabalho acadêmico.

O modelo pode reformular o estilo ou traduzir o idioma, mas **não pode tocar
em nenhum número**. Depois de qualquer reformulação, comparamos os tokens
numéricos dos dois textos: se algum sumiu ou mudou, o texto é descartado e o
template original volta com um aviso.

Alucinação numérica deixa de ser risco silencioso e vira erro detectado.
"""

from __future__ import annotations

import re

# Captura inteiros, decimais e percentuais em pt-BR (1.234,56) e en (1,234.56).
RE_NUMERO = re.compile(r"\d[\d.,]*\d|\d")


def _canonico(token: str) -> str:
    """Reduz um número à sua forma comparável, ignorando separadores.

    "5.174" e "5,174" e "5174" viram o mesmo token — o que interessa é que
    os dígitos não mudaram, não como foram formatados no idioma de destino.
    """
    return re.sub(r"[.,]", "", token).lstrip("0") or "0"


def extrair_numeros(texto: str) -> list[str]:
    """Todos os números de um texto, em forma canônica."""
    return [_canonico(t) for t in RE_NUMERO.findall(texto)]


def numeros_preservados(original: str, reformulado: str) -> tuple[bool, list[str]]:
    """Valida que a reformulação não alterou nenhum número.

    Devolve (ok, faltantes). A comparação é por multiconjunto: se o original
    cita 26,5% duas vezes, o reformulado precisa citar duas vezes.
    """
    esperados = extrair_numeros(original)
    obtidos = extrair_numeros(reformulado)
    faltantes = []
    restantes = list(obtidos)
    for numero in esperados:
        if numero in restantes:
            restantes.remove(numero)
        else:
            faltantes.append(numero)
    return (not faltantes), faltantes

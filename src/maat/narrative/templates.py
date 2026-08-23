"""Templates determinísticos de narrativa (§7), em pt-BR e inglês.

Tom acadêmico no MVP — o caso motivador é quem escreve trabalho de
graduação e precisa transformar tabela em parágrafo. Todos os números vêm
do `ColumnProfile`; nenhum é gerado por modelo.
"""

from __future__ import annotations

from typing import Any

from maat.core.profile import ColumnProfile
from maat.core.taxonomy import CardinalityRegime, VariableSubtype

# --------------------------------------------------------------------------
# formatação numérica por idioma
# --------------------------------------------------------------------------


def _num(valor: Any, casas: int = 0, idioma: str = "pt-BR") -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float) and valor != valor:  # NaN
        return "—"
    texto = f"{valor:,.{casas}f}"
    if idioma == "pt-BR":
        texto = texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return texto


def _pct(valor: Any, idioma: str = "pt-BR") -> str:
    if valor is None:
        return "—"
    return _num(valor * 100, 1, idioma) + "%"


# --------------------------------------------------------------------------


def gerar_narrativa(perfil: ColumnProfile, idioma: str = "pt-BR") -> str:
    """Prosa acadêmica a partir do perfil. Determinística e reproduzível."""
    vt = perfil.inferred_type
    if vt.subtype is VariableSubtype.BINARY:
        return _binaria(perfil, idioma)
    if vt.subtype is VariableSubtype.ORDINAL:
        return _ordinal(perfil, idioma)
    if vt.subtype is VariableSubtype.NOMINAL:
        if vt.regime is CardinalityRegime.TEXTUAL:
            return _textual(perfil, idioma)
        return _nominal(perfil, idioma)
    if vt.subtype is VariableSubtype.DISCRETE:
        return _discreta(perfil, idioma)
    if vt.subtype is VariableSubtype.CONTINUOUS:
        return _continua(perfil, idioma)
    if vt.subtype is VariableSubtype.INSTANT:
        return _temporal(perfil, idioma)
    if vt.subtype is VariableSubtype.RANK:
        return _rank(perfil, idioma)
    if vt.subtype in (VariableSubtype.KEY, VariableSubtype.CODE):
        return _identificador(perfil, idioma)
    return _generica(perfil, idioma)


def _abertura(perfil: ColumnProfile, tipo_txt: str, idioma: str) -> str:
    q = perfil.quality
    n = _num(q.get("n_validos", 0), 0, idioma)
    if idioma == "en":
        base = f"The variable **{perfil.name}** is {tipo_txt}, observed in {n} records"
        ausentes = q.get("n_ausentes", 0)
        return base + (
            f", with {_num(ausentes, 0, idioma)} missing values "
            f"({_pct(q.get('pct_ausentes'), idioma)})"
            if ausentes else ", with no missing values"
        )
    base = f"A variável **{perfil.name}** é {tipo_txt}, observada em {n} registros"
    ausentes = q.get("n_ausentes", 0)
    return base + (
        f", com {_num(ausentes, 0, idioma)} valores ausentes "
        f"({_pct(q.get('pct_ausentes'), idioma)})"
        if ausentes else ", sem valores ausentes"
    )


def _binaria(perfil: ColumnProfile, idioma: str) -> str:
    tipo = "binary qualitative" if idioma == "en" else "qualitativa binária"
    linhas = [t for t in perfil.essencial.get("tabela", []) if t["nivel"] is not None]
    if not linhas:
        return _abertura(perfil, tipo, idioma) + "."
    linhas = sorted(linhas, key=lambda x: x["absoluto"], reverse=True)
    a, b = linhas[0], linhas[-1]
    if idioma == "en":
        return (
            _abertura(perfil, tipo, idioma)
            + f". The predominant level is **{a['nivel']}**, present in "
            f"{_num(a['absoluto'], 0, idioma)} records ({_pct(a['pct_validos'], idioma)}), "
            f"while **{b['nivel']}** accounts for {_num(b['absoluto'], 0, idioma)} "
            f"({_pct(b['pct_validos'], idioma)})."
        )
    return (
        _abertura(perfil, tipo, idioma)
        + f". O nível predominante é **{a['nivel']}**, presente em "
        f"{_num(a['absoluto'], 0, idioma)} registros ({_pct(a['pct_validos'], idioma)}), "
        f"enquanto **{b['nivel']}** corresponde a {_num(b['absoluto'], 0, idioma)} "
        f"registros ({_pct(b['pct_validos'], idioma)})."
    )


def _nominal(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    regime = perfil.inferred_type.regime
    k = _num(e.get("k"), 0, idioma)
    tabela = e.get("tabela", [])
    tipo = (
        "qualitative nominal" if idioma == "en" else "qualitativa nominal"
    )
    texto = _abertura(perfil, tipo, idioma)
    texto += (
        f", with {k} distinct levels" if idioma == "en" else f", com {k} níveis distintos"
    )
    if tabela:
        t0 = tabela[0]
        texto += (
            f". The most frequent is **{t0['nivel']}** "
            f"({_num(t0['absoluto'], 0, idioma)}; {_pct(t0['pct_validos'], idioma)})"
            if idioma == "en"
            else f". O nível mais frequente é **{t0['nivel']}** "
            f"({_num(t0['absoluto'], 0, idioma)} registros; "
            f"{_pct(t0['pct_validos'], idioma)})"
        )
    conc = e.get("concentracao") or {}
    if regime is CardinalityRegime.LONG_TAIL and "niveis_para_80pct" in conc:
        n80 = conc["niveis_para_80pct"]
        texto += (
            f". The distribution is concentrated: {_num(n80, 0, idioma)} levels account "
            f"for 80% of observations"
            if idioma == "en"
            else f". A distribuição é concentrada: {_num(n80, 0, idioma)} níveis "
            f"respondem por 80% das observações"
        )
    return texto + "."


def _ordinal(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    tipo = "qualitative ordinal" if idioma == "en" else "qualitativa ordinal"
    texto = _abertura(perfil, tipo, idioma)
    if e.get("k"):
        texto += (
            f", with {_num(e['k'], 0, idioma)} ordered levels"
            if idioma == "en"
            else f", com {_num(e['k'], 0, idioma)} níveis ordenados"
        )
    linhas = e.get("tabela_ordenada") or []
    if linhas:
        maior = max(linhas, key=lambda x: x["absoluto"])
        texto += (
            f". The most frequent level is **{maior['nivel']}** "
            f"({_num(maior['absoluto'], 0, idioma)}; "
            f"{_pct(maior['pct_validos'], idioma)}), and the median category is "
            f"**{e.get('categoria_mediana')}**"
            if idioma == "en"
            else f". O nível mais frequente é **{maior['nivel']}** "
            f"({_num(maior['absoluto'], 0, idioma)} registros; "
            f"{_pct(maior['pct_validos'], idioma)}), e a categoria mediana é "
            f"**{e.get('categoria_mediana')}**"
        )
        ate_mediana = next(
            (x for x in linhas if x["nivel"] == e.get("categoria_mediana")), None
        )
        if ate_mediana:
            texto += (
                f". The cumulative frequency indicates that "
                f"{_pct(ate_mediana['pct_acumulado'], idioma)} of observations lie at or "
                f"below this level"
                if idioma == "en"
                else f". A frequência acumulada indica que "
                f"{_pct(ate_mediana['pct_acumulado'], idioma)} das observações situam-se "
                f"até esse nível"
            )
    return texto + "."


def _textual(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    comp = e.get("comprimento", {})
    tipo = (
        "qualitative nominal in textual regime"
        if idioma == "en"
        else "qualitativa nominal em regime textual"
    )
    texto = _abertura(perfil, tipo, idioma)
    if e.get("k"):
        texto += (
            f", with {_num(e['k'], 0, idioma)} distinct values "
            f"({_pct(e.get('k_sobre_n'), idioma)} unique)"
            if idioma == "en"
            else f", com {_num(e['k'], 0, idioma)} valores distintos "
            f"({_pct(e.get('k_sobre_n'), idioma)} únicos)"
        )
    if comp:
        texto += (
            f". String length ranges from {_num(comp.get('min'), 0, idioma)} to "
            f"{_num(comp.get('max'), 0, idioma)} characters, with median "
            f"{_num(comp.get('mediana'), 0, idioma)}"
            if idioma == "en"
            else f". O comprimento varia de {_num(comp.get('min'), 0, idioma)} a "
            f"{_num(comp.get('max'), 0, idioma)} caracteres, com mediana "
            f"{_num(comp.get('mediana'), 0, idioma)}"
        )
    if perfil.checks:
        maior = max(perfil.checks, key=lambda c: c.n)
        texto += (
            f". Among the quality checks, **{maior.nome}** occurred most often "
            f"({_num(maior.n, 0, idioma)} records; {_pct(maior.pct, idioma)})"
            if idioma == "en"
            else f". Entre as checagens de qualidade, **{maior.nome}** foi a mais "
            f"frequente ({_num(maior.n, 0, idioma)} registros; {_pct(maior.pct, idioma)})"
        )
    return texto + "."


def _discreta(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    tipo = "discrete quantitative" if idioma == "en" else "quantitativa discreta"
    texto = _abertura(perfil, tipo, idioma)
    texto += (
        f", ranging from {_num(e.get('min'), 0, idioma)} to "
        f"{_num(e.get('max'), 0, idioma)}"
        if idioma == "en"
        else f", variando de {_num(e.get('min'), 0, idioma)} a "
        f"{_num(e.get('max'), 0, idioma)}"
    )
    tabela = e.get("tabela") or []
    if tabela:
        maior = max(tabela, key=lambda x: x["absoluto"])
        texto += (
            f". The value {maior['valor']} predominates "
            f"({_num(maior['absoluto'], 0, idioma)} records; "
            f"{_pct(maior['pct_validos'], idioma)})"
            if idioma == "en"
            else f". Predomina o valor {maior['valor']} "
            f"({_num(maior['absoluto'], 0, idioma)} registros; "
            f"{_pct(maior['pct_validos'], idioma)})"
        )
    texto += (
        f", with mean {_num(e.get('media'), 2, idioma)} and median "
        f"{_num(e.get('mediana'), 2, idioma)}"
        if idioma == "en"
        else f", com média {_num(e.get('media'), 2, idioma)} e mediana "
        f"{_num(e.get('mediana'), 2, idioma)}"
    )
    return texto + "."


def _continua(perfil: ColumnProfile, idioma: str) -> str:
    e, c = perfil.essencial, perfil.completa
    tipo = "continuous quantitative" if idioma == "en" else "quantitativa contínua"
    texto = _abertura(perfil, tipo, idioma)
    texto += (
        f", ranging from {_num(e.get('min'), 2, idioma)} to "
        f"{_num(e.get('max'), 2, idioma)}"
        if idioma == "en"
        else f", variando de {_num(e.get('min'), 2, idioma)} a "
        f"{_num(e.get('max'), 2, idioma)}"
    )
    media, mediana = e.get("media"), e.get("mediana")
    if media is not None and mediana is not None:
        if media > mediana:
            texto += (
                f". The mean ({_num(media, 2, idioma)}) exceeds the median "
                f"({_num(mediana, 2, idioma)}), indicating a right-skewed distribution"
                if idioma == "en"
                else f". A média ({_num(media, 2, idioma)}) supera a mediana "
                f"({_num(mediana, 2, idioma)}), indicando distribuição assimétrica "
                f"à direita — valores extremos elevam a média, e a mediana representa "
                f"melhor o caso típico"
            )
        else:
            texto += (
                f". Mean ({_num(media, 2, idioma)}) and median "
                f"({_num(mediana, 2, idioma)}) are close, suggesting a balanced "
                f"distribution"
                if idioma == "en"
                else f". Média ({_num(media, 2, idioma)}) e mediana "
                f"({_num(mediana, 2, idioma)}) são próximas, sugerindo distribuição "
                f"equilibrada"
            )
    atipicos = c.get("atipicos_iqr")
    if atipicos:
        texto += (
            f". By the 1.5×IQR rule, {_num(atipicos, 0, idioma)} observations "
            f"({_pct(c.get('pct_atipicos_iqr'), idioma)}) are atypical"
            if idioma == "en"
            else f". Pela regra de 1,5×IQR, {_num(atipicos, 0, idioma)} observações "
            f"({_pct(c.get('pct_atipicos_iqr'), idioma)}) são atípicas"
        )
    return texto + "."


def _temporal(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    cob = e.get("cobertura", {})
    tipo = "a temporal variable" if idioma == "en" else "temporal (instante)"
    texto = _abertura(perfil, tipo, idioma)
    if cob.get("minimo"):
        texto += (
            f", covering from {cob['minimo'][:10]} to {cob['maximo'][:10]} "
            f"({_num(cob.get('amplitude_dias'), 0, idioma)} days)"
            if idioma == "en"
            else f", cobrindo de {cob['minimo'][:10]} a {cob['maximo'][:10]} "
            f"({_num(cob.get('amplitude_dias'), 0, idioma)} dias)"
        )
    if e.get("granularidade"):
        texto += (
            f", at {e['granularidade']} granularity"
            if idioma == "en"
            else f", com granularidade {e['granularidade']}"
        )
    if e.get("no_futuro"):
        texto += (
            f". {_num(e['no_futuro'], 0, idioma)} records "
            f"({_pct(e.get('pct_futuro'), idioma)}) fall in the future"
            if idioma == "en"
            else f". {_num(e['no_futuro'], 0, idioma)} registros "
            f"({_pct(e.get('pct_futuro'), idioma)}) situam-se no futuro"
        )
    return texto + "."


def _rank(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    tipo = "a rank (position)" if idioma == "en" else "um rank (colocação)"
    texto = _abertura(perfil, tipo, idioma)
    texto += (
        f", ranging from {_num(e.get('min'), 0, idioma)} to "
        f"{_num(e.get('max'), 0, idioma)}, ordered by **{e.get('referencia')}**"
        if idioma == "en"
        else f", variando de {_num(e.get('min'), 0, idioma)} a "
        f"{_num(e.get('max'), 0, idioma)}, ordenando **{e.get('referencia')}**"
    )
    return texto + "."


def _identificador(perfil: ColumnProfile, idioma: str) -> str:
    e = perfil.essencial
    eh_codigo = e.get("subtipo") == "code"
    if idioma == "en":
        tipo = "an entity code" if eh_codigo else "a row identifier"
    else:
        tipo = "um código de entidade" if eh_codigo else "um identificador de linha"
    texto = _abertura(perfil, tipo, idioma)
    texto += (
        f", with {_num(e.get('k'), 0, idioma)} distinct values"
        if idioma == "en"
        else f", com {_num(e.get('k'), 0, idioma)} valores distintos"
    )
    if eh_codigo and e.get("linhas_por_valor"):
        texto += (
            f" and {_num(e['linhas_por_valor'], 1, idioma)} rows per value"
            if idioma == "en"
            else f" e {_num(e['linhas_por_valor'], 1, idioma)} linhas por valor"
        )
    texto += (
        ". Statistical summaries do not apply."
        if idioma == "en"
        else ". Resumos estatísticos não se aplicam."
    )
    return texto


def _generica(perfil: ColumnProfile, idioma: str) -> str:
    tipo = perfil.inferred_type.var_class.value
    return _abertura(perfil, tipo, idioma) + "."

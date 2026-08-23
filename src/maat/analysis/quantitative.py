"""Análises de variáveis quantitativas (seção 3 do fluxo de análises)."""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile, VizSuggestion
from maat.core.taxonomy import CardinalityRegime, VariableType


def _base(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    n_total = backend.n_rows()
    resumo = backend.numeric_summary(column)
    n_validos = int(resumo.get("n", 0))
    return ColumnProfile(
        name=column,
        inferred_type=vtype,
        quality={
            "n": n_total,
            "n_validos": n_validos,
            "n_ausentes": n_total - n_validos,
            "pct_ausentes": (n_total - n_validos) / n_total if n_total else 0.0,
            "quantile_error": resumo.get("quantile_error", 0.0),
        },
        notes=list(vtype.warnings),
    ), resumo


def analyze_discrete(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Contagens — seção 3.1 (consolidada).

    Regime TABLE: frequência por valor exato, que revela buracos (o `SibSp`
    do titanic não tem os valores 6 e 7).
    Regime HISTOGRAM: bins inteiros + tabela de extremos de frequência.

    Essencial: tabela, mínimo, máximo, moda, média e mediana — o par
    média × mediana conta a assimetria sem jargão.
    Fora por decisão: soma total (leitura de negócio, não de distribuição).
    """
    perfil, resumo = _base(backend, column, vtype)
    n_validos = perfil.quality["n_validos"]

    perfil.essencial = {
        "min": resumo.get("min"),
        "max": resumo.get("max"),
        "moda": resumo.get("moda"),
        "media": resumo.get("media"),
        "mediana": resumo.get("mediana"),
    }

    if vtype.regime is CardinalityRegime.TABLE:
        contagens = backend.value_counts(column)
        ordenados = sorted(contagens.items(), key=lambda x: x[0])
        perfil.essencial["tabela"] = [
            {"valor": v, "absoluto": q, "pct_validos": q / n_validos if n_validos else 0}
            for v, q in ordenados
        ]
        perfil.essencial["regime"] = "tabela"
        perfil.viz_suggestions = [
            VizSuggestion(
                "barras_por_valor",
                {"valores": [v for v, _ in ordenados],
                 "contagens": [q for _, q in ordenados]},
                "Cada valor inteiro é uma barra — revela buracos na sequência",
            )
        ]
    else:
        perfil.essencial["regime"] = "histograma"
        perfil.essencial["histograma"] = backend.histogram(column, bins=30)
        if hasattr(backend, "frequency_extremes"):
            extremos = backend.frequency_extremes(
                column, backend.config.discrete_extremes_levels
            )
            perfil.essencial["extremos_frequencia"] = {
                "mais_frequentes": [
                    {"valor": v, "absoluto": q,
                     "pct_validos": q / n_validos if n_validos else 0}
                    for v, q in extremos["mais_frequentes"]
                ],
                "menos_frequentes": [
                    {"valor": v, "absoluto": q,
                     "pct_validos": q / n_validos if n_validos else 0}
                    for v, q in extremos["menos_frequentes"]
                ],
            }
        perfil.viz_suggestions = [
            VizSuggestion(
                "histograma",
                perfil.essencial["histograma"],
                "Bins inteiros — cardinalidade alta demais para tabela por valor",
            )
        ]

    perfil.completa = {
        "desvio_padrao": resumo.get("desvio_padrao"),
        "q1": resumo.get("q1"),
        "q3": resumo.get("q3"),
        "iqr": resumo.get("iqr"),
        "pct_zeros": resumo.get("pct_zeros"),
        "pct_negativos": resumo.get("pct_negativos"),
    }
    _nota_assimetria(perfil, resumo)
    return perfil


def analyze_continuous(
    backend: Backend, column: str, vtype: VariableType
) -> ColumnProfile:
    """Medições — seção 3.2 (consolidada).

    Essencial: resumo de cinco números + média, histograma e tabela de
    extremos de valor (n maiores e n menores, com contagem).
    Completa: quantis de cauda, dispersão, forma e atípicos 1,5×IQR —
    descritos, nunca julgados como erro.
    """
    perfil, resumo = _base(backend, column, vtype)
    n = backend.config.continuous_extremes_levels
    extremos = backend.value_extremes(column, n)

    perfil.essencial = {
        "min": resumo.get("min"),
        "q1": resumo.get("q1"),
        "mediana": resumo.get("mediana"),
        "media": resumo.get("media"),
        "q3": resumo.get("q3"),
        "max": resumo.get("max"),
        "histograma": backend.histogram(column, bins=30),
        "extremos_valor": {
            "maiores": [{"valor": v, "ocorrencias": q} for v, q in extremos["maiores"]],
            "menores": [{"valor": v, "ocorrencias": q} for v, q in extremos["menores"]],
        },
    }
    perfil.completa = {
        "p1": resumo.get("p1"),
        "p5": resumo.get("p5"),
        "p95": resumo.get("p95"),
        "p99": resumo.get("p99"),
        "desvio_padrao": resumo.get("desvio_padrao"),
        "iqr": resumo.get("iqr"),
        "cv": resumo.get("cv"),
        "assimetria": resumo.get("assimetria"),
        "curtose": resumo.get("curtose"),
        "atipicos_iqr": resumo.get("atipicos_iqr"),
        "pct_atipicos_iqr": resumo.get("pct_atipicos_iqr"),
        "criterio_atipicos": "fora de [q1 − 1,5×IQR, q3 + 1,5×IQR]; descritivo, "
                             "nunca veredito de erro",
    }
    perfil.viz_suggestions = [
        VizSuggestion("histograma", perfil.essencial["histograma"],
                      "Forma geral da distribuição"),
        VizSuggestion("boxplot",
                      {k: resumo.get(k) for k in ("min", "q1", "mediana", "q3", "max")},
                      "Resumo compacto com atípicos evidentes", camada="completa"),
    ]
    _nota_assimetria(perfil, resumo)
    return perfil


def _nota_assimetria(perfil: ColumnProfile, resumo: dict) -> None:
    """Quando média ≫ mediana, sugerir leitura em escala logarítmica."""
    media, mediana = resumo.get("media"), resumo.get("mediana")
    if media is None or mediana is None or not mediana:
        return
    if media > mediana * 1.2:
        perfil.notes.append(
            "Média supera a mediana: distribuição assimétrica à direita — a mediana "
            "representa melhor o caso típico, e a leitura em escala logarítmica ajuda"
        )
    elif mediana > media * 1.2:
        perfil.notes.append(
            "Mediana supera a média: distribuição assimétrica à esquerda"
        )

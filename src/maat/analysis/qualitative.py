"""Análises de variáveis qualitativas (seção 2 do fluxo de análises).

Recebe agregados do backend e produz o `ColumnProfile` — nunca toca nos
dados brutos (§0.4).
"""

from __future__ import annotations

import math
from typing import Any

from maat.backends.base import Backend
from maat.core.profile import Check, ColumnProfile, VizSuggestion
from maat.core.signals import CRITERIO_VARIANTES
from maat.core.taxonomy import CardinalityRegime, VariableSubtype, VariableType


def _base(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    n_total = backend.n_rows()
    contagens = backend.contagens(column)
    n_validos = sum(contagens.values())
    return ColumnProfile(
        name=column,
        inferred_type=vtype,
        quality={
            "n": n_total,
            "n_validos": n_validos,
            "n_ausentes": n_total - n_validos,
            "pct_ausentes": (n_total - n_validos) / n_total if n_total else 0.0,
        },
        notes=list(vtype.warnings),
    )


def analyze_binary(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Exatamente 2 níveis — seção 2.5 (consolidada).

    Essencial: tabela de frequência com o ausente como linha própria
    (absoluto, % do total, % dos válidos).
    Completa: nível dominante e razão de balanceamento.
    Fora por decisão: intervalo de confiança (é inferência, não descrição),
    par semântico e alertas por limiar.
    """
    perfil = _base(backend, column, vtype)
    contagens = backend.contagens(column)
    n, n_validos = perfil.quality["n"], perfil.quality["n_validos"]
    ausentes = perfil.quality["n_ausentes"]

    tabela = [
        {
            "nivel": nivel,
            "absoluto": qtd,
            "pct_total": qtd / n if n else 0.0,
            "pct_validos": qtd / n_validos if n_validos else 0.0,
        }
        for nivel, qtd in contagens.items()
    ]
    tabela.append({
        "nivel": None,
        "absoluto": ausentes,
        "pct_total": ausentes / n if n else 0.0,
        "pct_validos": None,
    })
    perfil.essencial = {"k": len(contagens), "tabela": tabela}

    if len(contagens) == 2:
        valores = list(contagens.values())
        dominante = max(contagens, key=contagens.get)
        perfil.completa = {
            "nivel_dominante": dominante,
            "razao_balanceamento": max(valores) / min(valores) if min(valores) else None,
        }

    perfil.viz_suggestions = [
        VizSuggestion(
            "proporcao",
            {"niveis": [t["nivel"] for t in tabela if t["nivel"] is not None],
             "pcts": [t["pct_validos"] for t in tabela if t["nivel"] is not None]},
            "Barra única de proporção — gráfico com duas barras é desperdício de tela",
        )
    ]
    return perfil


def analyze_nominal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Nominal — despacha pelo regime de cardinalidade (§2.0)."""
    if vtype.regime is CardinalityRegime.TEXTUAL:
        return analyze_textual(backend, column, vtype)
    if vtype.regime is CardinalityRegime.LONG_TAIL:
        return analyze_long_tail(backend, column, vtype)
    return analyze_categorical(backend, column, vtype)


def analyze_categorical(
    backend: Backend, column: str, vtype: VariableType
) -> ColumnProfile:
    """Regime categórico (§2.1): poucos níveis, todos no resumo."""
    perfil = _base(backend, column, vtype)
    contagens = backend.contagens(column)
    n_validos = perfil.quality["n_validos"]

    tabela = [
        {"nivel": nivel, "absoluto": qtd, "pct_validos": qtd / n_validos}
        for nivel, qtd in contagens.items()
    ]
    dominante = max(contagens, key=contagens.get) if contagens else None
    perfil.essencial = {
        "k": len(contagens),
        "tabela": tabela,
        "moda": dominante,
        "forca_moda": contagens[dominante] / n_validos if dominante is not None else None,
    }
    perfil.completa = {
        "entropia_normalizada": _entropia_normalizada(list(contagens.values())),
        "desbalanceamento": (
            max(contagens.values()) / min(contagens.values())
            if contagens and min(contagens.values())
            else None
        ),
    }
    perfil.viz_suggestions = [
        VizSuggestion(
            "barras",
            {"niveis": list(contagens), "contagens": list(contagens.values())},
            "Barras ordenadas por frequência",
        )
    ]
    return perfil


def analyze_long_tail(
    backend: Backend, column: str, vtype: VariableType
) -> ColumnProfile:
    """Regime cauda longa (§2.2, consolidada).

    Essencial: top-N + linha "Outros" declarando quantos níveis agrega;
    concentração (níveis para 50%/80%/95%); k, singletons e o número de
    grupos de variantes de grafia.
    """
    perfil = _base(backend, column, vtype)
    contagens = backend.contagens(column)
    n_validos = perfil.quality["n_validos"]
    top_n = backend.config.long_tail_top_n

    itens = list(contagens.items())
    topo = itens[:top_n]
    resto = itens[top_n:]
    tabela = [
        {"nivel": nivel, "absoluto": qtd, "pct_validos": qtd / n_validos}
        for nivel, qtd in topo
    ]
    if resto:
        soma = sum(q for _, q in resto)
        tabela.append({
            "nivel": f"Outros ({len(resto)} níveis)",
            "absoluto": soma,
            "pct_validos": soma / n_validos,
            "niveis_agregados": len(resto),
        })

    perfil.essencial = {
        "k": len(contagens),
        "tabela": tabela,
        "concentracao": _concentracao(list(contagens.values()), n_validos),
        "singletons": sum(1 for q in contagens.values() if q == 1),
        "pct_singletons": (
            sum(1 for q in contagens.values() if q == 1) / len(contagens)
            if contagens else 0.0
        ),
    }

    grupos = backend.spelling_variant_groups(column)
    perfil.essencial["grupos_variantes"] = len(grupos)
    if grupos:
        perfil.checks.append(
            Check(
                nome="variantes_grafia",
                descricao=CRITERIO_VARIANTES,
                n=sum(len(g) for g in grupos),
                pct=sum(len(g) for g in grupos) / len(contagens),
                amostra=[
                    [{"nivel": v, "n": q} for v, q in grupo]
                    for grupo in grupos[:5]
                ],
            )
        )

    perfil.completa = {
        "herfindahl": sum((q / n_validos) ** 2 for q in contagens.values()),
        "entropia_normalizada": _entropia_normalizada(list(contagens.values())),
        "grupos_variantes": [
            [{"nivel": v, "n": q} for v, q in grupo] for grupo in grupos
        ],
    }
    perfil.viz_suggestions = [
        VizSuggestion(
            "pareto",
            {"niveis": [n for n, _ in topo], "contagens": [q for _, q in topo]},
            "Pareto — mostra concentração e cauda juntas",
        )
    ]
    return perfil


def analyze_textual(
    backend: Backend, column: str, vtype: VariableType
) -> ColumnProfile:
    """Regime textual (§2.4, consolidada): a string vira o objeto.

    Roda sempre na base inteira — exatidão acima de velocidade.
    """
    perfil = _base(backend, column, vtype)
    texto = backend.text_profile(column)
    n_validos = perfil.quality["n_validos"]

    perfil.essencial = {
        "k": len(backend.contagens(column)) if n_validos < 1 else None,
        "comprimento": texto.get("comprimento", {}),
        "amostras": texto.get("amostras", {}),
        "padrao_dominante": texto.get("padrao_dominante", {}),
    }
    perfil.essencial["k"] = perfil.essencial["k"] or vtype_k(backend, column)
    perfil.essencial["k_sobre_n"] = (
        perfil.essencial["k"] / n_validos if n_validos else 0.0
    )
    perfil.completa = {"mascaras_top": texto.get("mascaras_top", [])}

    for c in backend.text_checks(column):
        perfil.checks.append(
            Check(
                nome=c["nome"],
                descricao=c["descricao"],
                n=c["n"],
                pct=c["pct"],
                amostra=c["amostra"],
            )
        )

    perfil.viz_suggestions = [
        VizSuggestion(
            "histograma",
            {"sobre": "comprimento", **texto.get("comprimento", {})},
            "Distribuição de comprimento — a forma da coluna",
        )
    ]
    return perfil


def vtype_k(backend: Backend, column: str) -> int:
    return len(backend.contagens(column))


def analyze_ordinal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Ordinal (§2.3, consolidada).

    Herda a nominal e acrescenta o que só a ordem permite: acumulada na
    ordem natural e categoria mediana. Média é inválida aqui, mesmo com
    níveis numéricos.
    """
    perfil = analyze_nominal(backend, column, vtype)
    if not vtype.ordered_levels:
        return perfil

    contagens = backend.contagens(column)
    n_validos = perfil.quality["n_validos"]
    ordenados = [n for n in vtype.ordered_levels if str(n) in map(str, contagens)]
    mapa = {str(k): v for k, v in contagens.items()}

    acumulado = 0
    linhas, mediana = [], None
    quartis: dict[str, Any] = {}
    for nivel in ordenados:
        qtd = mapa.get(str(nivel), 0)
        acumulado += qtd
        pct_acumulado = acumulado / n_validos if n_validos else 0.0
        linhas.append({
            "nivel": nivel,
            "absoluto": qtd,
            "pct_validos": qtd / n_validos if n_validos else 0.0,
            "pct_acumulado": pct_acumulado,
        })
        if mediana is None and pct_acumulado >= 0.5:
            mediana = nivel
        for marca, alvo in (("q1", 0.25), ("q3", 0.75)):
            if marca not in quartis and pct_acumulado >= alvo:
                quartis[marca] = nivel

    perfil.essencial["tabela_ordenada"] = linhas
    perfil.essencial["categoria_mediana"] = mediana
    perfil.completa["quartis_categoricos"] = quartis
    perfil.notes.append(
        "Média é inválida em escala ordinal: a distância entre níveis não é comparável"
    )
    perfil.viz_suggestions.insert(
        0,
        VizSuggestion(
            "barras_ordenadas",
            {"niveis": [x["nivel"] for x in linhas],
             "contagens": [x["absoluto"] for x in linhas],
             "acumulado": [x["pct_acumulado"] for x in linhas]},
            "Barras na ordem natural com a curva de acumulada — a ordem é informação",
        ),
    )
    return perfil


def analyze_rank(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Rank (§3.3): posição/colocação.

    O perfil **sempre nomeia a coluna de referência** — é a mitigação do
    falso positivo, para que um engano fique visível na primeira leitura.
    """
    perfil = _base(backend, column, vtype)
    resumo = backend.resumo_numerico(column)
    perfil.essencial = {
        "referencia": vtype.rank_reference,
        "spearman": vtype.rank_spearman,
        "min": resumo.get("min"),
        "max": resumo.get("max"),
        "mediana": resumo.get("mediana"),
        "q1": resumo.get("q1"),
        "q3": resumo.get("q3"),
    }
    perfil.notes.insert(
        0,
        f"Interpretado como colocação de '{vtype.rank_reference}' "
        f"(Spearman {vtype.rank_spearman:+.4f}). Se for uma chave, declare o tipo.",
    )
    return perfil


def analyze_identifier(
    backend: Backend, column: str, vtype: VariableType
) -> ColumnProfile:
    """Identificador (§3.3): chave ou código.

    Chave: unicidade e colisões, fora das estatísticas.
    Código: cardinalidade como nominal — nunca média ou histograma.
    """
    perfil = _base(backend, column, vtype)
    resumo = backend.identifier_summary(column)
    perfil.essencial = {
        "subtipo": vtype.subtype.value if vtype.subtype else None,
        "k": resumo["n_distinct"],
        "unico": resumo["unico"],
        "n_colisoes": resumo["n_colisoes"],
        "linhas_por_valor": resumo["linhas_por_valor"],
    }
    if vtype.subtype is VariableSubtype.CODE:
        contagens = backend.contagens(column, top_n=backend.config.long_tail_top_n)
        n_validos = perfil.quality["n_validos"]
        perfil.essencial["top_valores"] = [
            {"valor": v, "absoluto": q, "pct_validos": q / n_validos if n_validos else 0}
            for v, q in contagens.items()
        ]
    perfil.completa = {"amostra_colisoes": resumo["amostra_colisoes"]}
    perfil.notes.append(
        "Fora das estatísticas numéricas: média de identificador não significa nada"
    )
    return perfil


# --------------------------------------------------------------------------


def _entropia_normalizada(contagens: list[int]) -> float | None:
    total = sum(contagens)
    if total == 0 or len(contagens) < 2:
        return None
    h = -sum((q / total) * math.log(q / total) for q in contagens if q)
    return h / math.log(len(contagens))


def _concentracao(contagens: list[int], n_validos: int) -> dict[str, int]:
    """Quantos níveis acumulam 50%, 80% e 95% dos registros (§2.2)."""
    if not n_validos:
        return {}
    saida, acumulado = {}, 0
    alvos = [0.5, 0.8, 0.95]
    for i, qtd in enumerate(sorted(contagens, reverse=True), start=1):
        acumulado += qtd
        fracao = acumulado / n_validos
        for alvo in list(alvos):
            if fracao >= alvo:
                saida[f"niveis_para_{int(alvo * 100)}pct"] = i
                alvos.remove(alvo)
        if not alvos:
            break
    return saida

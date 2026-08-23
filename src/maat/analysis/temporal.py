"""Análises de variáveis temporais (seção 4 do fluxo de análises).

O temporal se decompõe: mês, dia da semana, hora e trimestre viram ordinais
cíclicas (§2.3); a posição na linha do tempo vira quantitativa. Foi essa
decomposição que resolveu o problema de "data não cabe em quali nem quanti".
"""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.meta import DateFormatEvidence
from maat.core.profile import Check, ColumnProfile, VizSuggestion
from maat.core.taxonomy import VariableType


def analyze_instant(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Instante — seção 4.1 (consolidada).

    Quando o formato é indecidível entre dd/mm e mm/dd, as análises que
    dependem do dia ficam **suspensas** e o impasse é declarado: o pandas
    escolhe em silêncio, nós dizemos que não dá para saber.
    """
    n_total = backend.n_rows()
    resumo = backend.temporal_summary(column)
    n_validos = int(resumo.get("n", 0))

    perfil = ColumnProfile(
        name=column,
        inferred_type=vtype,
        quality={
            "n": n_total,
            "n_validos": n_validos,
            "n_ausentes": int(resumo.get("n_missing", 0)),
            "pct_ausentes": resumo.get("n_missing", 0) / n_total if n_total else 0.0,
            "falha_parse": int(resumo.get("falha_parse", 0)),
        },
        notes=list(vtype.warnings),
    )
    if not n_validos:
        return perfil

    indecidivel = any("indecidível" in a for a in vtype.warnings)

    perfil.essencial = {
        "cobertura": {
            "minimo": resumo.get("minimo"),
            "maximo": resumo.get("maximo"),
            "amplitude_dias": resumo.get("amplitude_dias"),
        },
        "granularidade": resumo.get("granularidade"),
        "no_futuro": resumo.get("no_futuro"),
        "pct_futuro": resumo.get("pct_futuro"),
        "horizonte": resumo.get("horizonte"),
        "extremos": {
            "mais_antigas": resumo.get("mais_antigas"),
            "mais_futuras": resumo.get("mais_futuras"),
        },
        "gaps": resumo.get("gaps"),
    }

    if indecidivel:
        perfil.essencial["perfis_ciclicos"] = None
        perfil.notes.append(
            "Perfis cíclicos por dia suspensos: o formato da data é indecidível. "
            "Declare em Config.date_format para habilitá-los."
        )
    else:
        perfil.essencial["perfis_ciclicos"] = backend.cyclic_profiles(column)
        if hasattr(backend, "counts_by_period"):
            perfil.essencial["contagem_por_mes"] = backend.counts_by_period(column, "M")

    for data, info in (resumo.get("sentinelas") or {}).items():
        perfil.checks.append(
            Check(
                nome="data_sentinela",
                descricao=f"{data}: {info['significado']}",
                n=info["n"],
                pct=info["n"] / n_validos,
                amostra=[data],
            )
        )

    for nome, info in (resumo.get("quebras") or {}).items():
        if isinstance(info, dict) and info.get("n"):
            perfil.checks.append(
                Check(nome=nome, descricao=info["criterio"], n=info["n"],
                      pct=info["n"] / n_validos)
            )

    if resumo.get("no_futuro"):
        perfil.notes.append(
            f"{resumo['no_futuro']} datas no futuro ({resumo['pct_futuro']:.1%}) — "
            "fato reportado, não erro: data de vencimento deve estar no futuro"
        )

    perfil.viz_suggestions = [
        VizSuggestion(
            "linha_tempo",
            perfil.essencial.get("contagem_por_mes") or {},
            "Volume ao longo do tempo",
        )
    ]
    if perfil.essencial.get("perfis_ciclicos"):
        perfil.viz_suggestions.append(
            VizSuggestion(
                "barras_ciclicas",
                perfil.essencial["perfis_ciclicos"],
                "Sazonalidade: mês, dia da semana e hora",
            )
        )
    return perfil


def analyze_duration(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Duração — seção 4.2 (consolidada).

    Quantitativa contínua de fato (4h é o dobro de 2h): herda a §3.2. Muda a
    unidade de exibição, a mediana vira o resumo principal, e as durações
    negativas são reportadas como **fato**, nunca rotuladas erro.
    """
    from maat.analysis.quantitative import analyze_continuous

    perfil = analyze_continuous(backend, column, vtype)
    resumo = backend.resumo_numerico(column)

    mediana = resumo.get("mediana")
    perfil.essencial["unidade_sugerida"] = _unidade(mediana)
    perfil.notes.append(
        "Duração: a mediana é o resumo principal — a distribuição é quase sempre "
        "assimétrica à direita"
    )
    negativos = resumo.get("pct_negativos") or 0.0
    if negativos:
        perfil.checks.append(
            Check(
                nome="duracao_negativa",
                descricao="fim antes do início; pode ser estorno, fuso mal aplicado "
                          "ou erro — o maat reporta, não julga",
                n=int(negativos * (resumo.get("n") or 0)),
                pct=negativos,
            )
        )
    return perfil


def _unidade(segundos: float | None) -> str | None:
    """Unidade de exibição inteligente conforme a magnitude."""
    if segundos is None:
        return None
    escala = abs(segundos)
    if escala < 60:
        return "segundos"
    if escala < 3_600:
        return "minutos"
    if escala < 86_400:
        return "horas"
    return "dias"

"""Renderizadores da saída (seção 6 do fluxo de análises).

O contrato é a estrutura em memória; **todo formato é um renderizador sobre
ela** e nenhum recalcula nada. Custo medido em tokens, com tokenizador real,
sobre um perfil de coluna em regime textual (base = JSON indentado):

    JSON compacto  0,63x   ·  YAML  0,73x  ·  Markdown  0,30x
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from maat.core.profile import Camada, ColumnProfile, DatasetProfile
from maat.core.taxonomy import granularidade_legivel


def _limpa(valor: Any) -> Any:
    """Converte enums e dataclasses aninhados para tipos serializáveis."""
    if isinstance(valor, Enum):
        return valor.value
    if is_dataclass(valor) and not isinstance(valor, type):
        return _limpa(asdict(valor))
    if isinstance(valor, dict):
        return {str(k): _limpa(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_limpa(v) for v in valor]
    return valor


def coluna_para_dict(perfil: ColumnProfile, camada: Camada = "ambas") -> dict[str, Any]:
    vt = perfil.inferred_type
    saida: dict[str, Any] = {
        "coluna": perfil.name,
        "tipo": {
            "classe": vt.var_class.value,
            "subtipo": vt.subtype.value if vt.subtype else None,
            "regime": vt.regime.value if vt.regime else None,
            "confianca": vt.confidence,
        },
        "qualidade": _limpa(perfil.quality),
    }
    if vt.rank_reference:
        saida["tipo"]["rank_reference"] = vt.rank_reference
        saida["tipo"]["rank_spearman"] = vt.rank_spearman
    if vt.ordered_levels:
        saida["tipo"]["ordered_levels"] = vt.ordered_levels

    if camada in ("essencial", "ambas"):
        saida["essencial"] = _limpa(perfil.essencial)
    if camada in ("completa", "ambas"):
        saida["completa"] = _limpa(perfil.completa)

    if perfil.checks:
        saida["checagens"] = [_limpa(c) for c in perfil.checks]
    if perfil.notes:
        saida["observacoes"] = perfil.notes
    if perfil.narrative:
        saida["narrativa"] = perfil.narrative
    if camada != "essencial" and perfil.viz_suggestions:
        saida["visualizacoes"] = [
            {"tipo": v.chart, "motivo": v.reason, "camada": v.camada}
            for v in perfil.viz_suggestions
        ]
    return saida


def dataset_para_dict(perfil: DatasetProfile, camada: Camada = "ambas") -> dict[str, Any]:
    return {
        "maat": {"versao": _versao(), "camada": camada},
        "fonte": perfil.source,
        "n_linhas": perfil.n_rows,
        "n_colunas": len(perfil.columns),
        "colunas": [coluna_para_dict(c, camada) for c in perfil.columns.values()],
    }


def _versao() -> str:
    from maat import __version__

    return __version__


# --------------------------------------------------------------------------
# JSON e YAML
# --------------------------------------------------------------------------


def para_json(perfil: DatasetProfile, camada: Camada = "ambas", compact: bool = True) -> str:
    dados = dataset_para_dict(perfil, camada)
    if compact:
        return json.dumps(dados, ensure_ascii=False, separators=(",", ":"), default=str)
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


def para_yaml(perfil: DatasetProfile, camada: Camada = "ambas") -> str:
    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "to_yaml() exige PyYAML: pip install 'maat[yaml]'"
        ) from e
    dados = json.loads(para_json(perfil, camada, compact=True))
    return yaml.safe_dump(dados, allow_unicode=True, sort_keys=False)


# --------------------------------------------------------------------------
# Markdown — o mais barato em tokens; default na camada essencial
# --------------------------------------------------------------------------


# Tabelas de frequência chegam com dois nomes de chave: as qualitativas falam
# em "nivel", as quantitativas em "valor" — e a diferença é proposital, porque
# um nível de categoria e um valor numérico não são a mesma coisa para quem lê
# o JSON. Os renderizadores liam só "nivel", então a coluna saía vazia em todo
# regime tabela numérico. Aqui decidimos a chave pela linha, não pelo tipo.
_ROTULO = ("NÍVEL", "nivel")


def _cabeca_nivel(linhas: list[dict], rotulo: str = "NÍVEL") -> tuple[str, str]:
    """Escolhe a chave da 1ª coluna conforme o que a análise realmente emitiu."""
    if linhas and "valor" in linhas[0]:
        return ("VALOR" if rotulo == "NÍVEL" else "valor", "valor")
    return (rotulo, "nivel")


def _fmt(valor: Any) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, float):
        # 4 dígitos significativos com piso de 2 casas decimais. O `%.4g` puro
        # arredondava 118,75 para 118,8 — apagando a distinção que a tabela de
        # extremos existe para mostrar — e escrevia um máximo de 10.000 como
        # "1e+04", notação que ninguém lê num relatório descritivo.
        if valor.is_integer() and abs(valor) < 1e15:
            return _fmt(int(valor))
        magnitude = math.floor(math.log10(abs(valor))) if valor else 0
        casas = max(2, 3 - magnitude)
        texto = f"{valor:,.{casas}f}"
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return texto.replace(",", "·").replace(".", ",").replace("·", ".")
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def _tabela_md(linhas: list[dict], colunas: list[tuple[str, str]]) -> list[str]:
    saida = ["| " + " | ".join(t for t, _ in colunas) + " |",
             "|" + "|".join("---" for _ in colunas) + "|"]
    for linha in linhas:
        saida.append("| " + " | ".join(_fmt(linha.get(k)) for _, k in colunas) + " |")
    return saida


def para_markdown(perfil: DatasetProfile, camada: Camada = "essencial") -> str:
    partes = [f"# Perfil de dados — {perfil.source or 'DataFrame'}",
              "",
              f"{_fmt(perfil.n_rows)} linhas · {len(perfil.columns)} colunas · "
              f"gerado pelo maat {_versao()}",
              ""]

    partes.append("| coluna | tipo | k | ausentes |")
    partes.append("|---|---|---|---|")
    for c in perfil.columns.values():
        vt = c.inferred_type
        tipo = vt.var_class.value + (f"/{vt.subtype.value}" if vt.subtype else "")
        if vt.regime:
            tipo += f"[{vt.regime.value}]"
        k = c.essencial.get("k")
        partes.append(
            f"| {c.name} | {tipo} | {_fmt(k)} | "
            f"{_fmt(c.quality.get('n_ausentes'))} |"
        )
    partes.append("")

    for c in perfil.columns.values():
        partes.extend(_coluna_markdown(c, camada))
    return "\n".join(partes)


def _coluna_markdown(c: ColumnProfile, camada: Camada) -> list[str]:
    vt = c.inferred_type
    tipo = vt.var_class.value + (f"/{vt.subtype.value}" if vt.subtype else "")
    if vt.regime:
        tipo += f"[{vt.regime.value}]"

    p = [f"## {c.name}", "", f"**{tipo}**"]
    if vt.rank_reference:
        p[-1] += f" — colocação de `{vt.rank_reference}` (Spearman {vt.rank_spearman:+.4f})"
    q = c.quality
    p[-1] += (f" · n = {_fmt(q.get('n_validos'))} · ausentes "
              f"{_fmt(q.get('n_ausentes'))} ({_fmt(q.get('pct_ausentes'))})")
    p.append("")

    if c.narrative:
        p.extend([c.narrative, ""])

    e = c.essencial
    if e.get("tabela"):
        p.extend(_tabela_md(e["tabela"][:15],
                            [_cabeca_nivel(e["tabela"], "nível"), ("absoluto", "absoluto"),
                             ("% válidos", "pct_validos")]))
        p.append("")
    if e.get("tabela_ordenada"):
        p.extend(_tabela_md(e["tabela_ordenada"],
                            [_cabeca_nivel(e["tabela_ordenada"], "nível"), ("absoluto", "absoluto"),
                             ("% válidos", "pct_validos"),
                             ("% acumulado", "pct_acumulado")]))
        p.append("")
    for chave, rotulo in (("min", "mín"), ("q1", "q1"), ("mediana", "mediana"),
                          ("media", "média"), ("q3", "q3"), ("max", "máx")):
        if chave in e:
            p.append(f"- **{rotulo}**: {_fmt(e[chave])}")
    if e.get("cobertura"):
        cob = e["cobertura"]
        p.append(f"- **cobertura**: {cob.get('minimo', '')[:10]} a "
                 f"{cob.get('maximo', '')[:10]} ({_fmt(cob.get('amplitude_dias'))} dias)")
        p.append("- **granularidade**: "
                 + granularidade_legivel(e.get("granularidade")))
    for chave, campo in (("extremos_valor", "ocorrencias"),
                         ("extremos_frequencia", "absoluto")):
        bloco = e.get(chave)
        if not bloco:
            continue
        for lado in ("maiores", "mais_frequentes", "menores", "menos_frequentes"):
            if bloco.get(lado):
                p.append(f"- **{lado.replace('_', ' ')}**: " + " · ".join(
                    f"{_fmt(x.get('valor'))} (×{_fmt(x.get(campo))})"
                    for x in bloco[lado]))
    if e.get("horizonte") and any(e["horizonte"].values()):
        p.append("- **horizonte**: " + " · ".join(
            f"{faixa} = {_fmt(qtd)}" for faixa, qtd in e["horizonte"].items() if qtd))
    if e.get("gaps"):
        g = e["gaps"][0]
        p.append(f"- **maior intervalo sem registro**: {str(g.get('de', ''))[:10]} a "
                 f"{str(g.get('ate', ''))[:10]} ({_fmt(g.get('dias'))} dias)")
    if e.get("concentracao"):
        for k, v in e["concentracao"].items():
            p.append(f"- **{k.replace('_', ' ')}**: {_fmt(v)}")
    if e.get("comprimento"):
        comp = e["comprimento"]
        p.append(f"- **comprimento**: mín {_fmt(comp.get('min'))} · mediana "
                 f"{_fmt(comp.get('mediana'))} · máx {_fmt(comp.get('max'))}")
    if any(k in e for k in ("min", "cobertura", "concentracao", "comprimento",
                            "horizonte", "gaps", "extremos_valor",
                            "extremos_frequencia")):
        p.append("")

    if c.checks:
        p.append("**Checagens que dispararam**")
        p.append("")
        p.extend(_tabela_md(
            [{"nome": ck.nome, "n": ck.n, "pct": ck.pct, "descricao": ck.descricao}
             for ck in c.checks],
            [("checagem", "nome"), ("n", "n"), ("%", "pct"), ("critério", "descricao")]))
        p.append("")

    if camada in ("completa", "ambas") and c.completa:
        itens = [f"{k}: {_fmt(v)}" for k, v in c.completa.items()
                 if not isinstance(v, (dict, list))]
        if itens:
            p.extend(["**Camada completa** — " + " · ".join(itens), ""])

    if c.notes:
        p.extend([f"> {n}" for n in c.notes])
        p.append("")
    return p


# --------------------------------------------------------------------------
# HTML — a ponta humana, com a identidade visual do projeto
# --------------------------------------------------------------------------

_CSS = """
:root{--void:#05070F;--navy:#0A0E1A;--panel:#101828;--cyan:#00E5FF;--ice:#E6F7FF;
--magenta:#FF2E88;--violet:#9D4EDD;--steel:#3A4A63;--mist:#8FA3BF;--amber:#FFB03A;--mint:#3DF5C6}
*{box-sizing:border-box;margin:0}
body{background:radial-gradient(ellipse at 30% -10%,#0D1526 0%,var(--void) 60%);
color:var(--ice);font-family:'Space Grotesk',system-ui,sans-serif;padding:28px 24px 60px;line-height:1.6}
main{max-width:920px;margin:0 auto}
h1{font-family:'Rajdhani',system-ui,sans-serif;font-weight:700;font-size:32px;color:var(--cyan);
text-shadow:0 0 18px rgba(0,229,255,.4)}
h2{font-family:'Rajdhani',system-ui,sans-serif;font-weight:600;font-size:22px;color:var(--cyan);
margin:34px 0 10px;border-bottom:1px solid var(--steel);padding-bottom:6px}
.sub{color:var(--mist);font-size:13px;font-family:ui-monospace,monospace;margin-top:4px}
.chip{display:inline-block;font-family:ui-monospace,monospace;font-size:11px;padding:2px 9px;
border-radius:999px;border:1px solid var(--steel);color:var(--mist);margin-right:6px}
.chip.tipo{color:var(--cyan);border-color:var(--cyan)}
.card{background:var(--panel);border:1px solid var(--steel);border-radius:12px;padding:16px 18px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0}
th{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:1px;color:var(--mist);
text-align:left;padding:7px 9px;border-bottom:1px solid var(--steel)}
td{padding:6px 9px;border-bottom:1px solid rgba(58,74,99,.35)}
td.num{font-family:ui-monospace,monospace;text-align:right}
.narrativa{border-left:2px solid var(--violet);padding:10px 15px;background:rgba(157,78,221,.07);
border-radius:0 8px 8px 0;margin:10px 0}
.nota{color:var(--mist);font-size:13px;padding-left:14px;position:relative;margin:4px 0}
.nota::before{content:"▸";color:var(--magenta);position:absolute;left:0}
.check{border-color:rgba(255,176,58,.5)}
.check h3{color:var(--amber);font-family:'Rajdhani',system-ui,sans-serif;font-size:16px;margin-bottom:6px}
.metricas{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.metrica{border:1px solid var(--steel);border-radius:8px;padding:7px 13px;text-align:center;min-width:88px}
.metrica b{display:block;font-family:'Rajdhani',system-ui,sans-serif;font-size:19px;font-weight:700;color:var(--cyan)}
.metrica span{font-family:ui-monospace,monospace;font-size:10px;letter-spacing:1px;color:var(--mist)}
footer{margin-top:44px;font-family:ui-monospace,monospace;font-size:12px;color:var(--mist)}
"""


def _esc(valor: Any) -> str:
    from html import escape

    return escape(str(valor))


def _esc_negrito(texto: str) -> str:
    """Escapa e converte o `**negrito**` dos templates em `<strong>`.

    As narrativas sao escritas uma vez, em markdown, e servem aos quatro
    renderizadores — aqui traduzimos a enfase para HTML.
    """
    import re

    padrao = re.compile(r"\*\*([^*]+)\*\*")
    return padrao.sub(r"<strong>\g<1></strong>", _esc(texto))


def para_html(perfil: DatasetProfile, camada: Camada = "ambas") -> str:
    corpo = [
        f"<h1>Perfil de dados — {_esc(perfil.source or 'DataFrame')}</h1>",
        f'<div class="sub">{_fmt(perfil.n_rows)} linhas · {len(perfil.columns)} '
        f"colunas · maat {_versao()}</div>",
    ]

    corpo.append('<h2>Visão geral</h2><div class="card"><table>')
    corpo.append("<tr><th>COLUNA</th><th>TIPO</th><th>k</th><th>AUSENTES</th></tr>")
    for c in perfil.columns.values():
        vt = c.inferred_type
        tipo = vt.var_class.value + (f"/{vt.subtype.value}" if vt.subtype else "")
        if vt.regime:
            tipo += f"[{vt.regime.value}]"
        k = c.essencial.get("k")
        corpo.append(
            f'<tr><td><a href="#{_esc(c.name)}" style="color:var(--cyan)">'
            f"{_esc(c.name)}</a></td><td>{_esc(tipo)}</td>"
            f'<td class="num">{_fmt(k)}</td>'
            f'<td class="num">{_fmt(c.quality.get("n_ausentes"))}</td></tr>'
        )
    corpo.append("</table></div>")

    for c in perfil.columns.values():
        corpo.extend(_coluna_html(c, camada))

    return (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>maat — {_esc(perfil.source or 'perfil')}</title>"
        "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
        "family=Rajdhani:wght@600;700&family=Space+Grotesk:wght@400;500&display=swap'>"
        f"<style>{_CSS}</style></head><body><main>"
        + "".join(corpo)
        + "<footer>Gerado pelo maat · a inferência propõe, o usuário dispõe · "
        "github.com/SamNKB/maat</footer></main></body></html>"
    )


def _coluna_html(c: ColumnProfile, camada: Camada) -> list[str]:
    vt = c.inferred_type
    tipo = vt.var_class.value + (f"/{vt.subtype.value}" if vt.subtype else "")
    if vt.regime:
        tipo += f"[{vt.regime.value}]"

    p = [f'<h2 id="{_esc(c.name)}">{_esc(c.name)}</h2>',
         f'<div class="card"><span class="chip tipo">{_esc(tipo)}</span>'
         f'<span class="chip">n = {_fmt(c.quality.get("n_validos"))}</span>'
         f'<span class="chip">ausentes {_fmt(c.quality.get("n_ausentes"))}</span>']
    if vt.rank_reference:
        p.append(f'<span class="chip">colocação de {_esc(vt.rank_reference)} '
                 f"({vt.rank_spearman:+.4f})</span>")

    if c.narrative:
        p.append(f'<div class="narrativa">{_esc_negrito(c.narrative)}</div>')

    e = c.essencial
    metricas = [(k, r) for k, r in (("min", "MÍN"), ("q1", "Q1"), ("mediana", "MEDIANA"),
                                    ("media", "MÉDIA"), ("q3", "Q3"), ("max", "MÁX"))
                if k in e]
    if metricas:
        p.append('<div class="metricas">')
        for chave, rotulo in metricas:
            p.append(f'<div class="metrica"><b>{_fmt(e[chave])}</b>'
                     f"<span>{rotulo}</span></div>")
        p.append("</div>")

    # O HTML só conhecia métricas numéricas e tabela de frequência, então todo
    # o miolo da análise temporal (cobertura, horizonte, gaps) saía do relatório
    # sem deixar rastro — justamente o tipo com a análise mais rica.
    if e.get("cobertura"):
        cob = e["cobertura"]
        p.append('<div class="metricas">'
                 f'<div class="metrica"><b>{_esc(str(cob.get("minimo", ""))[:10])}</b>'
                 "<span>PRIMEIRA</span></div>"
                 f'<div class="metrica"><b>{_esc(str(cob.get("maximo", ""))[:10])}</b>'
                 "<span>ÚLTIMA</span></div>"
                 f'<div class="metrica"><b>{_fmt(cob.get("amplitude_dias"))}</b>'
                 "<span>DIAS</span></div>"
                 f'<div class="metrica"><b>{_esc(granularidade_legivel(e.get("granularidade")))}</b>'
                 "<span>GRANULARIDADE</span></div></div>")

    if e.get("comprimento"):
        comp = e["comprimento"]
        p.append('<div class="metricas">' + "".join(
            f'<div class="metrica"><b>{_fmt(comp.get(k))}</b><span>{r}</span></div>'
            for k, r in (("min", "MÍN CARACT."), ("mediana", "MEDIANA"), ("max", "MÁX"))
            if k in comp) + "</div>")

    if e.get("horizonte") and any(e["horizonte"].values()):
        p.append('<table><tr><th>HORIZONTE</th><th>REGISTROS</th></tr>')
        for faixa, qtd in e["horizonte"].items():
            if qtd:
                p.append(f"<tr><td>{_esc(faixa)}</td>"
                         f'<td class="num">{_fmt(qtd)}</td></tr>')
        p.append("</table>")

    if e.get("gaps"):
        p.append("<table><tr><th>SEM REGISTRO DE</th><th>ATÉ</th>"
                 "<th>DIAS</th></tr>")
        for g in e["gaps"][:5]:
            p.append(f'<tr><td>{_esc(str(g.get("de", ""))[:10])}</td>'
                     f'<td>{_esc(str(g.get("ate", ""))[:10])}</td>'
                     f'<td class="num">{_fmt(g.get("dias"))}</td></tr>')
        p.append("</table>")

    # As tabelas de extremos são o destaque da camada essencial nos regimes
    # numéricos (§3.1 e §3.2) e não eram renderizadas em nenhuma das saídas.
    for chave, titulos in (
        ("extremos_valor", ("MAIORES VALORES", "MENORES VALORES",
                            "ocorrencias", "OCORRÊNCIAS")),
        ("extremos_frequencia", ("MAIS FREQUENTES", "MENOS FREQUENTES",
                                 "absoluto", "REGISTROS")),
    ):
        bloco = e.get(chave)
        if not bloco:
            continue
        campo, rotulo_campo = titulos[2], titulos[3]
        for lado, titulo in (("maiores", titulos[0]), ("mais_frequentes", titulos[0]),
                             ("menores", titulos[1]), ("menos_frequentes", titulos[1])):
            linhas = bloco.get(lado)
            if not linhas:
                continue
            p.append(f"<table><tr><th>{titulo}</th><th>{rotulo_campo}</th></tr>")
            for linha in linhas:
                p.append(f'<tr><td>{_esc(_fmt(linha.get("valor")))}</td>'
                         f'<td class="num">{_fmt(linha.get(campo))}</td></tr>')
            p.append("</table>")

    if e.get("concentracao"):
        p.append('<div class="sub">' + " · ".join(
            f"{k.replace('_', ' ')}: {_fmt(v)}" for k, v in e["concentracao"].items())
            + "</div>")

    for chave, colunas in (
        ("tabela", [_ROTULO, ("ABSOLUTO", "absoluto"), ("% VÁLIDOS", "pct_validos")]),
        ("tabela_ordenada", [_ROTULO, ("ABSOLUTO", "absoluto"),
                             ("% VÁLIDOS", "pct_validos"), ("% ACUMULADO", "pct_acumulado")]),
    ):
        if e.get(chave):
            colunas = [_cabeca_nivel(e[chave]), *colunas[1:]]
            p.append("<table><tr>" + "".join(f"<th>{t}</th>" for t, _ in colunas) + "</tr>")
            for linha in e[chave][:20]:
                p.append("<tr>" + "".join(
                    f'<td class="num">{_fmt(linha.get(k))}</td>' if i else
                    f"<td>{_esc(_fmt(linha.get(k)))}</td>"
                    for i, (_, k) in enumerate(colunas)) + "</tr>")
            p.append("</table>")

    if c.checks:
        p.append('<div class="card check"><h3>Checagens que dispararam</h3><table>')
        p.append("<tr><th>CHECAGEM</th><th>n</th><th>%</th><th>CRITÉRIO</th></tr>")
        for ck in c.checks:
            p.append(f"<tr><td>{_esc(ck.nome)}</td><td class='num'>{_fmt(ck.n)}</td>"
                     f"<td class='num'>{_fmt(ck.pct)}</td>"
                     f"<td>{_esc(ck.descricao)}</td></tr>")
        p.append("</table></div>")

    if camada in ("completa", "ambas") and c.completa:
        itens = [f"{_esc(k)}: {_fmt(v)}" for k, v in c.completa.items()
                 if not isinstance(v, (dict, list))]
        if itens:
            p.append('<div class="sub">completa — ' + " · ".join(itens) + "</div>")

    for nota in c.notes:
        p.append(f'<div class="nota">{_esc(nota)}</div>')
    p.append("</div>")
    return p

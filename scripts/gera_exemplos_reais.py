"""Embute nas subpáginas de tipo a saída REAL do maat para as colunas-exemplo.

Antes as subpáginas descreviam a análise e traziam tabelas escritas à mão;
agora mostram o que a ferramenta produz de fato, rodado na hora sobre o
dataset do benchmark. Cada bloco carrega o comando que o reproduz, então
nada ali é ilustração — é output, e diverge visivelmente se o código mudar.

Uso: python scripts/gera_exemplos_reais.py
"""

from __future__ import annotations

import html
import re
import warnings
from pathlib import Path

import pandas as pd

import maat
from maat.core.taxonomy import VariableClass, VariableSubtype, VariableType
from maat.render import _coluna_html

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent.parent
DS = RAIZ / "datasets"
TIPOS = RAIZ / "docs/tipos"

MARCA_INICIO = "<!-- SAIDA-MAAT-INICIO -->"
MARCA_FIM = "<!-- SAIDA-MAAT-FIM -->"


class Ex:
    """Um bloco de saída real: de onde vem, o que mostra e por quê."""

    def __init__(self, pasta, arquivo, coluna, porque, *, titulo=None,
                 config=None, recorte=None):
        self.pasta, self.arquivo, self.coluna = pasta, arquivo, coluna
        self.porque, self.titulo = porque, titulo
        self.config, self.recorte = config or {}, recorte


CONTINUA_OVERRIDE = VariableType(VariableClass.QUANTITATIVE,
                                 VariableSubtype.CONTINUOUS)

EXEMPLOS: dict[str, list[Ex]] = {
    "binaria": [Ex(
        "telco-churn", "WA_Fn-UseC_-Telco-Customer-Churn.csv", "Churn",
        "O caso mais didático de binária: dois níveis em texto, sem ausentes, e "
        "desequilíbrio suficiente para a razão de balanceamento dizer algo — 2,77 "
        "para 1. Repare que a linha de ausentes aparece mesmo valendo zero: é "
        "proposital, porque a ausência de ausentes também é informação.")],

    "categorico": [Ex(
        "adult-census", "adult.csv", "education",
        "16 níveis cabem inteiros na tabela — é o que define o regime categórico. "
        "E este é o caso da ordinal disfarçada: a ordem entre Preschool e Doctorate "
        "existe para qualquer humano, mas o maat não a inventa. Ele registra a nota "
        "no rodapé e devolve a decisão a quem conhece o dado.")],

    "cauda-longa": [Ex(
        "nyc-airbnb", "AB_NYC_2019.csv", "neighbourhood",
        "221 bairros: níveis demais para listar, repetição de sobra para a "
        "frequência ainda importar — a definição do regime. O que a tabela "
        "completa não diria e a linha de concentração diz: 11 bairros concentram "
        "metade dos anúncios, e 36 concentram 80%.")],

    "ordinal": [Ex(
        "wine-quality", "winequality-red.csv", "quality",
        "Inteiro de 3 a 8 que é escala Likert, não contagem. Só chega aqui porque "
        "a ordem foi declarada — e são a segunda tabela (em ordem, com acumulada) "
        "e a categoria mediana que a ordem habilita. A nota final é o contrapeso: "
        "média continua inválida em escala ordinal.",
        config={"ordinal_levels": {"quality": [3, 4, 5, 6, 7, 8]}})],

    "textual": [Ex(
        "nyc-airbnb", "AB_NYC_2019.csv", "name",
        "98% dos valores são únicos, então contar frequência não diria nada e a "
        "string vira o objeto da análise. As sete checagens abaixo dispararam "
        "sobre títulos reais de anúncios — inclusive 3 casos de alfabeto misto e "
        "1 placeholder, achados que nenhuma contagem de nível encontraria.")],

    "discreta": [Ex(
        "titanic", "Titanic-Dataset.csv", "SibSp",
        "Contagem de irmãos e cônjuges a bordo: 7 valores distintos, então o regime "
        "é tabela. E é a tabela que revela o buraco — não existe SibSp 6 nem 7, "
        "salta de 5 para 8 — que um histograma teria alisado para dentro de uma "
        "barra qualquer.")],

    "continua": [
        Ex("telco-churn", "WA_Fn-UseC_-Telco-Customer-Churn.csv", "MonthlyCharges",
           "Mensalidade com centavos: as casas decimais medem em vez de contar, e é "
           "isso que separa contínua de discreta. A tabela de extremos entrega os "
           "limites reais do plano — 18,25 e 118,75 — sem pedir que ninguém "
           "interprete um desvio padrão."),
        Ex("nyc-airbnb", "AB_NYC_2019.csv", "price",
           "A diária do NYC é gravada em dólares inteiros, então a inferência a "
           "manda para discreta em regime histograma. Não é erro: é o que o dado "
           "mostra. Quem sabe que aquilo é medição arredondada declara o tipo — e "
           "as duas saídas abaixo, uma sob a outra, são o princípio "
           "<em>a inferência propõe, o usuário dispõe</em> em forma de output.",
           titulo="Antes: o que a infer&ecirc;ncia prop&otilde;e"),
        Ex("nyc-airbnb", "AB_NYC_2019.csv", "price",
           "Com o tipo declarado, a mesma coluna passa a entregar o resumo de cinco "
           "números e a tabela de extremos de valor — onde aparecem os 11 anúncios a "
           "preço 0 e as 3 diárias de 10.000 que a tabela de frequência escondia.",
           titulo="Depois: <code>overrides</code> declara cont&iacute;nua",
           config={"overrides": {"price": CONTINUA_OVERRIDE}}),
    ],

    "temporal": [Ex(
        "netflix", "netflix_titles.csv", "date_added",
        'Data por extenso em texto ("September 25, 2021") com 10 ausentes. O maat '
        "reconhece o formato, mede a granularidade real e mostra o horizonte nos "
        "dois sentidos. Os intervalos sem registro contam a história do catálogo: "
        "456 dias de silêncio entre 2008 e 2009, porque a Netflix quase não "
        "adicionava títulos antes de 2011.")],

    "nao-quantidades": [Ex(
        "videogame-sales", "vgsales.csv", "Rank",
        "Colocação verdadeira. Rank e id sequencial têm assinatura estatística "
        "idêntica, então a classificação vem do vínculo monotônico com outra coluna "
        "— e o perfil <strong>sempre nomeia essa referência</strong> (aqui "
        "Global_Sales, Spearman −0,9996), justamente para um engano ficar visível "
        "na primeira leitura. Sem Global_Sales no recorte não há monotonia a "
        "detectar e a mesma coluna cairia como chave.",
        recorte=["Rank", "Global_Sales"])],
}

# O CSS do renderizador, escopado para não colidir com o da subpágina. Vai
# entre marcas porque ele evolui junto com o gerador: sem elas, a primeira
# geração congelava uma versão antiga do CSS na página para sempre.
CSS_INICIO = "/* SAIDA-MAAT-CSS-INICIO */"
CSS_FIM = "/* SAIDA-MAAT-CSS-FIM */"

CSS_SAIDA = """
.saida-maat{border:1px solid var(--steel); border-radius:12px; margin:14px 0;
  background:rgba(5,7,15,.55); overflow:hidden}
.saida-maat .barra{font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--mist);
  background:rgba(0,229,255,.06); border-bottom:1px solid var(--steel); padding:7px 14px;
  display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap}
.saida-maat .barra b{color:var(--mint); font-weight:400}
.saida-maat .corpo{padding:14px 16px}
.saida-maat h2{font-family:'Rajdhani',sans-serif; font-size:19px; color:var(--cyan);
  margin:0 0 8px; border:0; padding:0}
.saida-maat .card{background:transparent; border:0; padding:0; margin:0}
.saida-maat .chip{display:inline-block; font-family:'JetBrains Mono',monospace; font-size:10.5px;
  padding:2px 9px; border-radius:999px; border:1px solid var(--steel); color:var(--mist); margin:0 5px 8px 0}
.saida-maat .chip.tipo{color:var(--cyan); border-color:var(--cyan)}
.saida-maat .narrativa{border-left:2px solid var(--violet); padding:9px 14px; margin:10px 0;
  background:rgba(157,78,221,.07); border-radius:0 8px 8px 0; font-size:13.5px}
.saida-maat .metricas{display:flex; flex-wrap:wrap; gap:7px; margin:10px 0}
.saida-maat .metrica{border:1px solid var(--steel); border-radius:8px; padding:6px 12px; text-align:center}
.saida-maat .metrica b{display:block; font-family:'Rajdhani',sans-serif; font-size:17px;
  font-weight:700; color:var(--cyan)}
.saida-maat .metrica span{font-family:'JetBrains Mono',monospace; font-size:9.5px;
  letter-spacing:1px; color:var(--mist)}
.saida-maat table{width:100%; border-collapse:collapse; font-size:13px; margin:8px 0}
.saida-maat th{font-family:'JetBrains Mono',monospace; font-size:10px; letter-spacing:1px;
  color:var(--mist); text-align:left; padding:6px 8px; border-bottom:1px solid var(--steel)}
.saida-maat td{padding:5px 8px; border-bottom:1px solid rgba(58,74,99,.3)}
.saida-maat td.num{font-family:'JetBrains Mono',monospace; text-align:right}
.saida-maat .check{border:1px solid rgba(255,176,58,.45); border-radius:10px; padding:10px 14px; margin:10px 0}
.saida-maat .check h3{color:var(--amber); font-family:'Rajdhani',sans-serif; font-size:15px; margin-bottom:5px}
.saida-maat .nota{color:var(--mist); font-size:12.5px; padding-left:14px; position:relative; margin:5px 0}
.saida-maat .nota::before{content:"\\25B8"; color:var(--magenta); position:absolute; left:0}
.saida-maat .sub{font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--mist); margin-top:8px}
.repro{background:var(--navy); border:1px solid var(--steel); border-radius:8px; padding:11px 14px;
  overflow-x:auto; font-family:'JetBrains Mono',monospace; font-size:12.5px; color:var(--mint); margin:0 0 6px}
"""


def ler(pasta: str, arquivo: str) -> pd.DataFrame:
    caminho = DS / pasta / arquivo
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(caminho, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise OSError(f"não consegui ler {caminho}")


def texto_config(config: dict) -> str:
    """Reproduz a Config de forma copiável, sem despejar o objeto inteiro."""
    if not config:
        return ""
    if "ordinal_levels" in config:
        return f", maat.Config(ordinal_levels={config['ordinal_levels']!r})"
    if "overrides" in config:
        coluna = next(iter(config["overrides"]))
        return (f', maat.Config(overrides={{"{coluna}": VariableType(\n'
                "        VariableClass.QUANTITATIVE, VariableSubtype.CONTINUOUS)})")
    return f", maat.Config({', '.join(f'{k}=...' for k in config)})"


def bloco(ex: Ex) -> str:
    df = ler(ex.pasta, ex.arquivo)
    colunas = ex.recorte or [ex.coluna]
    perfil = maat.describe(df[colunas], maat.Config(**ex.config))
    fragmento = "".join(_coluna_html(perfil[ex.coluna], "ambas"))

    # Quem for copiar o exemplo do override precisa dos três nomes importados.
    preambulo = ("from maat.core.taxonomy import (VariableClass, VariableSubtype,\n"
                 "                                VariableType)\n"
                 if "overrides" in ex.config else "")
    comando = html.escape(
        preambulo
        + f'df = pd.read_csv("{ex.pasta}/{ex.arquivo}")\n'
        f"maat.describe(df[{colunas!r}]{texto_config(ex.config)})"
        f'["{ex.coluna}"]'
    )
    titulo = ex.titulo or "A sa&iacute;da real do maat"
    return f"""<h2>{titulo} <span class="tag">RODADO NO BENCHMARK</span></h2>
<p class="muted">{ex.porque}</p>
<div class="saida-maat">
  <div class="barra"><span>fonte: <b>{ex.pasta}/{ex.arquivo}</b> &middot; coluna
    <b>{ex.coluna}</b></span><span>gerado por
    <b>scripts/gera_exemplos_reais.py</b></span></div>
  <div class="corpo">{fragmento}</div>
</div>
<pre class="repro">{comando}</pre>
"""


def main() -> int:
    for pagina, exemplos in EXEMPLOS.items():
        destino = TIPOS / f"{pagina}.html"
        if not destino.exists():
            print(f"  !! página ausente: {pagina}.html")
            continue
        texto = destino.read_text(encoding="utf-8")
        novo = MARCA_INICIO + "\n" + "".join(bloco(e) for e in exemplos) + MARCA_FIM + "\n"

        if MARCA_INICIO in texto:  # substitui o bloco da rodada anterior
            i = texto.index(MARCA_INICIO)
            f = texto.index(MARCA_FIM) + len(MARCA_FIM) + 1
            texto = texto[:i] + novo + texto[f:]
        else:  # entra antes da galeria de exemplos, que fecha toda página
            achados = [m.start() for m in re.finditer(r"<h2[^>]*>[^<]*benchmark", texto)]
            corte = achados[-1] if achados else texto.index("<footer>")
            texto = texto[:corte] + novo + "\n" + texto[corte:]

        css = CSS_INICIO + CSS_SAIDA + CSS_FIM + "\n"
        if CSS_INICIO in texto:  # troca o CSS da rodada anterior
            i, f = texto.index(CSS_INICIO), texto.index(CSS_FIM) + len(CSS_FIM) + 1
            texto = texto[:i] + css + texto[f:]
        else:
            # Gerações anteriores deixaram CSS sem marcas, em versões diferentes
            # conforme a rodada. `.saida-maat` e `.repro` são seletores só nossos,
            # então dá para varrer por seletor em vez de adivinhar o bloco.
            texto = re.sub(r"^\.(saida-maat|repro)\b[^{]*\{[^}]*\}\n?", "", texto,
                           flags=re.M)
            texto = texto.replace("</style>", css + "</style>", 1)

        destino.write_text(texto, encoding="utf-8")
        cols = ", ".join(e.coluna for e in exemplos)
        print(f"  {pagina}.html <- {cols}")
    print("\npronto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

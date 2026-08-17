"""Compara a classificação do ydata-profiling com a taxonomia do maat.

IMPORTANTE: este script **não implementa** a inferência do maat — ele apenas
aplica mecanicamente as regras já documentadas em docs/fluxo-de-analises.md
(§1 e §2.0) sobre os mesmos dados, para revelar onde as duas taxonomias
divergem. Serve de evidência para a comparação competitiva e para calibrar
os limiares com dados reais.

Uso: python scripts/comparar_com_ydata.py
Saída: benchmarks/ydata/_divergencias.csv e um resumo no terminal.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "benchmarks" / "ydata"

# Limiares documentados na §1.2 (defaults da maat.Config)
MAX_CATEGORICAL_LEVELS = 30
MAX_DISCRETE_LEVELS = 30
TEXTUAL_UNIQUE_RATIO = 0.5


def classificar_maat(serie: pd.Series, n_validos: int, k: int) -> str:
    """Aplica as regras documentadas do maat. Não decide nada novo."""
    if n_validos == 0:
        return "vazia"
    ratio = k / n_validos

    if pd.api.types.is_bool_dtype(serie):
        return "binaria"
    if pd.api.types.is_datetime64_any_dtype(serie):
        return "temporal-instante"
    if pd.api.types.is_timedelta64_dtype(serie):
        return "temporal-duracao"

    if pd.api.types.is_numeric_dtype(serie):
        if k == 2:
            return "binaria"
        if k == n_validos and n_validos > 50:
            return "identificador"
        limpa = serie.dropna()
        inteiros = (limpa % 1 == 0).all() if len(limpa) else False
        if inteiros:
            regime = "tabela" if k <= MAX_DISCRETE_LEVELS else "histograma"
            return f"discreta[{regime}]"
        return "continua"

    # string / object
    if k == 2:
        return "binaria"
    if ratio > TEXTUAL_UNIQUE_RATIO:
        return "nominal[textual]"
    if k <= MAX_CATEGORICAL_LEVELS:
        return "nominal[categorico]"
    return "nominal[cauda-longa]"


def main() -> int:
    execucoes = list(csv.DictReader((OUT / "_execucao.csv").open(encoding="utf-8")))
    ok = [e for e in execucoes if e.get("status") == "ok"]
    print(f"datasets com perfil: {len(ok)}")

    linhas = []
    for e in ok:
        nome, arquivo = e["dataset"], e["arquivo"]
        caminho = next((RAIZ / "datasets" / nome).rglob(arquivo), None)
        if caminho is None:
            continue
        dados = json.loads((OUT / f"{nome}.json").read_text(encoding="utf-8"))
        tipos_ydata = {c: i.get("type") for c, i in dados.get("variables", {}).items()}

        df = None
        for encoding in ("utf-8", "latin-1"):
            for sep in (",", ";"):
                try:
                    tmp = pd.read_csv(caminho, nrows=100_000, encoding=encoding,
                                      sep=sep, low_memory=False, on_bad_lines="skip")
                    if tmp.shape[1] > 1:
                        df = tmp
                        break
                except Exception:  # noqa: BLE001, S112
                    continue
            if df is not None:
                break
        if df is None:
            continue

        for coluna in df.columns:
            serie = df[coluna]
            n_validos = int(serie.notna().sum())
            k = int(serie.nunique(dropna=True))
            linhas.append({
                "dataset": nome,
                "coluna": str(coluna),
                "tipo_ydata": tipos_ydata.get(str(coluna), "?"),
                "tipo_maat": classificar_maat(serie, n_validos, k),
                "k": k,
                "n_validos": n_validos,
                "k_sobre_n": round(k / n_validos, 4) if n_validos else "",
                "ausentes": int(serie.isna().sum()),
            })

    with (OUT / "_divergencias.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)

    print(f"colunas analisadas: {len(linhas)}\n")
    print("== distribuição dos tipos do ydata")
    for tipo, qtd in Counter(x["tipo_ydata"] for x in linhas).most_common():
        print(f"  {tipo:<14} {qtd}")
    print("\n== distribuição dos tipos do maat (regras documentadas)")
    for tipo, qtd in Counter(x["tipo_maat"] for x in linhas).most_common():
        print(f"  {tipo:<22} {qtd}")

    print("\n== o que o ydata agrupa que o maat separa")
    for alvo in ("Numeric", "Categorical", "Text"):
        sub = Counter(x["tipo_maat"] for x in linhas if x["tipo_ydata"] == alvo)
        if sub:
            print(f"  {alvo} ->", dict(sub.most_common()))

    print(f"\nDetalhe coluna a coluna em {OUT / '_divergencias.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

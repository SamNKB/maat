"""Roda o ydata-profiling sobre o benchmark e guarda os resultados localmente.

Serve de baseline de comparação com o maat: o ydata-profiling é a ferramenta
de mercado mais próxima do que estamos propondo (ver docs/fluxo-de-analises.md
e a seção de concorrência no CLAUDE.md).

Saída em `benchmarks/ydata/` (fora do git):
  <dataset>.html   relatório navegável, para inspeção humana
  <dataset>.json   descrição estruturada, para comparação automática
  _resumo.csv      uma linha por coluna: tipo detectado, distintos, ausentes
  _execucao.csv    uma linha por dataset: linhas, colunas, tempo, status

Uso: python scripts/run_ydata_baseline.py [--only nome1,nome2]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent.parent
DS = RAIZ / "datasets"
OUT = RAIZ / "benchmarks" / "ydata"

# Amostra: o objetivo é comparar comportamento por coluna, não medir escala.
MAX_LINHAS = 100_000
# Acima disso, roda em modo mínimo (sem correlações/interações) para não travar.
LIMITE_MODO_MINIMO = 30_000


def escolher_csv(pasta: Path) -> Path | None:
    """Maior CSV da pasta — heurística simples e previsível."""
    csvs = [p for p in pasta.rglob("*.csv") if p.is_file()]
    if not csvs:
        return None
    # evita os agregados nacionais gigantes quando há recortes menores
    return max(csvs, key=lambda p: p.stat().st_size)


def ler(caminho: Path) -> pd.DataFrame:
    """Lê o CSV tentando encoding e separador comuns no benchmark."""
    ultimo_erro: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        for sep in (",", ";"):
            try:
                df = pd.read_csv(
                    caminho, nrows=MAX_LINHAS, encoding=encoding, sep=sep,
                    low_memory=False, on_bad_lines="skip",
                )
                if df.shape[1] > 1:  # separador errado devolve 1 coluna só
                    return df
            except Exception as e:  # noqa: BLE001 — tentamos a próxima combinação
                ultimo_erro = e
    if ultimo_erro:
        raise ultimo_erro
    raise ValueError("não foi possível separar as colunas")


def perfilar(nome: str, caminho: Path) -> dict:
    from ydata_profiling import ProfileReport

    inicio = time.time()
    df = ler(caminho)
    minimo = len(df) > LIMITE_MODO_MINIMO or df.shape[1] > 40

    # `interactions` desabilitado: a matriz de dispersão é O(colunas²) e trava em
    # bases largas (breast-cancer, 33 colunas numéricas, não terminava). As
    # correlações — que é o que interessa comparar — continuam ativas no modo
    # completo.
    perfil = ProfileReport(
        df, title=f"ydata baseline — {nome}", minimal=minimo, progress_bar=False,
        interactions={"continuous": False, "targets": []},
    )
    perfil.to_file(OUT / f"{nome}.html")
    descricao = json.loads(perfil.to_json())
    (OUT / f"{nome}.json").write_text(json.dumps(descricao, indent=1), encoding="utf-8")

    linhas_resumo = []
    for coluna, info in descricao.get("variables", {}).items():
        linhas_resumo.append({
            "dataset": nome,
            "coluna": coluna,
            "tipo_ydata": info.get("type"),
            "distintos": info.get("n_distinct"),
            "distintos_pct": round(info.get("p_distinct", 0) or 0, 4),
            "ausentes": info.get("n_missing"),
            "memoria_bytes": info.get("memory_size"),
        })

    return {
        "dataset": nome,
        "arquivo": caminho.name,
        "linhas": len(df),
        "colunas": df.shape[1],
        "modo": "minimo" if minimo else "completo",
        "alertas": len(descricao.get("alerts", [])),
        "segundos": round(time.time() - inicio, 1),
        "status": "ok",
        "_resumo": linhas_resumo,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="lista separada por vírgula de pastas a rodar")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    pastas = sorted(p for p in DS.iterdir() if p.is_dir())
    if args.only:
        alvos = {n.strip() for n in args.only.split(",")}
        pastas = [p for p in pastas if p.name in alvos]

    execucoes, resumo = [], []
    for i, pasta in enumerate(pastas, 1):
        nome = pasta.name
        if (OUT / f"{nome}.json").exists():
            print(f"[{i}/{len(pastas)}] {nome}: já existe, pulando", flush=True)
            continue
        caminho = escolher_csv(pasta)
        if caminho is None:
            print(f"[{i}/{len(pastas)}] {nome}: sem CSV, pulando", flush=True)
            execucoes.append({"dataset": nome, "status": "sem csv"})
            continue
        print(f"[{i}/{len(pastas)}] {nome} ({caminho.name})...", flush=True)
        try:
            r = perfilar(nome, caminho)
            resumo.extend(r.pop("_resumo"))
            execucoes.append(r)
            print(f"    ok: {r['linhas']}x{r['colunas']} · {r['modo']} · "
                  f"{r['alertas']} alertas · {r['segundos']}s", flush=True)
        except Exception as e:  # noqa: BLE001 — um dataset ruim não derruba a rodada
            print(f"    FALHOU: {type(e).__name__}: {e}", flush=True)
            execucoes.append({"dataset": nome, "arquivo": caminho.name,
                              "status": f"erro: {type(e).__name__}"})

    if resumo:
        modo = "a" if (OUT / "_resumo.csv").exists() else "w"
        with (OUT / "_resumo.csv").open(modo, newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(resumo[0].keys()))
            if modo == "w":
                w.writeheader()
            w.writerows(resumo)
    if execucoes:
        campos = ["dataset", "arquivo", "linhas", "colunas", "modo", "alertas",
                  "segundos", "status"]
        modo = "a" if (OUT / "_execucao.csv").exists() else "w"
        with (OUT / "_execucao.csv").open(modo, newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            if modo == "w":
                w.writeheader()
            w.writerows(execucoes)

    ok = sum(1 for e in execucoes if e.get("status") == "ok")
    print(f"\nConcluído: {ok} perfis gerados, {len(execucoes) - ok} sem sucesso.")
    print(f"Resultados em {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

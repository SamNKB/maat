"""Mede os sinais da seção 3.3 do fluxo de análises sobre o benchmark.

Produziu a evidência que fechou a decisão de 2026-08-17: densidade, monotonia,
dígito verificador, zeros à esquerda, comprimento fixo e razão de repetição.
Saída: /tmp/sinais_rank.csv (uma linha por coluna inteira analisada).
"""
import warnings, csv
warnings.filterwarnings("ignore")
import pandas as pd
from pathlib import Path

DS = Path("datasets")
ALVOS = [
    ("videogame-sales", "vgsales.csv", None, None),
    ("world-happiness", None, None, None),
    ("titanic", "Titanic-Dataset.csv", None, None),
    ("nyc-airbnb", "AB_NYC_2019.csv", None, None),
    ("gov-cvm-fundos", "inf_diario_fi_202506.csv", ";", None),
    ("gov-camara-cota", "Ano-2025.csv", ";", None),
    ("gov-comex-exp-mun", "exp_2024_municipios.csv", ";", None),
    ("mall-customers", None, None, None),
    ("stroke", None, None, None),
]

def ler(pasta, arquivo, sep):
    p = DS / pasta
    caminho = (p / arquivo) if arquivo else max(p.rglob("*.csv"), key=lambda x: x.stat().st_size)
    for enc in ("utf-8", "latin-1"):
        for s in ([sep] if sep else [",", ";"]):
            try:
                df = pd.read_csv(caminho, nrows=60000, encoding=enc, sep=s, low_memory=False)
                if df.shape[1] > 1:
                    return df, caminho.name
            except Exception:
                continue
    return None, None

linhas = []
for pasta, arquivo, sep, _ in ALVOS:
    df, nome_arq = ler(pasta, arquivo, sep)
    if df is None:
        print(f"!! {pasta}: nao leu"); continue
    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 20: continue
        # so numericas inteiras (inclusive as que vieram como string de digitos)
        num = pd.to_numeric(s, errors="coerce")
        if num.notna().mean() < 0.99: continue
        num = num.dropna()
        if not (num % 1 == 0).all(): continue
        n, k = len(num), num.nunique()
        mn, mx = int(num.min()), int(num.max())
        amplitude = mx - mn + 1
        denso = round(k / amplitude, 4) if amplitude > 0 else 0
        # zeros a esquerda preservados no texto original?
        txt = s.astype(str)
        zeros_esq = bool((txt.str.match(r"^0\d")).any())
        comp = txt.str.len()
        linhas.append({
            "dataset": pasta, "coluna": str(col), "n": n, "k": k,
            "k_sobre_n": round(k / n, 4), "min": mn, "max": mx,
            "densidade": denso, "comeca_em_1": mn == 1,
            "comprimento_fixo": bool(comp.nunique() == 1),
            "zeros_esquerda": zeros_esq,
            "amostra": " | ".join(txt.head(3).tolist()),
        })

with open("/tmp/sinais_rank.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0].keys())); w.writeheader(); w.writerows(linhas)
print(f"colunas inteiras analisadas: {len(linhas)}")

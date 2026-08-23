"""Mede os sinais candidatos do tipo temporal (§4) sobre o benchmark.

Testa em dados reais as ideias levantadas na discussão de 2026-08-17:
cobertura, falha de parse, formatos misturados, datas-placeholder, datas
impossíveis, datas no futuro e a distribuição por horizonte de idade.

Uso: python scripts/sinais_temporais.py
"""

from __future__ import annotations

import re
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
DS = Path(__file__).resolve().parent.parent / "datasets"
HOJE = pd.Timestamp("2026-08-17")

# Datas que quase sempre significam "vazio" em vez de um instante real.
PLACEHOLDERS = {
    "1900-01-01": "zero do Excel / sentinela clássica",
    "1899-12-30": "zero real do Excel",
    "1970-01-01": "epoch Unix — costuma ser 0 convertido",
    "0001-01-01": "mínimo do datetime",
    "9999-12-31": "máximo — usado como 'sem fim'",
    "2999-12-31": "sentinela de 'nunca expira'",
}

# Formatos comuns; a coluna é "mista" se valores diferentes exigem formatos diferentes.
FORMATOS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y",
            "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"]


def perfil(nome: str, serie: pd.Series, ja_temporal: bool = False) -> None:
    bruto = serie.dropna()
    n_original = len(serie)
    n_nulo_origem = int(serie.isna().sum())

    if ja_temporal:
        dt = pd.to_datetime(bruto, errors="coerce")
        falha_parse = 0
    else:
        texto = bruto.astype(str).str.strip()
        dt = pd.to_datetime(texto, errors="coerce", format="mixed", dayfirst=False)
        falha_parse = int(dt.isna().sum())

    validas = dt.dropna()
    if validas.empty:
        print(f"\n== {nome}: nenhuma data válida")
        return

    print(f"\n== {nome}  (n={n_original:,})".replace(",", "."))
    print(f"   cobertura: {validas.min().date()} a {validas.max().date()}"
          f"   ({(validas.max() - validas.min()).days:,} dias)".replace(",", "."))
    print(f"   nulos na origem: {n_nulo_origem} ({n_nulo_origem/n_original:.2%})"
          f" | falharam no parse: {falha_parse} ({falha_parse/max(len(bruto),1):.2%})")

    # granularidade real: tudo à meia-noite = diário disfarçado de timestamp
    if not ja_temporal or True:
        so_meia_noite = bool((validas.dt.time == datetime.min.time()).all())
        print(f"   granularidade: {'diária (todo horário é 00:00)' if so_meia_noite else 'com hora'}")

    # placeholders
    achados = {}
    for p, desc in PLACEHOLDERS.items():
        q = int((validas.dt.strftime("%Y-%m-%d") == p).sum())
        if q:
            achados[p] = (q, desc)
    print(f"   datas-placeholder: {achados if achados else 'nenhuma'}")

    # futuro e horizontes
    futuro = int((validas > HOJE).sum())
    print(f"   no futuro (após {HOJE.date()}): {futuro} ({futuro/len(validas):.2%})")
    idade = (HOJE - validas).dt.days / 365.25
    faixas = {f">{a} anos": int((idade > a).sum()) for a in (10, 20, 30, 40, 50)}
    print(f"   horizonte: {faixas}")

    # formatos coexistindo (só para colunas em texto)
    if not ja_temporal:
        amostra = bruto.astype(str).str.strip().head(5000)
        casam = {}
        for f in FORMATOS:
            ok = int(pd.to_datetime(amostra, format=f, errors="coerce").notna().sum())
            if ok:
                casam[f] = ok
        principal = max(casam.values()) if casam else 0
        misto = len([f for f, q in casam.items() if q >= 0.02 * len(amostra)]) > 1
        print(f"   formatos que casam (amostra 5k): {casam if casam else 'nenhum exato'}")
        print(f"   >> formatos misturados? {'SIM' if misto else 'não'}"
              f" (formato dominante cobre {principal/len(amostra):.1%})")


def main() -> None:
    nfx = pd.read_csv(DS / "netflix" / "netflix_titles.csv")
    perfil("netflix / date_added", nfx["date_added"])

    eco = pd.read_csv(DS / "ecommerce" / "data.csv", encoding="latin-1")
    perfil("ecommerce / InvoiceDate", eco["InvoiceDate"])

    cam = pd.read_csv(DS / "gov-camara-cota" / "Ano-2025.csv", sep=";", low_memory=False)
    perfil("gov-camara-cota / datEmissao", cam["datEmissao"])

    kc = pd.read_csv(DS / "house-sales-kc" / "kc_house_data.csv")
    perfil("house-sales-kc / date", kc["date"])

    bcb = pd.read_csv(DS / "gov-bcb-dolar" / "dolar_diario.csv", sep=";", decimal=",")
    perfil("gov-bcb-dolar / data", bcb["data"])

    tes = pd.read_csv(DS / "gov-tesouro-direto" / "preco_taxa_tesouro_direto.csv",
                      sep=";", decimal=",")
    col = [c for c in tes.columns if "Vencimento" in c][0]
    perfil(f"gov-tesouro-direto / {col}", tes[col])


if __name__ == "__main__":
    main()

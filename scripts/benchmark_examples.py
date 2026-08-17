"""Extrai números reais dos datasets de benchmark para referenciar nos
exemplos da documentação e do fluxo interativo (docs/fluxo-interativo.html).

Uso: ``python scripts/benchmark_examples.py``
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DS = Path(__file__).resolve().parent.parent / "datasets"


def main() -> None:
    # Binária — telco churn
    telco = pd.read_csv(DS / "telco-churn" / "WA_Fn-UseC_-Telco-Customer-Churn.csv")
    print("== telco-churn / Churn (binária)")
    print(telco["Churn"].value_counts(dropna=False).to_dict(), "| n =", len(telco))
    blanks = (telco["TotalCharges"].astype(str).str.strip() == "").sum()
    print("TotalCharges em branco (numérico-em-string):", blanks)

    # Discreta — titanic SibSp
    tit = pd.read_csv(DS / "titanic" / "Titanic-Dataset.csv")
    print("\n== titanic / SibSp (discreta)")
    vc = tit["SibSp"].value_counts().sort_index()
    print(vc.to_dict(), "| n =", len(tit))
    print("zeros: {:.1%} | média {:.2f} | mediana {}".format(
        (tit["SibSp"] == 0).mean(), tit["SibSp"].mean(), tit["SibSp"].median()))
    print("PassengerId (id): k =", tit["PassengerId"].nunique(), "de n =", len(tit))

    # Contínua — telco MonthlyCharges
    print("\n== telco-churn / MonthlyCharges (contínua)")
    mc = telco["MonthlyCharges"]
    print("k = {} | média {:.2f} | mediana {:.2f} | p5 {:.2f} | p95 {:.2f}".format(
        mc.nunique(), mc.mean(), mc.median(), mc.quantile(0.05), mc.quantile(0.95)))

    # Categórico e cauda longa — adult census
    adult = pd.read_csv(DS / "adult-census" / "adult.csv")
    print("\n== adult-census (nominais)")
    print("education: k =", adult["education"].nunique(),
          "| top:", adult["education"].value_counts().head(3).to_dict())
    nc = adult["native.country"] if "native.country" in adult else adult["native-country"]
    print("native.country: k =", nc.nunique(),
          "| dominante: {:.1%}".format(nc.value_counts(normalize=True).iloc[0]))

    # Cauda longa + textual — nyc airbnb
    nyc = pd.read_csv(DS / "nyc-airbnb" / "AB_NYC_2019.csv")
    print("\n== nyc-airbnb")
    print("neighbourhood: k =", nyc["neighbourhood"].nunique(), "| n =", len(nyc))
    conc = nyc["neighbourhood"].value_counts(normalize=True).cumsum()
    print("bairros para acumular 80%:", int((conc <= 0.80).sum()) + 1)
    print("name (textual): k = {} de n = {} (k/n = {:.2f})".format(
        nyc["name"].nunique(), len(nyc), nyc["name"].nunique() / len(nyc)))
    ln = nyc["name"].dropna().str.len()
    print("comprimento do name: mediana {:.0f} | mín {} | máx {}".format(
        ln.median(), int(ln.min()), int(ln.max())))

    # Ordinal disfarçada — wine quality
    wine = pd.read_csv(DS / "wine-quality" / "winequality-red.csv")
    print("\n== wine-quality / quality (ordinal disfarçada de inteiro)")
    print(wine["quality"].value_counts().sort_index().to_dict(), "| n =", len(wine))

    # Temporal — netflix e ecommerce
    nfx = pd.read_csv(DS / "netflix" / "netflix_titles.csv")
    da = pd.to_datetime(nfx["date_added"].str.strip(), errors="coerce", format="mixed")
    print("\n== netflix / date_added (temporal em string)")
    print("parseia: {:.1%} | cobertura: {} a {}".format(
        da.notna().mean(), da.min().date(), da.max().date()))

    eco = pd.read_csv(DS / "ecommerce" / "data.csv", encoding="latin-1")
    idt = pd.to_datetime(eco["InvoiceDate"], errors="coerce", format="mixed")
    print("\n== ecommerce / InvoiceDate (timestamps) e Quantity")
    print("cobertura: {} a {} | negativos em Quantity (devoluções): {:.1%}".format(
        idt.min().date(), idt.max().date(), (eco["Quantity"] < 0).mean()))

    # Suspeita — king county zipcode
    kc = pd.read_csv(DS / "house-sales-kc" / "kc_house_data.csv")
    print("\n== house-sales-kc / zipcode (número com cara de código)")
    print("dtype:", kc["zipcode"].dtype, "| k =", kc["zipcode"].nunique(),
          "| média 'sem sentido': {:.1f}".format(kc["zipcode"].mean()))


if __name__ == "__main__":
    main()

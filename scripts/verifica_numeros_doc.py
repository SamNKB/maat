"""Recomputa os números escritos à mão nas documentações e acusa divergência.

Os blocos gerados por `gera_exemplos_reais.py` não precisam disso — saem do
próprio maat. O risco mora nas tabelas escritas à mão, que envelhecem em
silêncio: esta varredura nasceu depois de encontrarmos três números publicados
errados (`price` 11×1 e 12×1, `espaco_borda` 238, `PassengerId` 0,0695).

Cada entrada declara o valor documentado e como recomputá-lo. Divergência
significa uma de duas coisas — a doc está velha ou o código regrediu — e as
duas exigem olhar humano, então o script relata e devolve status 1.

Uso: python scripts/verifica_numeros_doc.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

import maat
from maat.backends.pandas_backend import PandasBackend
from maat.core.signals import evidencia_formato_data

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent.parent
DS = RAIZ / "datasets"

_cache: dict[tuple, pd.DataFrame] = {}


def csv(caminho: str, **kwargs) -> pd.DataFrame:
    chave = (caminho, tuple(sorted(kwargs.items())))
    if chave not in _cache:
        _cache[chave] = pd.read_csv(DS / caminho, low_memory=False, **kwargs)
    return _cache[chave]


CAMARA = dict(sep=";", encoding="utf-8", on_bad_lines="skip")


def checagens(df: pd.DataFrame, coluna: str, **cfg) -> dict[str, int]:
    perfil = maat.describe(df[[coluna]], maat.Config(**cfg))[coluna]
    return {c.nome: c.n for c in perfil.checks}


def contagem(df: pd.DataFrame, coluna: str, valor) -> int:
    return int((df[coluna] == valor).sum())


def max_spearman(df: pd.DataFrame, coluna: str) -> float:
    numericas = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    achado = PandasBackend(df)._matriz_spearman(df, numericas).get(coluna)
    return round(achado[0], 4) if achado else float("nan")


# (o que a doc afirma, valor publicado, como recomputar)
CLAIMS: list[tuple[str, object, object]] = [
    # --- §2.4 / textual.html: bateria de checagens em roteamento padrão
    ("textual · espaco_borda no nyc/name", 237,
     lambda: checagens(csv("nyc-airbnb/AB_NYC_2019.csv"), "name")["espaco_borda"]),
    ("textual · espaco_duplo no nyc/name", 1435,
     lambda: checagens(csv("nyc-airbnb/AB_NYC_2019.csv"), "name")["espaco_duplo"]),
    ("textual · markdown no nyc/name", 71,
     lambda: checagens(csv("nyc-airbnb/AB_NYC_2019.csv"), "name")["markdown"]),
    ("textual · url no sms/v2", 89,
     lambda: checagens(csv("sms-spam/spam.csv", encoding="latin-1"), "v2")["url"]),
    ("textual · html_residual no sms/v2", 309,
     lambda: checagens(csv("sms-spam/spam.csv", encoding="latin-1"), "v2")["html_residual"]),
    # Câmara só dispara com regime forçado — a doc diz isso, e aqui provamos.
    ("textual · espaco_duplo na Câmara (regime forçado)", 1449,
     lambda: checagens(csv("gov-camara-cota/Ano-2025.csv", **CAMARA), "txtFornecedor",
                       textual_unique_ratio=0.001)["espaco_duplo"]),
    ("textual · html_residual na Câmara (regime forçado)", 312,
     lambda: checagens(csv("gov-camara-cota/Ano-2025.csv", **CAMARA), "txtFornecedor",
                       textual_unique_ratio=0.001)["html_residual"]),

    # --- §3.2 / continua.html: extremos do price
    ("contínua · price == 0", 11,
     lambda: contagem(csv("nyc-airbnb/AB_NYC_2019.csv"), "price", 0)),
    ("contínua · price == 10.000", 3,
     lambda: contagem(csv("nyc-airbnb/AB_NYC_2019.csv"), "price", 10000)),
    ("contínua · price == 11", 3,
     lambda: contagem(csv("nyc-airbnb/AB_NYC_2019.csv"), "price", 11)),
    ("contínua · price == 12", 4,
     lambda: contagem(csv("nyc-airbnb/AB_NYC_2019.csv"), "price", 12)),

    # --- §3.3 / nao-quantidades.html: monotonia e densidade
    ("rank · videogame/Rank × Global_Sales", -0.9996,
     lambda: max_spearman(csv("videogame-sales/vgsales.csv"), "Rank")),
    ("rank · happiness/Happiness.Rank × Score", -1.0,
     lambda: max_spearman(csv("world-happiness/2017.csv"), "Happiness.Rank")),
    ("rank · mall/CustomerID (falso positivo aceito)", 0.9996,
     lambda: max_spearman(csv("mall-customers/Mall_Customers.csv"), "CustomerID")),
    ("chave · titanic/PassengerId (longe do piso 0,99)", -0.0612,
     lambda: max_spearman(csv("titanic/Titanic-Dataset.csv"), "PassengerId")),

    # --- §4 / temporal.html: prova dd/mm × mm/dd
    ("temporal · ecommerce/InvoiceDate provas mm/dd", 308950,
     lambda: evidencia_formato_data(
         csv("ecommerce/data.csv", encoding="latin-1")["InvoiceDate"].dropna().astype(str))[1]),
    ("temporal · bcb/dolar provas dd/mm", 1378,
     lambda: evidencia_formato_data(
         csv("gov-bcb-dolar/dolar_diario.csv", sep=";")["data"].dropna().astype(str))[0]),
    ("temporal · tesouro/Data Vencimento provas dd/mm", 87801,
     lambda: evidencia_formato_data(
         csv("gov-tesouro-direto/preco_taxa_tesouro_direto.csv", sep=";")
         ["Data Vencimento"].dropna().astype(str))[0]),

    # --- §2.1 / categorico.html
    ("categórico · adult/education k", 16,
     lambda: int(csv("adult-census/adult.csv")["education"].nunique())),
    ("categórico · adult/workclass k", 9,
     lambda: int(csv("adult-census/adult.csv")["workclass"].nunique())),

    # --- §2.2 / cauda-longa.html: variantes de grafia reais
    ("cauda longa · UBER DO BRASIL (caixa alta)", 10267,
     lambda: contagem(csv("gov-camara-cota/Ano-2025.csv", **CAMARA), "txtFornecedor",
                      "UBER DO BRASIL TECNOLOGIA LTDA.")),
    ("cauda longa · Uber Do Brasil (caixa mista)", 8,
     lambda: contagem(csv("gov-camara-cota/Ano-2025.csv", **CAMARA), "txtFornecedor",
                      "Uber Do Brasil Tecnologia Ltda.")),
]


def main() -> int:
    divergentes = []
    for descricao, publicado, recomputa in CLAIMS:
        try:
            obtido = recomputa()
        except Exception as erro:  # noqa: BLE001 — queremos o relato, não o traceback
            divergentes.append((descricao, publicado, f"ERRO: {type(erro).__name__}: {erro}"))
            print(f"  ERRO   {descricao}: {type(erro).__name__}: {erro}")
            continue
        if isinstance(publicado, float):
            bate = abs(float(obtido) - publicado) < 5e-5
        else:
            bate = obtido == publicado
        print(f"  {'ok    ' if bate else 'DIVERGE'} {descricao}: "
              f"publicado {publicado} · obtido {obtido}")
        if not bate:
            divergentes.append((descricao, publicado, obtido))

    print(f"\n{len(CLAIMS) - len(divergentes)}/{len(CLAIMS)} conferem")
    if divergentes:
        print("\nDivergências — ou a doc está velha, ou o código regrediu:")
        for descricao, publicado, obtido in divergentes:
            print(f"  - {descricao}: doc diz {publicado}, código diz {obtido}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

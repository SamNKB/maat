"""Baixa 10 datasets famosos de dados abertos do governo brasileiro.

Fontes com download direto verificado (sem autenticação). Idempotente:
pastas já baixadas são puladas. Uso: ``python scripts/download_gov_datasets.py``
"""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

# (pasta, url, nome do arquivo de saída — None para zip extraído)
DATASETS = [
    ("gov-bcb-ipca",
     "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=csv",
     "ipca_mensal.csv"),
    ("gov-bcb-selic",
     "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=csv",
     "selic_meta.csv"),
    ("gov-bcb-dolar",
     "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?dataInicial=01/01/2015&formato=csv",
     "dolar_diario.csv"),
    ("gov-ibge-municipios",
     "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
     "municipios.json"),
    ("gov-tesouro-direto",
     "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv",
     "preco_taxa_tesouro_direto.csv"),
    ("gov-tse-candidatos",
     "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip",
     None),
    ("gov-camara-cota",
     "https://www.camara.leg.br/cotas/Ano-2025.csv.zip",
     None),
    ("gov-cvm-fundos",
     "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_202506.zip",
     None),
    ("gov-transparencia-viagens",
     "https://portaldatransparencia.gov.br/download-de-dados/viagens/2024",
     None),
    ("gov-comex-exp-mun",
     "https://balanca.economia.gov.br/balanca/bd/comexstat-bd/mun/EXP_2024_MUN.csv",
     "exp_2024_municipios.csv"),
]

ROOT = Path(__file__).resolve().parent.parent / "datasets"
UA = {"User-Agent": "maat-benchmark/0.1 (github.com/SamNKB/maat)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main() -> int:
    ROOT.mkdir(exist_ok=True)
    ok, skipped, failed = [], [], []
    for folder, url, fname in DATASETS:
        dest = ROOT / folder
        if dest.exists() and any(dest.iterdir()):
            skipped.append(folder)
            continue
        print(f"→ {folder}")
        try:
            data = fetch(url)
            dest.mkdir(exist_ok=True)
            if fname is None:
                zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
            else:
                (dest / fname).write_bytes(data)
            ok.append(folder)
        except Exception as e:  # noqa: BLE001 — resume os demais downloads
            print(f"  FALHOU: {e}")
            failed.append(folder)
    print(f"\nBaixados: {len(ok)} | Já existiam: {len(skipped)} | Falharam: {len(failed)}")
    if failed:
        print("Falhas:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

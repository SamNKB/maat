"""Baixa os 30 datasets de benchmark do Kaggle para datasets/ (não versionado).

Pré-requisito (uma vez): ``kaggle auth login``.
Uso: ``python scripts/download_datasets.py``

O script é idempotente: pastas já baixadas são puladas.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# (pasta local, ref no Kaggle) — mesma ordem do manifesto em datasets/README.md
DATASETS = [
    ("titanic", "yasserh/titanic-dataset"),
    ("iris", "uciml/iris"),
    ("wine-quality", "uciml/red-wine-quality-cortez-et-al-2009"),
    ("diabetes", "kumargh/pimaindiansdiabetescsv"),
    ("breast-cancer", "uciml/breast-cancer-wisconsin-data"),
    ("adult-census", "uciml/adult-census-income"),
    ("mushrooms", "uciml/mushroom-classification"),
    ("sms-spam", "uciml/sms-spam-collection-dataset"),
    ("heart-disease", "johnsmith88/heart-disease-dataset"),
    ("california-housing", "camnugent/california-housing-prices"),
    ("house-sales-kc", "harlfoxem/housesalesprediction"),
    ("insurance", "mirichoi0218/insurance"),
    ("telco-churn", "blastchar/telco-customer-churn"),
    ("mall-customers", "vjchoudhary7/customer-segmentation-tutorial-in-python"),
    ("students", "spscientist/students-performance-in-exams"),
    ("wine-reviews", "zynicide/wine-reviews"),
    ("world-happiness", "unsdsn/world-happiness"),
    ("videogame-sales", "gregorut/videogamesales"),
    ("fifa19", "javagarm/fifa-19-complete-player-dataset"),
    ("google-play", "lava18/google-play-store-apps"),
    ("netflix", "shivamb/netflix-shows"),
    ("movies", "rounakbanik/the-movies-dataset"),
    ("youtube-trending", "datasnaek/youtube-new"),
    ("nyc-airbnb", "dgomonov/new-york-city-airbnb-open-data"),
    ("hotel-bookings", "jessemostipak/hotel-booking-demand"),
    ("avocado", "neuromusic/avocado-prices"),
    ("creditcard-fraud", "mlg-ulb/creditcardfraud"),
    ("ecommerce", "carrie1/ecommerce-data"),
    ("suicide-rates", "russellyates88/suicide-rates-overview-1985-to-2016"),
    ("stroke", "fedesoriano/stroke-prediction-dataset"),
]

ROOT = Path(__file__).resolve().parent.parent / "datasets"


def main() -> int:
    ROOT.mkdir(exist_ok=True)
    ok, skipped, failed = [], [], []
    for folder, ref in DATASETS:
        dest = ROOT / folder
        if dest.exists() and any(dest.iterdir()):
            skipped.append(folder)
            continue
        print(f"→ {folder} ({ref})")
        result = subprocess.run(
            [sys.executable, "-m", "kaggle", "datasets", "download",
             "-d", ref, "-p", str(dest), "--unzip"],
        )
        (ok if result.returncode == 0 else failed).append(folder)
    print(f"\nBaixados: {len(ok)} | Já existiam: {len(skipped)} | Falharam: {len(failed)}")
    if failed:
        print("Falhas:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

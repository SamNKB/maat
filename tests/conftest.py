"""Configuração compartilhada dos testes.

Duas camadas, por decisão de projeto:

1. **Testes unitários** sobre fixtures minúsculas versionadas em
   `tests/fixtures/` — sempre rodam, não dependem dos 3,5 GB de datasets.
   As fixtures são fatias reais do benchmark, então preservam a sujeira do
   mundo real (caracteres invisíveis, variantes de grafia, datas ambíguas).

2. **Testes de benchmark** (`@pytest.mark.benchmark`) que rodam sobre os 40
   datasets completos e são **pulados** quando eles não estão em disco.
   Reproduza com `python scripts/download_datasets.py`.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent.parent
DATASETS = RAIZ / "datasets"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "benchmark: roda sobre os 40 datasets completos; pulado se ausentes",
    )
    config.addinivalue_line("markers", "spark: exige PySpark e Java instalados")


@pytest.fixture(scope="session")
def datasets_disponiveis() -> bool:
    return DATASETS.exists() and any(DATASETS.glob("*/*.csv"))


@pytest.fixture
def exige_datasets(datasets_disponiveis):
    if not datasets_disponiveis:
        pytest.skip("datasets do benchmark ausentes: rode scripts/download_datasets.py")


def carregar_fixture(nome: str):
    """Lê uma fixture versionada como DataFrame pandas."""
    import pandas as pd

    caminho = FIXTURES / f"{nome}.csv"
    if not caminho.exists():
        pytest.skip(f"fixture ausente: {nome}")
    return pd.read_csv(caminho, encoding="utf-8")


def carregar_dataset(pasta: str, arquivo: str | None = None, **kwargs):
    """Lê um dataset do benchmark; pula o teste se ele não estiver em disco."""
    import pandas as pd

    p = DATASETS / pasta
    if not p.exists():
        pytest.skip(f"dataset ausente: {pasta}")
    caminho = (p / arquivo) if arquivo else max(
        p.rglob("*.csv"), key=lambda x: x.stat().st_size
    )
    return pd.read_csv(caminho, **kwargs)

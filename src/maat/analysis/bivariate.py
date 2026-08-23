"""Análises bivariadas — a matriz tipo × tipo da seção 5 do fluxo.

FORA DO MVP (decisão de 2026-08-17): a explosão combinatória torna o
relatório ilegível — o fifa19 sozinho tem 3.916 pares, e os 39 datasets
do benchmark somam 9.412. Adiado para o beta.

Direção registrada: modelo híbrido em que a **IA seleciona os pares
pertinentes** (ranqueamento a partir dos nomes e dos perfis univariados)
e o **maat calcula deterministicamente** os pares escolhidos — mesma
divisão de responsabilidades das narrativas (§7), que mantém os números
fora do alcance do modelo. O usuário sempre pode escolher os pares na mão.
"""

from __future__ import annotations

from maat.backends.base import Backend


def analyze_pair(backend: Backend, column_a: str, column_b: str):
    """Despacha para a análise correta conforme os tipos do par:

    - quali × quali   → contingência, qui-quadrado, V de Cramér
    - quali × quanti  → estatísticas por grupo, boxplots por categoria
    - quanti × quanti → correlação (Pearson/Spearman), dispersão amostrada
    - temporal × *    → agregados por período (por categoria ou da métrica)
    """
    raise NotImplementedError

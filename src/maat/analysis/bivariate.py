"""Análises bivariadas — a matriz tipo × tipo da seção 5 do fluxo.

MVP: o usuário escolhe os pares. Futuro: sugestão automática dos pares
mais informativos.
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

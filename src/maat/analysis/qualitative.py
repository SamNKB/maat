"""Análises de variáveis qualitativas (seção 2 do fluxo de análises).

Recebe agregados do backend (value_counts) e produz o ColumnProfile —
nunca toca nos dados brutos.
"""

from __future__ import annotations

from maat.backends.base import Backend
from maat.core.profile import ColumnProfile
from maat.core.taxonomy import VariableType


def analyze_nominal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Nominal — despacha pelo regime de cardinalidade (seção 2 do fluxo).

    CATEGORICAL: frequências completas, moda, força da moda.
    LONG_TAIL (§2.2, consolidada): essencial = top-N (`long_tail_top_n`,
    default 10) + linha "Outros" declarando quantos níveis agrega;
    concentração (níveis para 50%/80%/95%); k, singletons e número de
    grupos de variantes de grafia. Completa = Herfindahl, entropia
    normalizada e a lista dos grupos de variantes.
    TEXTUAL: perfil da string (forma, padrão, sujeira) — ver §2.4.
    """
    raise NotImplementedError


def find_spelling_variant_groups(backend: Backend, column: str) -> dict:
    """Grupos de níveis idênticos sob normalização determinística.

    Critério declarado (§0.2, corolário "mostrar é obrigação, agir é do
    usuário"): minúsculas + remoção de acentos + espaços internos
    colapsados + bordas aparadas. Sem semelhança aproximada nem distância
    de edição — o critério é reproduzível e acompanha o resultado.

    O maat reporta os grupos e suas frequências; nunca une, corrige ou
    sugere correção.
    """
    raise NotImplementedError


def analyze_ordinal(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Tudo da nominal + acumuladas na ordem natural, categoria mediana."""
    raise NotImplementedError


def analyze_binary(backend: Backend, column: str, vtype: VariableType) -> ColumnProfile:
    """Exatamente 2 níveis — seção 2.5 do fluxo (consolidada).

    Essencial: tabela de frequência com o ausente como linha própria
    (absoluto, % do total, % dos válidos).
    Completa: nível dominante e razão de balanceamento.
    Fora por decisão: intervalo de confiança (é inferência, não descrição),
    detecção de par semântico e alertas por limiar.
    """
    raise NotImplementedError

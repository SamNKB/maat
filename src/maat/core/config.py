"""Parâmetros do usuário (seção 1.2 do fluxo de análises).

Os limiares de classificação não são constantes do maat: são parâmetros com
defaults sensatos. A decisão de 2026-08-16 foi explícita — "o usuário pode
especificar quantos níveis quer que a aplicação valide antes de decidir o
que é alto ou baixo".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Check:
    """Checagem de texto registrada pelo usuário (§2.4).

    A bateria embutida é o piso, não o teto.
    """

    nome: str
    regex: str
    descricao: str


@dataclass
class Config:
    """Configuração de uma análise. Todos os campos têm default utilizável."""

    # --- regimes de cardinalidade (§2.0) ---
    max_categorical_levels: int = 30
    """Até aqui, nominal em regime categórico (frequências completas)."""

    textual_unique_ratio: float = 0.5
    """Fração de valores únicos acima da qual a nominal vira regime textual."""

    max_discrete_levels: int = 30
    """Discreta: até k distintos → regime tabela; acima → regime histograma."""

    # --- amostra de inferência (§1.2) ---
    inference_sample_size: int | None = 100_000
    """Linhas amostradas para decidir a ROTA. As contagens finais vêm sempre
    da base inteira. None = usar tudo."""

    # --- tabelas de extremos ---
    discrete_extremes_levels: int = 5
    """Regime histograma: n valores mais e n menos frequentes (§3.1)."""

    discrete_extremes_include_middle: bool = False
    """Opt-in: acrescenta os n valores do meio do ranking. Desligado porque
    o histograma já retrata o corpo da distribuição."""

    continuous_extremes_levels: int = 5
    """Contínua: n maiores e n menores valores observados (§3.2)."""

    long_tail_top_n: int = 10
    """Cauda longa: n níveis na tabela, mais a linha "Outros" (§2.2)."""

    temporal_extremes_levels: int = 5
    """Temporal: n datas mais antigas e mais futuras (§4.1)."""

    # --- ordinal (§2.3) ---
    ordinal_levels: dict[str, list[Any]] = field(default_factory=dict)
    """Ordem declarada por coluna, ex.: {"tamanho": ["P", "M", "G"]}.
    Só caminhos determinísticos: declaração ou número inicial no rótulo."""

    # --- rank e códigos (§3.3) ---
    rank_monotonia_minima: float = 0.99
    """|Spearman| contra outra coluna a partir do qual vira rank. O falso
    positivo é conhecido e mitigado nomeando sempre a coluna de referência."""

    identifier_min_rows: int = 50
    """Abaixo disso, k == n não é evidência suficiente de identificador."""

    # --- regime textual (§2.4) ---
    textual_sample_size: int = 5
    """n de cada amostra dirigida: mais curtas, mais longas, aleatórias."""

    textual_extra_checks: list[Check] = field(default_factory=list)
    """Checagens próprias do usuário, somadas à bateria embutida."""

    textual_mask_top_n: int = 5
    """Quantas máscaras de caractere mostrar na camada completa."""

    # --- temporal (§4) ---
    date_format: dict[str, str] = field(default_factory=dict)
    """Formato declarado por coluna quando indecidível: {"data": "dd/mm"}."""

    date_horizons: list[int] = field(default_factory=lambda: [10, 20, 30, 40, 50, 100])
    """Faixas (anos) do perfil de horizonte temporal."""

    date_parse_min_rate: float = 0.9
    """Taxa mínima de parse para uma string virar temporal."""

    # --- Spark (§0.4) ---
    quantile_error: float = 0.01
    """Erro relativo do approxQuantile. O erro usado é sempre reportado."""

    scatter_sample_size: int = 5_000
    """Amostra para visuais que exigem pontos individuais."""

    # --- narrativa (§7) ---
    language: str = "pt-BR"
    """Idioma do núcleo de templates: pt-BR ou en."""

    narrative_tone: str = "academico"
    """Tom da narrativa. MVP: só acadêmico."""

    narrative_llm: str | None = None
    """LLM local opcional para reformular/traduzir, ex.: "ollama/llama3.2:3b".
    Nunca gera análise e nunca altera números (trava validada)."""

    # --- sobrescritas de tipo ---
    overrides: dict[str, Any] = field(default_factory=dict)
    """Tipos declarados pelo usuário, por coluna. A inferência propõe, o
    usuário dispõe (§0.1)."""

    def __post_init__(self) -> None:
        if not 0 < self.textual_unique_ratio <= 1:
            raise ValueError("textual_unique_ratio deve estar em (0, 1]")
        if not 0 <= self.rank_monotonia_minima <= 1:
            raise ValueError("rank_monotonia_minima deve estar em [0, 1]")
        if self.language not in ("pt-BR", "en"):
            raise ValueError("language deve ser 'pt-BR' ou 'en'")

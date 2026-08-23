"""Metadados por coluna — o insumo barato da inferência.

Cada backend calcula estes campos do jeito mais eficiente no seu motor
(pandas: direto; Spark: agregações distribuídas), e a inferência em si é
código puro e compartilhado (`maat.core.inference`).

Os sinais aqui são exatamente os decididos nas seções 2.0, 3.1, 3.3 e 4.1
do fluxo de análises — todos determinísticos e independentes de idioma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DtypeKind(str, Enum):
    """Tipo físico normalizado pelo backend."""

    BOOL = "bool"
    NUMERIC = "numeric"
    STRING = "string"
    DATETIME = "datetime"
    TIMEDELTA = "timedelta"
    OTHER = "other"


class DateFormatEvidence(str, Enum):
    """Estado da ambiguidade dd/mm × mm/dd (§4.1).

    Em toda coluna A/B/AAAA, 39% a 50% dos valores são individualmente
    ambíguos; a prova vem da minoria com campo > 12.
    """

    DMY = "dmy"  # provado dia/mês
    MDY = "mdy"  # provado mês/dia
    MIXED = "mixed"  # provas dos dois lados — dado corrompido
    UNDECIDABLE = "undecidable"  # nenhum valor desambigua
    NOT_APPLICABLE = "not_applicable"  # não é padrão A/B/AAAA (ISO, textual…)


@dataclass
class ColumnMeta:
    """Metadados de uma coluna, calculados pelo backend sobre a amostra."""

    name: str
    dtype_kind: DtypeKind
    n: int
    n_missing: int
    n_distinct: int

    # --- numéricas ---
    all_integer: bool = False
    minimum: float | None = None
    maximum: float | None = None

    # --- sinais de "não é quantidade" (§3.3) ---
    has_leading_zeros: bool = False
    """Zero à esquerda preservado no texto original: número descarta, código não."""

    fixed_length: bool = False
    """Todos os valores com o mesmo nº de dígitos/caracteres, e pelo menos 5.

    O piso de 5 existe porque ano tem 4 dígitos e é contagem, não código —
    `CO_MUN` tem 7, CEP 8, CNPJ 14.
    """

    check_digit_rate: float = 0.0
    """Fração que passa no dígito verificador de CPF/CNPJ."""

    check_digit_kind: str | None = None
    """Qual algoritmo validou: "cnpj", "cpf" ou None."""

    max_spearman: float | None = None
    """Maior |Spearman| contra as demais colunas numéricas."""

    spearman_reference: str | None = None
    """Coluna que produziu esse Spearman — obrigatória ao classificar rank."""

    # --- strings ---
    parse_date_rate: float = 0.0
    """Fração que parseia como data."""

    date_format_evidence: DateFormatEvidence = DateFormatEvidence.NOT_APPLICABLE
    dmy_proofs: int = 0
    mdy_proofs: int = 0
    ambiguous_dates: int = 0

    # --- ordinal (§2.3) ---
    leading_number_order: list[Any] | None = None
    """Ordem extraída do número inicial dos rótulos ("5-14 years" < "15-24
    years"). Única inferência automática de ordem aceita."""

    sample_values: list[Any] = field(default_factory=list)

    @property
    def n_valid(self) -> int:
        return self.n - self.n_missing

    @property
    def unique_ratio(self) -> float:
        """k / n_válidos — decide o regime textual."""
        return self.n_distinct / self.n_valid if self.n_valid else 0.0

    @property
    def density(self) -> float:
        """k / (máx − mín + 1) — separa identificador esparso de denso (§3.3).

        `nyc/id` = 0,0013 (vai de 2.539 a 36 milhões) contra 1,0 de um rank.
        """
        if self.minimum is None or self.maximum is None:
            return 0.0
        amplitude = self.maximum - self.minimum + 1
        return self.n_distinct / amplitude if amplitude > 0 else 0.0

    @property
    def repetition_ratio(self) -> float:
        """n / k — linhas por valor distinto. `ideCadastro` = 391 → chave
        estrangeira, não primária."""
        return self.n_valid / self.n_distinct if self.n_distinct else 0.0

    @property
    def looks_like_code(self) -> bool:
        """Sinais de código: dígito verificador, zeros à esquerda ou
        comprimento fixo com repetição (§3.3)."""
        if self.check_digit_rate >= 0.9:
            return True
        if self.has_leading_zeros:
            return True
        return self.fixed_length and self.repetition_ratio > 1.5

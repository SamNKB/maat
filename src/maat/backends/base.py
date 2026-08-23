"""Contrato abstrato dos backends.

O princípio de projeto (§0.4): **todo o custo computacional fica no
backend** — agregações, quantis, amostragem, regex. Os módulos de análise e
visualização trabalham apenas com os agregados devolvidos. É isso que
permite que o mesmo código de análise sirva para pandas (local) e Spark
(distribuído).

Nenhum método aqui devolve dados brutos: sempre contagens, resumos ou
amostras já limitadas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from maat.core.config import Config
from maat.core.meta import ColumnMeta


class Backend(ABC):
    """Operações primitivas que cada motor de dados precisa oferecer."""

    def __init__(self, df: Any, config: Config | None = None) -> None:
        self.df = df
        self.config = config or Config()
        self._memo: dict[tuple, Any] = {}

    def contagens(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        """`value_counts` memoizado.

        Uma análise qualitativa consulta as contagens várias vezes (qualidade,
        tabela, concentração, singletons). Sem memoização, cada consulta é
        uma agregação distribuída completa — no Spark isso é uma releitura da
        base inteira por chamada.
        """
        chave = ("vc", column, top_n)
        if chave not in self._memo:
            self._memo[chave] = self.value_counts(column, top_n)
        return self._memo[chave]

    def resumo_numerico(self, column: str) -> dict[str, float]:
        """`numeric_summary` memoizado — idem."""
        chave = ("ns", column)
        if chave not in self._memo:
            self._memo[chave] = self.numeric_summary(column)
        return self._memo[chave]

    # --- inferência -------------------------------------------------------

    @abstractmethod
    def n_rows(self) -> int:
        """Total de linhas da base (não da amostra)."""

    @abstractmethod
    def columns_meta(self) -> dict[str, ColumnMeta]:
        """Metadados baratos por coluna, insumo de `infer_schema`.

        Calculados sobre a amostra de inferência (`inference_sample_size`);
        as contagens finais das análises vêm da base inteira.
        """

    # --- qualitativas -----------------------------------------------------

    @abstractmethod
    def value_counts(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        """Frequência por valor, do mais frequente para o menos."""

    @abstractmethod
    def spelling_variant_groups(self, column: str) -> list[list[tuple[Any, int]]]:
        """Grupos de níveis idênticos sob normalização determinística (§2.2).

        O maat nunca une, corrige ou sugere correção — só relata.
        """

    # --- quantitativas ----------------------------------------------------

    @abstractmethod
    def numeric_summary(self, column: str) -> dict[str, float]:
        """Posição, dispersão e forma.

        Deve incluir `quantile_error`: 0.0 quando exato (pandas), o erro
        usado quando aproximado (Spark).
        """

    @abstractmethod
    def histogram(self, column: str, bins: int) -> dict[str, list[float]]:
        """Contagens por bin, calculadas no motor."""

    @abstractmethod
    def value_extremes(self, column: str, n: int) -> dict[str, list[tuple[Any, int]]]:
        """N maiores e N menores valores observados, com contagem (§3.2)."""

    # --- temporais --------------------------------------------------------

    @abstractmethod
    def temporal_summary(self, column: str) -> dict[str, Any]:
        """Cobertura, granularidade, gaps, horizonte, sentinelas e as
        quebras de calendário/dtype da §4.1."""

    @abstractmethod
    def cyclic_profiles(self, column: str) -> dict[str, dict[Any, int]]:
        """Contagens por componente cíclico: mês, dia da semana, hora."""

    # --- textuais ---------------------------------------------------------

    @abstractmethod
    def text_profile(self, column: str) -> dict[str, Any]:
        """Comprimento, amostras dirigidas (curtas, longas, aleatórias),
        máscaras de caractere e padrão dominante (§2.4)."""

    @abstractmethod
    def text_checks(self, column: str) -> list[dict[str, Any]]:
        """Bateria de checagens: contagem, % e amostra dos ofensores.

        Roda sempre na base inteira — exatidão acima de velocidade, decisão
        de 2026-08-17.
        """

    # --- identificadores --------------------------------------------------

    @abstractmethod
    def identifier_summary(self, column: str) -> dict[str, Any]:
        """Unicidade, colisões e duplicatas (§3.3)."""

    # --- amostragem -------------------------------------------------------

    @abstractmethod
    def sample(self, columns: list[str], n: int) -> list[dict[str, Any]]:
        """Amostra para visuais que exigem pontos individuais."""

"""Contrato de saída das análises (seção 6 do fluxo de análises).

O princípio, decidido em 2026-08-17: **o contrato é a estrutura em memória;
todo formato é um renderizador sobre ela**. Acrescentar um formato novo vira
um método, não uma refatoração — e nenhum renderizador recalcula nada.

Assim a camada de visualização e o relatório nunca dependem de pandas ou
Spark, e os quatro formatos do MVP (JSON, YAML, Markdown, HTML) leem a
mesma fonte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from maat.core.taxonomy import VariableType

Camada = Literal["essencial", "completa", "ambas"]


@dataclass
class VizSuggestion:
    """Sugestão de visualização com os dados já pré-agregados pelo backend.

    Nunca carrega dados brutos: o custo mora no backend (§0.4), e o
    renderizador recebe apenas o que já está agregado.
    """

    chart: str  # ex.: "bar", "histogram", "boxplot", "timeline", "pareto"
    data: dict[str, Any]  # dados agregados, prontos para plotar
    reason: str  # por que este gráfico foi sugerido
    camada: Camada = "essencial"


@dataclass
class Check:
    """Resultado de uma checagem determinística (regime textual §2.4,
    variantes de grafia §2.2, quebras de calendário §4.1).

    O critério é declarado junto do resultado — §0.2, corolário "mostrar é
    obrigação, agir é do usuário". Nunca há veredito de aprovado/reprovado.
    """

    nome: str
    descricao: str  # o critério, em palavras
    n: int
    pct: float
    amostra: list[Any] = field(default_factory=list)  # ofensores, para tornar acionável


@dataclass
class ColumnProfile:
    """Resultado completo da análise de uma coluna.

    As duas camadas (§0.3) são estruturais, não uma opção de exibição:
    `essencial` é o que qualquer pessoa lê; `completa` exige contexto
    estatístico. Os renderizadores filtram por camada.
    """

    name: str
    inferred_type: VariableType
    # n, n_validos, n_ausentes, pct_ausentes — vale para todo tipo
    quality: dict[str, Any] = field(default_factory=dict)
    # Conteúdo varia por tipo/regime: tabela de frequência, cinco números,
    # cobertura temporal, comprimento de string...
    essencial: dict[str, Any] = field(default_factory=dict)
    completa: dict[str, Any] = field(default_factory=dict)
    # Checagens determinísticas que dispararam
    checks: list[Check] = field(default_factory=list)
    viz_suggestions: list[VizSuggestion] = field(default_factory=list)
    # Observações da inferência ("possível ordinal: declare a ordem para
    # habilitar acumulada e categoria mediana")
    notes: list[str] = field(default_factory=list)
    # Prosa gerada por template determinístico (§7); reformulação via LLM
    # local opcional nunca altera números (trava validada).
    narrative: str | None = None

    def to_dict(self, camada: Camada = "ambas") -> dict[str, Any]:
        """Estrutura serializável — a fonte de todos os renderizadores."""
        raise NotImplementedError


@dataclass
class DatasetProfile:
    """Resultado da análise do DataFrame inteiro.

    Os quatro formatos do MVP são métodos dedicados (decisão de 2026-08-17,
    pelo autocomplete). Todos aceitam `camada`: mandar só o essencial para
    um agente de IA economiza tokens — medido em ~3,4x entre Markdown
    essencial e JSON indentado completo.
    """

    n_rows: int
    columns: dict[str, ColumnProfile] = field(default_factory=dict)
    # Nome da fonte, quando conhecido — útil ao comparar perfis
    source: str | None = None

    def __getitem__(self, name: str) -> ColumnProfile:
        return self.columns[name]

    @property
    def schema(self) -> dict[str, VariableType]:
        return {name: col.inferred_type for name, col in self.columns.items()}

    def to_dict(self, camada: Camada = "ambas") -> dict[str, Any]:
        """Estrutura serializável — fonte única dos renderizadores abaixo."""
        raise NotImplementedError

    def to_json(self, path: str | None = None, camada: Camada = "ambas",
                compact: bool = True) -> str:
        """JSON — o formato de máquina. Compacto por padrão: medido em
        0,63x os tokens do JSON indentado e mais barato que YAML."""
        raise NotImplementedError

    def to_yaml(self, path: str | None = None, camada: Camada = "ambas") -> str:
        """YAML — mais legível para edição à mão (0,73x o JSON indentado)."""
        raise NotImplementedError

    def to_markdown(self, path: str | None = None,
                    camada: Camada = "essencial") -> str:
        """Markdown — nativo para humano e para LLM ao mesmo tempo. O mais
        barato em tokens (0,30x); default na camada essencial, que é o caso
        de uso de mandar o perfil para um agente ou colar num trabalho."""
        raise NotImplementedError

    def to_html(self, path: str | None = None, camada: Camada = "ambas") -> str:
        """HTML navegável — a ponta humana, com a identidade visual do
        projeto e as camadas separadas na interface."""
        raise NotImplementedError

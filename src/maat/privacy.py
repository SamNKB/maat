"""Mascaramento de PII/PHI no resultado das análises.

Opt-in via `Config.mask_pii`. Quando ligado, os **trechos de dado bruto** que
o perfil carrega — amostras dirigidas e amostras de ofensores — passam por
detecção e mascaramento antes de sair.

Três decisões de projeto (2026-08-23):

1. **Nunca mascarar em silêncio.** Se a flag está ligada e o Presidio não
   está instalado, levantamos erro com instrução de instalação. Produzir
   saída não mascarada quando o usuário pediu proteção seria vazamento
   silencioso — o pior resultado possível.
2. **Mascaramento parcial**: `123.456.789-01` vira `***.456.789-**`. A
   pontuação é preservada, então o formato continua legível para análise,
   mas o valor não é reconstituível.
3. **Alcance limitado a amostras e ofensores** — os trechos de texto livre,
   que são o risco maior. Níveis de tabela e agregados não são mascarados.

Nota sobre o Presidio: o modelo padrão é **inglês** (`en_core_web_lg`, ~400
MB baixado na primeira instalação) e erra em dado brasileiro — classifica CPF
como telefone e detecta CNPJ pela metade. Por isso registramos
**reconhecedores próprios** de CPF e CNPJ que usam os validadores de dígito
verificador de `core.signals`: falso positivo quase zero, porque o número
precisa passar no algoritmo oficial.
"""

from __future__ import annotations

import re
from typing import Any

from maat.core.signals import valida_cnpj, valida_cpf

MENSAGEM_SEM_PRESIDIO = (
    "mask_pii=True exige o Presidio, que não está instalado.\n"
    "Instale com:  pip install 'maat[pii]'\n"
    "O maat não mascara em silêncio: se você pediu proteção e não podemos "
    "aplicá-la, preferimos falhar a entregar dado exposto."
)

# Frações mascaradas dos caracteres alfanuméricos, preservando a pontuação.
# Em um CPF de 11 dígitos isso mascara os 3 primeiros e os 2 últimos,
# produzindo exatamente `***.456.789-**`.
_FRACAO_INICIO = 0.3
_FRACAO_FIM = 0.2

_ALFANUM = re.compile(r"[0-9A-Za-zÀ-ÿ]")


def mascara_parcial(texto: str, marcador: str = "*") -> str:
    """Mascara o início e o fim, preservando a pontuação e o miolo.

    >>> mascara_parcial("123.456.789-01")
    '***.456.789-**'
    """
    texto = str(texto)
    posicoes = [i for i, ch in enumerate(texto) if _ALFANUM.match(ch)]
    total = len(posicoes)
    if total <= 2:
        return marcador * len(texto)

    n_inicio = max(1, int(total * _FRACAO_INICIO))
    n_fim = max(1, int(total * _FRACAO_FIM))
    if n_inicio + n_fim >= total:  # muito curto: mascara tudo menos um
        n_inicio, n_fim = total - 1, 0

    esconder = set(posicoes[:n_inicio]) | set(posicoes[total - n_fim:] if n_fim else [])
    return "".join(
        marcador if i in esconder else ch for i, ch in enumerate(texto)
    )


# --------------------------------------------------------------------------
# reconhecedores próprios: o dígito verificador vale mais que o padrão do
# Presidio, porque elimina o falso positivo
# --------------------------------------------------------------------------


def _reconhecedores_br():
    from presidio_analyzer import Pattern, PatternRecognizer

    class DocumentoBR(PatternRecognizer):
        """CPF/CNPJ validados pelo dígito verificador, não só pelo formato."""

        def __init__(self, entidade: str, padrao: str, validador):
            super().__init__(
                supported_entity=entidade,
                patterns=[Pattern(name=entidade.lower(), regex=padrao, score=0.5)],
                supported_language="en",
            )
            self._validador = validador

        def validate_result(self, texto_detectado: str):
            # True eleva o score ao máximo; False descarta o achado.
            return self._validador(texto_detectado)

    return [
        DocumentoBR("BR_CPF", r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", valida_cpf),
        DocumentoBR(
            "BR_CNPJ", r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", valida_cnpj
        ),
    ]


_analisador_cache: Any = None


def analisador(language: str = "en"):
    """Motor do Presidio com os reconhecedores brasileiros registrados.

    Levanta `ImportError` com instrução clara se o Presidio faltar — nunca
    devolve None nem degrada em silêncio.
    """
    global _analisador_cache
    if _analisador_cache is not None:
        return _analisador_cache
    try:
        from presidio_analyzer import AnalyzerEngine
    except ImportError as e:
        raise ImportError(MENSAGEM_SEM_PRESIDIO) from e

    motor = AnalyzerEngine()
    for r in _reconhecedores_br():
        motor.registry.add_recognizer(r)
    _analisador_cache = motor
    return motor


# --------------------------------------------------------------------------


# Nomes precisam de regra própria: mascarar 30%/20% deixaria "Ana Souza"
# como "**a Souz*", quase legível. Para pessoa e localização guardamos só a
# inicial de cada palavra — ainda parcial (a forma continua visível), mas
# sem revelar o valor.
_SO_INICIAIS = {"PERSON", "LOCATION", "NRP", "ORGANIZATION"}


def _mascara_iniciais(texto: str, marcador: str = "*") -> str:
    """`Ana Souza` vira `A** S****`."""
    saida, inicio_de_palavra = [], True
    for ch in texto:
        if not _ALFANUM.match(ch):
            saida.append(ch)
            inicio_de_palavra = True
            continue
        saida.append(ch if inicio_de_palavra else marcador)
        inicio_de_palavra = False
    return "".join(saida)


def mascarar_texto(texto: Any, motor, language: str = "en") -> Any:
    """Detecta PII num valor e mascara parcialmente cada trecho encontrado."""
    if not isinstance(texto, str) or not texto.strip():
        return texto
    try:
        achados = motor.analyze(text=texto, language=language)
    except Exception:  # noqa: BLE001 — um valor exótico não derruba o perfil
        return texto
    if not achados:
        return texto

    # O Presidio pode devolver spans sobrepostos para o mesmo trecho (nosso
    # BR_CPF e o PHONE_NUMBER dele, por exemplo). Mascarar os dois corromperia
    # o resultado, então ficamos com o de maior confiança e descartamos quem
    # se sobrepõe a ele.
    escolhidos = []
    for a in sorted(achados, key=lambda x: (-x.score, x.start)):
        if not any(a.start < e.end and e.start < a.end for e in escolhidos):
            escolhidos.append(a)

    # aplica de trás para frente para não deslocar os índices
    saida = texto
    for a in sorted(escolhidos, key=lambda x: x.start, reverse=True):
        trecho = saida[a.start : a.end]
        regra = (
            _mascara_iniciais if a.entity_type in _SO_INICIAIS else mascara_parcial
        )
        saida = saida[: a.start] + regra(trecho) + saida[a.end :]
    return saida


def mascarar_perfil(perfil, config) -> None:
    """Mascara amostras e ofensores de um `DatasetProfile`, no lugar.

    Aplicado logo após a análise: o objeto em memória já sai protegido.
    """
    motor = analisador(config.pii_language)
    idioma = config.pii_language

    def mascarar(valor):
        if isinstance(valor, list):
            return [mascarar(v) for v in valor]
        if isinstance(valor, dict):
            return {k: mascarar(v) for k, v in valor.items()}
        return mascarar_texto(valor, motor, idioma)

    for coluna in perfil.columns.values():
        amostras = coluna.essencial.get("amostras")
        if amostras:
            coluna.essencial["amostras"] = mascarar(amostras)

        padrao = coluna.essencial.get("padrao_dominante")
        if isinstance(padrao, dict) and padrao.get("amostra_violacoes"):
            padrao["amostra_violacoes"] = mascarar(padrao["amostra_violacoes"])

        for check in coluna.checks:
            if check.amostra:
                check.amostra = mascarar(check.amostra)

        temporal = coluna.essencial.get("extremos")
        if isinstance(temporal, dict):
            continue  # datas não são PII

        coluna.notes.append(
            "Amostras e ofensores mascarados (mask_pii): trechos detectados como "
            "PII/PHI aparecem parcialmente ocultos, preservando a pontuação"
        )

"""Narrativas geradas (seção 7 do fluxo de análises).

Arquitetura decidida em 2026-08-16:

1. **Núcleo determinístico** — templates em pt-BR e inglês preenchidos com os
   números do `ColumnProfile`. Sem dependências, offline, números que nunca
   mentem. Tom do MVP: acadêmico.
2. **Plug opcional de LLM local e gratuito** (Ollama) — nunca APIs de nuvem
   por padrão: o dado do usuário não sai da máquina. O LLM **não gera
   análise**: só reformula ou traduz o texto-template pronto.
3. **Trava de números** — após qualquer reformulação, valida que todos os
   números do original aparecem intactos. Se o modelo alterou um número, o
   texto é descartado e volta o template com aviso.
"""

from maat.narrative.templates import gerar_narrativa
from maat.narrative.numbers import extrair_numeros, numeros_preservados

__all__ = ["gerar_narrativa", "extrair_numeros", "numeros_preservados"]

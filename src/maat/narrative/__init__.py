"""Narrativas geradas (seção 7 do fluxo de análises).

Arquitetura decidida em 2026-08-16:

1. **Núcleo determinístico** — templates em pt-BR e inglês preenchidos com os
   números do `ColumnProfile`. Sem dependências, offline, números que nunca
   mentem. Tom do MVP: acadêmico.
2. 🚧 **Plug de LLM — EM CONSTRUÇÃO.** `Config.narrative_llm` existe mas
   nada o consome ainda. O princípio permanece: o LLM **não gera análise**,
   só reformula ou traduz o texto pronto, e o dado não sai da máquina. O
   contrato (exigir Ollama × aceitar qualquer função texto→texto) está em
   avaliação — ver §7 do fluxo de análises.
3. **Trava de números** — após qualquer reformulação, valida que todos os
   números do original aparecem intactos. Se o modelo alterou um número, o
   texto é descartado e volta o template com aviso.
"""

from maat.narrative.templates import gerar_narrativa
from maat.narrative.numbers import extrair_numeros, numeros_preservados

__all__ = ["gerar_narrativa", "extrair_numeros", "numeros_preservados"]

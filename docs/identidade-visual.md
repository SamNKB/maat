# Identidade visual do maat

Inspiração: **Blade Runner** — neon sobre a noite, hologramas, painéis escuros, e a névoa âmbar de 2049. A estética serve a função: o maat é uma lente que revela estrutura no escuro dos dados brutos.

Os tokens prontos para uso estão em [`assets/design-tokens.css`](../assets/design-tokens.css) e a paleta visual em [`assets/palette.svg`](../assets/palette.svg).

## Cores

### Primárias — estrutura e identidade (≈80% de tudo)

| Nome | Hex | Papel |
|---|---|---|
| Void navy | `#0A0E1A` | Fundo — o preto azulado da noite de LA |
| Panel blue | `#101828` | Superfícies: cards, nós de diagrama, blocos de código |
| Neon cyan | `#00E5FF` | **A cor do maat**: destaques, bordas ativas, links, títulos |
| Ice white | `#E6F7FF` | Texto principal sobre fundo escuro |

### Secundárias — apoio e movimento

| Nome | Hex | Papel |
|---|---|---|
| Neon magenta | `#FF2E88` | Ação e fluxo: arestas de diagrama, hover, ênfase forte |
| Hologram violet | `#9D4EDD` | Decisões e interatividade: losangos de fluxograma, filtros |
| Steel blue | `#3A4A63` | Bordas neutras, divisores, elementos desabilitados |
| Mist blue | `#8FA3BF` | Texto secundário, legendas, metadados |

### Terciárias — semântica (uso pontual, sempre com o mesmo significado)

| Nome | Hex | Papel |
|---|---|---|
| Amber 2049 | `#FFB03A` | Avisos: colunas suspeitas, inferência de baixa confiança |
| Acid mint | `#3DF5C6` | Sucesso: checagens que passaram, qualidade ok |
| Signal red | `#FF4757` | Erro: dado quebrado, checagem crítica reprovada |

Regra de ouro: cyan é identidade, magenta é movimento, âmbar/mint/red **só** carregam semântica — nunca decoração. Em gráficos de dados (fase viz), a paleta categórica deriva de cyan → magenta → violet → amber → mint, nessa ordem.

### Acessibilidade

Sobre void navy `#0A0E1A`: ice white (contraste ~16:1), neon cyan (~12:1), mist blue (~7:1), amber (~9:1) — todos acima de AA. Magenta sobre navy (~5:1) passa AA para texto grande/bordas; não usar magenta para texto corrido.

## Fontes

**Decisão (2026-08-16): combinação A aprovada** — **Rajdhani** (títulos e diagramas) + **Space Grotesk** (corpo) + **JetBrains Mono** (código e dados), com Share Tech Mono como acento opcional em labels. Tokens em `assets/design-tokens.css`.

Todas gratuitas no Google Fonts. Onde aplicam: relatórios HTML do maat, site e visuais — o GitHub não carrega fontes customizadas em markdown/mermaid. As alternativas avaliadas ficam registradas abaixo.

| Papel | Opção | Vibe | Observação |
|---|---|---|---|
| Títulos/display | **Rajdhani** ⭐ | tech semi-condensada, painel militar | Funciona de título a label de diagrama |
| Títulos/display | Orbitron | sci-fi geométrica clássica | Icônica, mas cansa em títulos longos |
| Títulos/display | Audiowide | retrofuturista anos 80 | Só para logo/hero, nunca em massa |
| Títulos/display | Michroma | painel de nave, larga | Só display curto |
| Corpo/UI | **Space Grotesk** ⭐ | grotesca com personalidade futurista | Corpo com identidade sem perder leitura |
| Corpo/UI | Inter | neutra, invisível | Máxima legibilidade, zero personalidade |
| Corpo/UI | IBM Plex Sans | técnica, séria | Par natural do Plex Mono |
| Corpo/UI | Exo 2 | futurista versátil | Serve título e corpo se quiser 1 família só |
| Código/dados | **JetBrains Mono** ⭐ | moderna, altíssima legibilidade | Padrão para blocos de código e tabelas |
| Código/dados | Share Tech Mono | terminal da Tyrell Corp | A mais Blade Runner de todas — boa para acentos/labels |
| Código/dados | IBM Plex Mono | técnica clássica | — |

⭐ = a combinação aprovada.

## Aplicação nos fluxogramas (mermaid)

Os diagramas da documentação usam tema customizado via diretiva `%%{init}%%` com estes mapeamentos:

| Elemento | Token |
|---|---|
| Nós de tipo/resultado | fill panel blue, borda neon cyan, texto ice |
| Losangos de decisão | fill `#1A1030`, borda hologram violet |
| Nós de regime | fill `#0F1D2E`, borda neon magenta |
| Avisos (⚠️ suspeita) | borda e texto amber 2049 |
| Identificadores/neutros | borda steel blue, texto mist blue |
| Arestas | neon magenta |

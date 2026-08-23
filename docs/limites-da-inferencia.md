# Onde a inferência do maat falha

Documento honesto sobre os limites do nosso classificador, escrito depois de rodá-lo em **38 datasets e 609 colunas reais**. Nenhuma das falhas abaixo é hipotética: todas apareceram no benchmark.

O princípio que organiza tudo aqui é o §0.1 — **a inferência propõe, o usuário dispõe**. Um erro de classificação não é bug se o maat o declara; vira bug quando decide em silêncio.

---

## 1. A ambiguidade que nenhum sinal estatístico resolve

### Rank × identificador sequencial

Medido: `videogame-sales/Rank` e `mall-customers/CustomerID` têm assinatura **idêntica** — `k = n`, densidade ≈ 1, começam em 1, e ambos com |Spearman| = 0,9996 contra outra coluna. A diferença é semântica, não estatística: um id sequencial num arquivo ordenado por renda *é*, matematicamente, um rank de renda.

**O que fazemos**: classificamos como rank acima do limiar de monotonia, aceitando o falso positivo conhecido, e **sempre nomeamos a coluna de referência**. O `CustomerID` aparece como "colocação de `Annual Income`", e o engano fica visível na primeira leitura.

**O que não fazemos**: dicionário de nomes de coluna. Foi recusado por depender de contexto regional — e a ironia é que, ao auditar este benchmark, a própria heurística de auditoria caiu no **problema Scunthorpe**: o substring `id` casou com `acidity`, `Interceptions` e `SlidingTackle`.

---

## 2. O maior gap aberto: chaves estrangeiras

Colunas que **identificam uma entidade e se repetem** não têm sinal determinístico que as separe de uma contagem legítima:

| Coluna | k | linhas por valor | Classificado | O que é |
|---|---|---|---|---|
| `movies/userId` | 346 | 86,7 | discreta | chave estrangeira |
| `movies/movieId` | 5.024 | 6,0 | discreta | chave estrangeira |
| `gov-camara/nuDeputadoId` | 94 | 319,1 | discreta | chave estrangeira |
| `nyc-airbnb/host_id` | — | — | discreta | chave estrangeira |

Calcular média de `nuDeputadoId` é tão sem sentido quanto média de CEP. Mas nenhum dos nossos sinais os pega: não têm zeros à esquerda, não têm comprimento fixo, não passam em dígito verificador, e a razão de repetição alta é indistinguível de uma variável categórica legítima.

**Só pegamos chave estrangeira quando ela tem um sinal próprio** — `CNPJ` pelo dígito verificador, `CO_MUN` pelo comprimento fixo de 7 dígitos, `CustomerID` do ecommerce pelo comprimento fixo.

**Decisão pendente para o dono do projeto**: aceitar isso como limite declarado, ou admitir um sinal mais fraco (ex.: inteiro esparso de magnitude alta com repetição) que pegaria mais casos ao custo de falsos positivos em contagens legítimas.

---

## 3. Ambiguidades genuínas do próprio dado

Casos em que **não existe resposta certa** sem saber a pergunta de pesquisa:

### Ano
`avocado/year`, `netflix/release_year`, `suicide-rates/year`, `hotel-bookings/arrival_date_year` — todos classificados como discreta. Um ano é:
- **temporal**, se o eixo de análise for o tempo;
- **ordinal**, se for uma faixa de agrupamento;
- **discreta**, se o interesse for a contagem.

Nenhuma das três está errada. O maat escolhe discreta e o usuário reclassifica.

### Data quebrada em várias colunas
`hotel-bookings` guarda a data em `arrival_date_year` + `arrival_date_month` + `arrival_date_day_of_month`. As três viram discreta/nominal isoladamente, e **a natureza temporal desaparece** — o maat analisa colunas, não combinações. Reconstruir exigiria inferência entre colunas, que é território das bivariadas (§5, adiadas).

### Epoch como inteiro
`creditcard-fraud/Time` são segundos decorridos. Vira discreta, e é defensável — mas um timestamp Unix (`1735689600`) também viraria discreta, perdendo a natureza temporal.

---

## 4. Falhas encontradas e corrigidas

Registradas porque cada uma revelou algo sobre o desenho:

| Falha | Causa | Correção |
|---|---|---|
| Toda medição contínua de base pequena virava identificador | `k == n` é trivialmente verdadeiro para floats — cada medição é única por natureza | Identificador e rank passaram a exigir `all_integer` |
| `Year` virava código | dtype `float64` faz `2006.0` ter 6 caracteres, furando o piso de 5 do comprimento fixo | Contamos **dígitos**, não caracteres da representação |
| `InvoiceDate` parecia indecidível | As 5.000 primeiras linhas do ecommerce são todas de 1º de dezembro; a prova de mm/dd está no resto | Amostra **espalhada**, nunca a cabeça |
| Coluna constante virava discreta | Não havia rota para `k = 1` | Rota própria, declarando o fato — o `NR_CPF_CANDIDATO` do TSE é `-4` em todas as linhas, anonimizado por LGPD |
| Crash em datas com fuso | Comparar tz-aware com tz-naive levanta `TypeError` | Normalizamos para UTC sem fuso antes de comparar |

---

## 5. Limites herdados dos motores

Descobertos rodando, não previstos no design:

- **pandas 3.x usa PyArrow para strings**, e o motor RE2 **não suporta retrovisor**: a checagem `(.)\1{3,}` (4 caracteres iguais seguidos) precisa de fallback para o `re` do Python.
- **Spark 4 usa modo ANSI por padrão**: `to_timestamp` **levanta exceção** em valor malformado em vez de devolver NULL. Usamos `try_to_timestamp` com `coalesce` de formatos conhecidos.
- **Spark também recusa retrovisor e lookahead**: `repeticao` tem variante enumerada e `misto_alfabeto` é pulada.
- **`approxQuantile` diverge do exato**: no titanic, 118 atípicos no Spark contra 116 no pandas. O campo `quantile_error` reporta o erro usado — a divergência é declarada, não escondida.

---

## 6. O que essa lista não é

Não é uma lista de defeitos a esconder. Cada limite aqui está **visível no perfil**: colunas ambíguas carregam observação, o rank nomeia sua referência, o formato indecidível suspende as análises que dependem dele, e a coluna constante diz que é constante.

O maat erra como qualquer classificador erra. A diferença que perseguimos é errar **em voz alta**.

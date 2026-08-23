"""Backend PySpark — dados distribuídos, agregações no cluster.

Diferenças de contrato em relação ao pandas (§0.4):

- **Quantis via `approxQuantile`**: o erro usado (`Config.quantile_error`) é
  sempre reportado em `quantile_error`, contra 0.0 do pandas.
- **Visuais de dispersão sempre amostrados** — nunca coletar o DataFrame
  inteiro para o driver.
- **Regex distribuído** via `rlike`; a bateria de checagens roda como
  agregação única, uma passada por coluna em vez de uma por checagem.

O que roda no driver é sempre resultado já agregado ou amostra limitada.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from maat.backends.base import Backend
from maat.core.config import Config
from maat.core.meta import ColumnMeta, DateFormatEvidence, DtypeKind
from maat.core.signals import (
    CHECAGENS_TEXTO,
    CORTE_GREGORIANO,
    DATAS_SENTINELA,
    LACUNA_GREGORIANA,
    LIMITE_PANDAS_MAX,
    LIMITE_PANDAS_MIN,
    PADROES_DOMINANTES,
    evidencia_formato_data,
    normaliza_nivel,
    ordem_por_numero_inicial,
    valida_cnpj,
    valida_cpf,
)

if TYPE_CHECKING:  # pragma: no cover
    from pyspark.sql import DataFrame

# RE2 (usado pelo Spark) não suporta retrovisor — a checagem de repetição
# precisa ser reescrita sem `(.)\1{3,}`.
_SEM_RETROVISOR = {
    "repeticao": r"(aaaa|bbbb|cccc|dddd|eeee|ffff|gggg|hhhh|iiii|jjjj|kkkk|llll|"
                 r"mmmm|nnnn|oooo|pppp|qqqq|rrrr|ssss|tttt|uuuu|vvvv|wwww|xxxx|"
                 r"yyyy|zzzz|0000|1111|2222|3333|4444|5555|6666|7777|8888|9999|"
                 r"\.\.\.\.|----|____|    )",
}


class SparkBackend(Backend):
    """Implementação sobre `pyspark.sql.DataFrame`."""

    def __init__(self, df: DataFrame, config: Config | None = None) -> None:
        super().__init__(df, config)
        self._n_rows: int | None = None
        self._amostra_pd = None

    # --- infraestrutura ---------------------------------------------------

    def n_rows(self) -> int:
        if self._n_rows is None:
            self._n_rows = int(self.df.count())
        return self._n_rows

    @property
    def amostra_pandas(self):
        """Amostra trazida ao driver para a inferência de tipos.

        Só a **rota** é decidida aqui; todas as contagens das análises são
        agregações distribuídas sobre a base inteira.
        """
        if self._amostra_pd is None:
            limite = self.config.inference_sample_size or 100_000
            total = self.n_rows()
            if total > limite:
                fracao = min(1.0, (limite * 1.2) / total)
                amostrado = self.df.sample(False, fracao, seed=42).limit(limite)
            else:
                amostrado = self.df
            self._amostra_pd = amostrado.toPandas()
        return self._amostra_pd

    # --- metadados --------------------------------------------------------

    def columns_meta(self) -> dict[str, ColumnMeta]:
        """Reaproveita a lógica do pandas sobre a amostra trazida ao driver.

        Os sinais de inferência (dígito verificador, zeros à esquerda,
        Spearman) são estatísticas de amostra por definição — trazê-los ao
        driver é mais barato que distribuí-los, e o resultado é o mesmo.
        """
        from maat.backends.pandas_backend import PandasBackend

        auxiliar = PandasBackend(self.amostra_pandas, self.config)
        metas = auxiliar.columns_meta()
        total = self.n_rows()
        amostrados = len(self.amostra_pandas)
        if amostrados and total > amostrados:
            escala = total / amostrados
            for meta in metas.values():
                meta.n = total
                meta.n_missing = int(meta.n_missing * escala)
        return metas

    # --- helpers ----------------------------------------------------------

    def _col(self, column: str):
        from pyspark.sql import functions as F

        return F.col(f"`{column}`")

    def _validos(self, column: str) -> DataFrame:
        return self.df.filter(self._col(column).isNotNull())

    def _texto(self, column: str):
        from pyspark.sql import functions as F

        return F.col(f"`{column}`").cast("string")

    def _numerico(self, column: str):
        from pyspark.sql import functions as F

        return F.col(f"`{column}`").cast("double")

    # Formatos tentados em ordem; o primeiro que casar vence (coalesce).
    # A ordem dd/mm × mm/dd vem da evidência detectada na inferência (§4.1) —
    # sem ela, o Spark escolheria em silêncio, que é o que não queremos.
    _FORMATOS_DATA = [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd'T'HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy HH:mm",
        "dd/MM/yyyy",
        "MM/dd/yyyy HH:mm",
        "MM/dd/yyyy",
        "d/M/yyyy H:mm",
        "M/d/yyyy H:mm",
        "MMMM d, yyyy",
        "yyyy/MM/dd",
    ]

    def _data(self, column: str, evidencia: str | None = None):
        """Coluna como timestamp, tolerando string, fuso e valores inválidos.

        O Spark 4 usa modo ANSI por padrão: `to_timestamp` **levanta exceção**
        em valores malformados em vez de devolver NULL. Usamos
        `try_to_timestamp`, que é a forma tolerante, e encadeamos os formatos
        conhecidos com `coalesce`.
        """
        from pyspark.sql import functions as F

        tipo = dict(self.df.dtypes).get(column, "")
        if tipo.startswith(("timestamp", "date")):
            return F.col(f"`{column}`").cast("timestamp")

        texto = self._texto(column)
        formatos = list(self._FORMATOS_DATA)
        if evidencia == "mdy":  # prioriza mm/dd quando a evidência provou
            formatos.sort(key=lambda f: 0 if f.startswith(("MM/", "M/")) else 1)
        elif evidencia == "dmy":
            formatos.sort(key=lambda f: 0 if f.startswith(("dd/", "d/")) else 1)

        tentativas = [F.try_to_timestamp(texto, F.lit(f)) for f in formatos]
        tentativas.append(F.try_to_timestamp(texto))
        return F.coalesce(*tentativas)

    # --- qualitativas -----------------------------------------------------

    def value_counts(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        from pyspark.sql import functions as F

        agrupado = (
            self._validos(column)
            .groupBy(self._col(column).alias("_v"))
            .agg(F.count(F.lit(1)).alias("_n"))
            .orderBy(F.desc("_n"))
        )
        if top_n:
            agrupado = agrupado.limit(top_n)
        return {linha["_v"]: int(linha["_n"]) for linha in agrupado.collect()}

    def spelling_variant_groups(self, column: str) -> list[list[tuple[Any, int]]]:
        """Critério declarado: minúsculas, sem acentos, espaços colapsados.

        No Spark a normalização roda distribuída; só os grupos com mais de
        um nível chegam ao driver.
        """
        from collections import defaultdict

        from pyspark.sql import functions as F

        normalizada = F.trim(
            F.regexp_replace(
                F.lower(F.translate(self._texto(column),
                                    "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                                    "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")),
                r"\s+", " ",
            )
        )
        contagem = (
            self._validos(column)
            .groupBy(self._col(column).alias("_v"), normalizada.alias("_k"))
            .agg(F.count(F.lit(1)).alias("_n"))
        )
        com_variantes = (
            contagem.groupBy("_k")
            .agg(F.count(F.lit(1)).alias("_niveis"))
            .filter(F.col("_niveis") > 1)
        )
        alvo = contagem.join(com_variantes.select("_k"), on="_k", how="inner")
        grupos: dict[str, list[tuple[Any, int]]] = defaultdict(list)
        for linha in alvo.collect():
            grupos[linha["_k"]].append((linha["_v"], int(linha["_n"])))
        return [sorted(g, key=lambda x: -x[1]) for g in grupos.values()]

    # --- quantitativas ----------------------------------------------------

    def numeric_summary(self, column: str) -> dict[str, float]:
        from pyspark.sql import functions as F

        alvo = self.df.select(self._numerico(column).alias("v")).filter(
            F.col("v").isNotNull()
        )
        erro = self.config.quantile_error
        quantis = alvo.approxQuantile("v", [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99], erro)
        if not quantis:
            return {"quantile_error": erro}
        p1, p5, q1, mediana, q3, p95, p99 = quantis

        linha = alvo.agg(
            F.count("v").alias("n"),
            F.min("v").alias("min"),
            F.max("v").alias("max"),
            F.avg("v").alias("media"),
            F.stddev("v").alias("desvio"),
            F.skewness("v").alias("assimetria"),
            F.kurtosis("v").alias("curtose"),
            F.sum(F.when(F.col("v") == 0, 1).otherwise(0)).alias("zeros"),
            F.sum(F.when(F.col("v") < 0, 1).otherwise(0)).alias("negativos"),
        ).collect()[0]
        n = int(linha["n"]) or 1

        iqr = q3 - q1
        atipicos = int(
            alvo.filter(
                (F.col("v") < q1 - 1.5 * iqr) | (F.col("v") > q3 + 1.5 * iqr)
            ).count()
        )
        moda_linha = (
            alvo.groupBy("v").agg(F.count(F.lit(1)).alias("_n"))
            .orderBy(F.desc("_n")).limit(1).collect()
        )
        media = float(linha["media"]) if linha["media"] is not None else None
        desvio = float(linha["desvio"]) if linha["desvio"] is not None else None
        return {
            "n": n,
            "min": float(linha["min"]),
            "max": float(linha["max"]),
            "media": media,
            "mediana": mediana,
            "moda": moda_linha[0]["v"] if moda_linha else None,
            "q1": q1,
            "q3": q3,
            "p1": p1,
            "p5": p5,
            "p95": p95,
            "p99": p99,
            "desvio_padrao": desvio,
            "iqr": iqr,
            "cv": (desvio / media) if media else None,
            "assimetria": float(linha["assimetria"]) if linha["assimetria"] is not None else None,
            "curtose": float(linha["curtose"]) if linha["curtose"] is not None else None,
            "pct_zeros": int(linha["zeros"]) / n,
            "pct_negativos": int(linha["negativos"]) / n,
            "atipicos_iqr": atipicos,
            "pct_atipicos_iqr": atipicos / n,
            "quantile_error": erro,
        }

    def histogram(self, column: str, bins: int) -> dict[str, list[float]]:
        alvo = self.df.select(self._numerico(column).alias("v")).filter(
            "v is not null"
        )
        try:
            bordas, contagens = alvo.rdd.map(lambda r: r["v"]).histogram(bins)
        except Exception:  # noqa: BLE001 — coluna constante ou vazia
            return {"bordas": [], "contagens": []}
        return {"bordas": [float(b) for b in bordas],
                "contagens": [int(c) for c in contagens]}

    def value_extremes(self, column: str, n: int) -> dict[str, list[tuple[Any, int]]]:
        from pyspark.sql import functions as F

        agrupado = (
            self.df.select(self._numerico(column).alias("v"))
            .filter("v is not null")
            .groupBy("v")
            .agg(F.count(F.lit(1)).alias("_n"))
        )
        maiores = agrupado.orderBy(F.desc("v")).limit(n).collect()
        menores = agrupado.orderBy(F.asc("v")).limit(n).collect()
        return {
            "maiores": [(linha["v"], int(linha["_n"])) for linha in maiores],
            "menores": [(linha["v"], int(linha["_n"])) for linha in menores],
        }

    def frequency_extremes(self, column: str, n: int) -> dict[str, list[tuple[Any, int]]]:
        from pyspark.sql import functions as F

        agrupado = (
            self._validos(column)
            .groupBy(self._col(column).alias("_v"))
            .agg(F.count(F.lit(1)).alias("_n"))
        )
        mais = agrupado.orderBy(F.desc("_n")).limit(n).collect()
        # empates na menor frequência: os valores mais extremos primeiro
        menos = (
            agrupado.orderBy(F.asc("_n"), F.desc(F.abs(F.col("_v").cast("double"))))
            .limit(n)
            .collect()
        )
        return {
            "mais_frequentes": [(l["_v"], int(l["_n"])) for l in mais],
            "menos_frequentes": [(l["_v"], int(l["_n"])) for l in menos],
        }

    # --- temporais --------------------------------------------------------

    def temporal_summary(self, column: str) -> dict[str, Any]:
        """Cobertura, granularidade, horizonte, sentinelas e quebras.

        **Uma única agregação** para tudo: horizontes, sentinelas e quebras
        de calendário viram colunas de um só `agg`. Ingênuo seria um
        `count()` por checagem — 15 varreduras completas da base.
        """
        from pyspark.sql import functions as F

        alvo = self.df.select(self._data(column).alias("d"))
        validos = alvo.filter(F.col("d").isNotNull())

        d = F.col("d")
        anos = F.months_between(F.current_timestamp(), d) / 12
        formatada = F.date_format(d, "yyyy-MM-dd")

        expressoes = [
            F.count(F.lit(1)).alias("n"),
            F.min("d").alias("min"),
            F.max("d").alias("max"),
            F.sum(F.when(d > F.current_timestamp(), 1).otherwise(0)).alias("fut"),
            F.sum(F.when(F.hour(d) + F.minute(d) + F.second(d) == 0, 1)
                  .otherwise(0)).alias("meia_noite"),
            F.sum(F.when(F.dayofmonth(d) == 1, 1).otherwise(0)).alias("dia_um"),
        ]
        for a in self.config.date_horizons:
            expressoes.append(
                F.sum(F.when(anos > a, 1).otherwise(0)).alias(f"h_{a}")
            )
        for i, data in enumerate(DATAS_SENTINELA):
            expressoes.append(
                F.sum(F.when(formatada == data, 1).otherwise(0)).alias(f"s_{i}")
            )
        expressoes += [
            F.sum(F.when(d < F.lit(CORTE_GREGORIANO).cast("timestamp"), 1)
                  .otherwise(0)).alias("q_rebase"),
            F.sum(F.when(
                (d >= F.lit(LACUNA_GREGORIANA[0]).cast("timestamp"))
                & (d <= F.lit(LACUNA_GREGORIANA[1]).cast("timestamp")), 1)
                .otherwise(0)).alias("q_lacuna"),
            F.sum(F.when(
                (d < F.lit(LIMITE_PANDAS_MIN).cast("timestamp"))
                | (d > F.lit(LIMITE_PANDAS_MAX).cast("timestamp")), 1)
                .otherwise(0)).alias("q_dtype"),
        ]

        r = validos.agg(*expressoes).collect()[0]
        n = int(r["n"] or 0)
        if not n:
            return {"n": 0}

        bruto_nao_nulo = int(self._validos(column).count())
        minimo, maximo = r["min"], r["max"]
        futuro = int(r["fut"])

        sentinelas = {}
        for i, (data, descricao) in enumerate(DATAS_SENTINELA.items()):
            q = int(r[f"s_{i}"] or 0)
            if q:
                sentinelas[data] = {"n": q, "significado": descricao}

        if int(r["meia_noite"]) == n:
            granularidade = "mensal" if int(r["dia_um"]) == n else "diaria"
        else:
            granularidade = "com_hora"

        n_ext = self.config.temporal_extremes_levels
        antigas = validos.orderBy(F.asc("d")).limit(n_ext).collect()
        futuras = validos.orderBy(F.desc("d")).limit(n_ext).collect()

        return {
            "n": n,
            "n_missing": self.n_rows() - bruto_nao_nulo,
            "falha_parse": bruto_nao_nulo - n,
            "minimo": minimo.isoformat(),
            "maximo": maximo.isoformat(),
            "amplitude_dias": (maximo - minimo).days,
            "granularidade": granularidade,
            "no_futuro": futuro,
            "pct_futuro": futuro / n,
            "horizonte": {
                f">{a} anos": int(r[f"h_{a}"] or 0) for a in self.config.date_horizons
            },
            "sentinelas": sentinelas,
            "mais_antigas": [x["d"].isoformat() for x in antigas],
            "mais_futuras": [x["d"].isoformat() for x in reversed(futuras)],
            "quebras": {
                "rebase_spark": {
                    "n": int(r["q_rebase"] or 0),
                    "criterio": f"anteriores a {CORTE_GREGORIANO}; mudam de valor entre "
                                "calendário híbrido e proléptico ao ler Parquet/Avro",
                },
                "lacuna_gregoriana": {
                    "n": int(r["q_lacuna"] or 0),
                    "criterio": f"entre {LACUNA_GREGORIANA[0]} e "
                                f"{LACUNA_GREGORIANA[1]}, dias que não existem no "
                                "calendário híbrido",
                },
                "fora_datetime64_ns": {
                    "n": int(r["q_dtype"] or 0),
                    "criterio": f"antes de {LIMITE_PANDAS_MIN} ou após "
                                f"{LIMITE_PANDAS_MAX}: o Spark representa, o pandas "
                                "não — armadilha de interoperabilidade",
                },
            },
            "gaps": [],
        }

    def _quebras_calendario(self, validos: DataFrame) -> dict[str, Any]:
        """Rebase do Spark, lacuna gregoriana e limites do dtype (§4.1).

        Aqui a checagem é especialmente pertinente: é o próprio Spark que
        faz o rebase ao ler Parquet e Avro.
        """
        from pyspark.sql import functions as F

        def conta(condicao) -> int:
            return int(validos.filter(condicao).count())

        d = F.col("d")
        return {
            "rebase_spark": {
                "n": conta(d < F.lit(CORTE_GREGORIANO).cast("timestamp")),
                "criterio": f"anteriores a {CORTE_GREGORIANO}; mudam de valor entre "
                            "calendário híbrido e proléptico ao ler Parquet/Avro",
            },
            "lacuna_gregoriana": {
                "n": conta(
                    (d >= F.lit(LACUNA_GREGORIANA[0]).cast("timestamp"))
                    & (d <= F.lit(LACUNA_GREGORIANA[1]).cast("timestamp"))
                ),
                "criterio": f"entre {LACUNA_GREGORIANA[0]} e {LACUNA_GREGORIANA[1]}, "
                            "dias que não existem no calendário híbrido",
            },
            "fora_datetime64_ns": {
                "n": conta(
                    (d < F.lit(LIMITE_PANDAS_MIN).cast("timestamp"))
                    | (d > F.lit(LIMITE_PANDAS_MAX).cast("timestamp"))
                ),
                "criterio": f"antes de {LIMITE_PANDAS_MIN} ou após {LIMITE_PANDAS_MAX}: "
                            "o Spark representa, o pandas não — armadilha de "
                            "interoperabilidade",
            },
        }

    def cyclic_profiles(self, column: str) -> dict[str, dict[Any, int]]:
        from pyspark.sql import functions as F

        alvo = self.df.select(self._data(column).alias("d")).filter("d is not null")
        dias = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]

        def contar(expr) -> dict:
            linhas = alvo.groupBy(expr.alias("_c")).agg(
                F.count(F.lit(1)).alias("_n")
            ).orderBy("_c").collect()
            return {linha["_c"]: int(linha["_n"]) for linha in linhas}

        perfis = {
            "mes": contar(F.month("d")),
            "trimestre": contar(F.quarter("d")),
        }
        semana = contar(F.dayofweek("d"))
        perfis["dia_semana"] = {dias[int(k) - 1]: v for k, v in semana.items()}
        perfis["hora"] = contar(F.hour("d"))
        return perfis

    def counts_by_period(self, column: str, freq: str = "M") -> dict[str, int]:
        from pyspark.sql import functions as F

        formato = {"M": "yyyy-MM", "D": "yyyy-MM-dd", "Y": "yyyy"}.get(freq, "yyyy-MM")
        alvo = self.df.select(self._data(column).alias("d")).filter("d is not null")
        linhas = (
            alvo.groupBy(F.date_format("d", formato).alias("_p"))
            .agg(F.count(F.lit(1)).alias("_n"))
            .orderBy("_p")
            .collect()
        )
        return {linha["_p"]: int(linha["_n"]) for linha in linhas}

    # --- textuais ---------------------------------------------------------

    def text_profile(self, column: str) -> dict[str, Any]:
        from pyspark.sql import functions as F

        alvo = self._validos(column).select(self._texto(column).alias("v"))
        comprimento = F.length("v")
        erro = self.config.quantile_error
        quantis = alvo.select(comprimento.alias("L")).approxQuantile(
            "L", [0.25, 0.5, 0.75], erro
        )
        linha = alvo.agg(
            F.min(comprimento).alias("min"), F.max(comprimento).alias("max")
        ).collect()[0]

        n = self.config.textual_sample_size
        curtas = alvo.orderBy(comprimento.asc()).limit(n).collect()
        longas = alvo.orderBy(comprimento.desc()).limit(n).collect()
        aleatorias = alvo.sample(False, min(1.0, 5_000 / max(self.n_rows(), 1)),
                                 seed=42).limit(n).collect()

        mascara = F.regexp_replace(
            F.regexp_replace(F.regexp_replace("v", "[a-záàâãéêíóôõúüç]", "a"),
                             "[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]", "A"),
            r"\d", "9",
        )
        mascaras = (
            alvo.groupBy(mascara.alias("_m"))
            .agg(F.count(F.lit(1)).alias("_n"))
            .orderBy(F.desc("_n"))
            .limit(self.config.textual_mask_top_n)
            .collect()
        )
        padrao, aderencia, violacoes = self._padrao_dominante(alvo)

        return {
            "comprimento": {
                "min": int(linha["min"]),
                "p25": int(quantis[0]) if quantis else None,
                "mediana": int(quantis[1]) if quantis else None,
                "p75": int(quantis[2]) if quantis else None,
                "max": int(linha["max"]),
            },
            "amostras": {
                "mais_curtas": [r["v"] for r in curtas],
                "mais_longas": [r["v"] for r in longas],
                "aleatorias": [r["v"] for r in aleatorias],
            },
            "mascaras_top": [{"mascara": r["_m"], "n": int(r["_n"])} for r in mascaras],
            "padrao_dominante": {
                "tipo": padrao,
                "aderencia": aderencia,
                "amostra_violacoes": violacoes,
            },
        }

    def _padrao_dominante(self, alvo: DataFrame):
        """Aderência dos padrões conhecidos em **uma** agregação, não sete."""
        from pyspark.sql import functions as F

        expressoes = [F.count(F.lit(1)).alias("_total")]
        for nome, regex in PADROES_DOMINANTES:
            expressoes.append(
                F.sum(F.when(F.col("v").rlike(regex), 1).otherwise(0)).alias(nome)
            )
        r = alvo.agg(*expressoes).collect()[0]
        total = int(r["_total"] or 0) or 1

        melhor, melhor_taxa, melhor_regex = None, 0.0, None
        for nome, regex in PADROES_DOMINANTES:
            taxa = int(r[nome] or 0) / total
            if taxa > melhor_taxa:
                melhor, melhor_taxa, melhor_regex = nome, taxa, regex
        if melhor is None or melhor_taxa < 0.5:
            return None, None, []
        violacoes = (
            alvo.filter(~F.col("v").rlike(melhor_regex))
            .limit(self.config.textual_sample_size)
            .collect()
        )
        return melhor, melhor_taxa, [r["v"] for r in violacoes]

    def text_checks(self, column: str) -> list[dict[str, Any]]:
        """Bateria em **uma única passada**: todas as checagens viram colunas
        de uma agregação só, em vez de um scan por checagem.
        """
        from pyspark.sql import functions as F

        alvo = self._validos(column).select(self._texto(column).alias("v"))
        total = int(alvo.count())
        if not total:
            return []

        todas = list(CHECAGENS_TEXTO) + [
            (c.nome, c.regex, c.descricao) for c in self.config.textual_extra_checks
        ]
        expressoes, metadados = [], []
        for nome, regex, descricao in todas:
            padrao = _SEM_RETROVISOR.get(nome, regex)
            if "\\1" in padrao or "(?=" in padrao:
                continue  # RE2 não suporta retrovisor nem lookahead
            expressoes.append(
                F.sum(F.when(F.col("v").rlike(padrao), 1).otherwise(0)).alias(nome)
            )
            metadados.append((nome, padrao, descricao))

        if not expressoes:
            return []
        contagens = alvo.agg(*expressoes).collect()[0].asDict()

        resultados = []
        for nome, padrao, descricao in metadados:
            qtd = int(contagens.get(nome) or 0)
            if not qtd:
                continue
            amostra = (
                alvo.filter(F.col("v").rlike(padrao))
                .limit(self.config.textual_sample_size)
                .collect()
            )
            resultados.append({
                "nome": nome,
                "descricao": descricao,
                "n": qtd,
                "pct": qtd / total,
                "amostra": [r["v"] for r in amostra],
            })
        return resultados

    # --- identificadores --------------------------------------------------

    def identifier_summary(self, column: str) -> dict[str, Any]:
        from pyspark.sql import functions as F

        alvo = self._validos(column)
        n = int(alvo.count())
        agrupado = (
            alvo.groupBy(self._col(column).alias("_v"))
            .agg(F.count(F.lit(1)).alias("_n"))
        )
        k = int(agrupado.count())
        colisoes = agrupado.filter(F.col("_n") > 1)
        n_colisoes = int(colisoes.count())
        amostra = colisoes.orderBy(F.desc("_n")).limit(5).collect()
        return {
            "n": n,
            "n_distinct": k,
            "unico": n_colisoes == 0,
            "n_colisoes": n_colisoes,
            "linhas_por_valor": n / k if k else 0.0,
            "amostra_colisoes": [
                {"valor": r["_v"], "n": int(r["_n"])} for r in amostra
            ],
        }

    # --- amostragem -------------------------------------------------------

    def sample(self, columns: list[str], n: int) -> list[dict[str, Any]]:
        total = self.n_rows()
        fracao = min(1.0, (n * 1.5) / total) if total else 1.0
        linhas = (
            self.df.select(*[f"`{c}`" for c in columns])
            .sample(False, fracao, seed=42)
            .limit(n)
            .collect()
        )
        return [linha.asDict() for linha in linhas]

"""Backend pandas — dados locais, resultados exatos.

Quantis são exatos aqui (`quantile_error = 0.0`); no Spark são aproximados
e o erro usado é reportado no mesmo campo.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

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
    mascara_caractere,
    normaliza_nivel,
    ordem_por_numero_inicial,
    valida_cnpj,
    valida_cpf,
)

RE_ZERO_ESQUERDA = re.compile(r"^0\d")


class PandasBackend(Backend):
    """Implementação sobre `pandas.DataFrame`."""

    def __init__(self, df: pd.DataFrame, config: Config | None = None) -> None:
        super().__init__(df, config)
        self._amostra: pd.DataFrame | None = None

    # --- infraestrutura ---------------------------------------------------

    def n_rows(self) -> int:
        return len(self.df)

    @property
    def amostra(self) -> pd.DataFrame:
        """Amostra de inferência — decide a rota, não as contagens finais."""
        if self._amostra is None:
            limite = self.config.inference_sample_size
            if limite and len(self.df) > limite:
                self._amostra = self.df.sample(limite, random_state=42)
            else:
                self._amostra = self.df
        return self._amostra

    def _serie(self, column: str) -> pd.Series:
        return self.df[column]

    def _validos(self, column: str) -> pd.Series:
        return self.df[column].dropna()

    # --- metadados --------------------------------------------------------

    def columns_meta(self) -> dict[str, ColumnMeta]:
        amostra = self.amostra
        numericas = [
            c for c in amostra.columns if pd.api.types.is_numeric_dtype(amostra[c])
        ]
        spearman = self._matriz_spearman(amostra, numericas)

        metas: dict[str, ColumnMeta] = {}
        for coluna in amostra.columns:
            metas[str(coluna)] = self._meta_coluna(
                amostra, str(coluna), spearman.get(str(coluna))
            )
        return metas

    def _matriz_spearman(
        self, df: pd.DataFrame, numericas: list[str]
    ) -> dict[str, tuple[float, str]]:
        """Maior |Spearman| de cada numérica contra as demais (§3.3)."""
        if len(numericas) < 2:
            return {}
        alvo = df[numericas]
        if len(alvo) > 20_000:
            alvo = alvo.sample(20_000, random_state=42)
        try:
            corr = alvo.corr(method="spearman", numeric_only=True)
        except Exception:  # noqa: BLE001 — correlação não é essencial ao perfil
            return {}
        saida: dict[str, tuple[float, str]] = {}
        for coluna in corr.columns:
            outras = corr[coluna].drop(labels=[coluna], errors="ignore").dropna()
            if outras.empty:
                continue
            ref = outras.abs().idxmax()
            saida[str(coluna)] = (float(outras[ref]), str(ref))
        return saida

    def _meta_coluna(
        self, df: pd.DataFrame, coluna: str, spearman: tuple[float, str] | None
    ) -> ColumnMeta:
        s = df[coluna]
        validos = s.dropna()
        meta = ColumnMeta(
            name=coluna,
            dtype_kind=self._dtype_kind(s),
            n=len(s),
            n_missing=int(s.isna().sum()),
            n_distinct=int(validos.nunique()) if len(validos) else 0,
            sample_values=[self._py(v) for v in validos.head(5).tolist()],
        )
        if not len(validos):
            return meta

        if spearman:
            meta.max_spearman, meta.spearman_reference = spearman

        if meta.dtype_kind is DtypeKind.NUMERIC:
            self._meta_numerica(validos, meta)
        elif meta.dtype_kind is DtypeKind.STRING:
            self._meta_texto(validos, meta)
        elif meta.dtype_kind is DtypeKind.DATETIME:
            meta.parse_date_rate = 1.0
        return meta

    def _meta_numerica(self, validos: pd.Series, meta: ColumnMeta) -> None:
        numerica = pd.to_numeric(validos, errors="coerce").dropna()
        if numerica.empty:
            return
        meta.minimum = float(numerica.min())
        meta.maximum = float(numerica.max())
        meta.all_integer = bool(np.all(np.mod(numerica.to_numpy(), 1) == 0))

        # Um inteiro guardado como float vira "2006.0": medir o comprimento
        # da representação textual contaria o ".0" e faria um ano de 4 dígitos
        # parecer código de 6. Contamos dígitos.
        if meta.all_integer:
            texto = numerica.astype("int64").astype(str)
        else:
            texto = validos.astype(str)
        meta.has_leading_zeros = bool(texto.str.match(RE_ZERO_ESQUERDA).any())
        digitos = texto.str.replace(r"\D", "", regex=True).str.len()
        meta.fixed_length = bool(digitos.nunique() == 1 and digitos.iloc[0] >= 5)
        self._meta_digito_verificador(texto, meta)

    def _meta_texto(self, validos: pd.Series, meta: ColumnMeta) -> None:
        texto = validos.astype(str).str.strip()
        # Amostra ESPALHADA, não a cabeça: no ecommerce as primeiras 5.000
        # linhas são todas de 1º de dezembro e pareceriam indecidíveis, embora
        # a coluna inteira prove mm/dd com 308.950 valores.
        cabeca = texto.sample(min(5_000, len(texto)), random_state=42)

        parseadas = pd.to_datetime(cabeca, errors="coerce", format="mixed")
        meta.parse_date_rate = float(parseadas.notna().mean())

        if meta.parse_date_rate >= self.config.date_parse_min_rate:
            dmy, mdy, ambiguos = evidencia_formato_data(cabeca.tolist())
            meta.dmy_proofs, meta.mdy_proofs, meta.ambiguous_dates = dmy, mdy, ambiguos
            if dmy and mdy:
                meta.date_format_evidence = DateFormatEvidence.MIXED
            elif dmy:
                meta.date_format_evidence = DateFormatEvidence.DMY
            elif mdy:
                meta.date_format_evidence = DateFormatEvidence.MDY
            elif ambiguos:
                meta.date_format_evidence = DateFormatEvidence.UNDECIDABLE
            return

        meta.has_leading_zeros = bool(cabeca.str.match(RE_ZERO_ESQUERDA).any())
        comprimentos = cabeca.str.len()
        meta.fixed_length = bool(comprimentos.nunique() == 1 and comprimentos.iloc[0] >= 5)
        self._meta_digito_verificador(cabeca, meta)

        if 2 < meta.n_distinct <= self.config.max_categorical_levels:
            niveis = validos.astype(str).unique().tolist()
            meta.leading_number_order = ordem_por_numero_inicial(niveis)

    def _meta_digito_verificador(self, texto: pd.Series, meta: ColumnMeta) -> None:
        candidatos = texto.head(2_000)
        digitos = candidatos.str.replace(r"\D", "", regex=True).str.len()
        if (digitos == 14).mean() > 0.5:
            taxa = float(candidatos.map(valida_cnpj).mean())
            if taxa > meta.check_digit_rate:
                meta.check_digit_rate, meta.check_digit_kind = taxa, "cnpj"
        if (digitos == 11).mean() > 0.5:
            taxa = float(candidatos.map(valida_cpf).mean())
            if taxa > meta.check_digit_rate:
                meta.check_digit_rate, meta.check_digit_kind = taxa, "cpf"

    @staticmethod
    def _dtype_kind(s: pd.Series) -> DtypeKind:
        if pd.api.types.is_bool_dtype(s):
            return DtypeKind.BOOL
        if pd.api.types.is_datetime64_any_dtype(s):
            return DtypeKind.DATETIME
        if pd.api.types.is_timedelta64_dtype(s):
            return DtypeKind.TIMEDELTA
        if pd.api.types.is_numeric_dtype(s):
            return DtypeKind.NUMERIC
        if pd.api.types.is_string_dtype(s) or s.dtype == object:
            return DtypeKind.STRING
        return DtypeKind.OTHER

    @staticmethod
    def _py(valor: Any) -> Any:
        """Converte tipos numpy/pandas para nativos, para serialização."""
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            return None
        if isinstance(valor, (np.integer,)):
            return int(valor)
        if isinstance(valor, (np.floating,)):
            return float(valor)
        if isinstance(valor, (np.bool_,)):
            return bool(valor)
        if isinstance(valor, (pd.Timestamp,)):
            return valor.isoformat()
        return valor

    # --- qualitativas -----------------------------------------------------

    def value_counts(self, column: str, top_n: int | None = None) -> dict[Any, int]:
        vc = self._validos(column).value_counts()
        if top_n:
            vc = vc.head(top_n)
        return {self._py(k): int(v) for k, v in vc.items()}

    def spelling_variant_groups(self, column: str) -> list[list[tuple[Any, int]]]:
        vc = self._validos(column).value_counts()
        grupos: dict[str, list[tuple[Any, int]]] = defaultdict(list)
        for valor, n in vc.items():
            grupos[normaliza_nivel(valor)].append((self._py(valor), int(n)))
        return [g for g in grupos.values() if len(g) > 1]

    # --- quantitativas ----------------------------------------------------

    def numeric_summary(self, column: str) -> dict[str, float]:
        s = pd.to_numeric(self._validos(column), errors="coerce").dropna()
        if s.empty:
            return {"quantile_error": 0.0}
        q = s.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
        iqr = float(q[0.75] - q[0.25])
        media, desvio = float(s.mean()), float(s.std())
        atipicos = int(
            ((s < q[0.25] - 1.5 * iqr) | (s > q[0.75] + 1.5 * iqr)).sum()
        )
        return {
            "n": int(s.size),
            "min": float(s.min()),
            "max": float(s.max()),
            "media": media,
            "mediana": float(q[0.5]),
            "moda": self._py(s.mode().iloc[0]) if not s.mode().empty else None,
            "q1": float(q[0.25]),
            "q3": float(q[0.75]),
            "p1": float(q[0.01]),
            "p5": float(q[0.05]),
            "p95": float(q[0.95]),
            "p99": float(q[0.99]),
            "desvio_padrao": desvio,
            "iqr": iqr,
            "cv": float(desvio / media) if media else None,
            "assimetria": float(s.skew()),
            "curtose": float(s.kurt()),
            "pct_zeros": float((s == 0).mean()),
            "pct_negativos": float((s < 0).mean()),
            "atipicos_iqr": atipicos,
            "pct_atipicos_iqr": float(atipicos / s.size),
            "quantile_error": 0.0,
        }

    def histogram(self, column: str, bins: int) -> dict[str, list[float]]:
        s = pd.to_numeric(self._validos(column), errors="coerce").dropna()
        if s.empty:
            return {"bordas": [], "contagens": []}
        contagens, bordas = np.histogram(s.to_numpy(), bins=bins)
        return {
            "bordas": [float(b) for b in bordas],
            "contagens": [int(c) for c in contagens],
        }

    def value_extremes(self, column: str, n: int) -> dict[str, list[tuple[Any, int]]]:
        s = pd.to_numeric(self._validos(column), errors="coerce").dropna()
        if s.empty:
            return {"maiores": [], "menores": []}
        vc = s.value_counts()
        ordenados = sorted(vc.index.tolist())
        menores = [(self._py(v), int(vc[v])) for v in ordenados[:n]]
        maiores = [(self._py(v), int(vc[v])) for v in reversed(ordenados[-n:])]
        return {"maiores": maiores, "menores": menores}

    def frequency_extremes(self, column: str, n: int) -> dict[str, list[tuple[Any, int]]]:
        """Mais e menos frequentes; empates na menor frequência são
        desempatados pelos valores mais extremos (§3.1)."""
        vc = self._validos(column).value_counts()
        if vc.empty:
            return {"mais_frequentes": [], "menos_frequentes": []}
        mais = [(self._py(k), int(v)) for k, v in vc.head(n).items()]
        minimo = vc.min()
        empatados = vc[vc == minimo].index.tolist()
        try:
            empatados = sorted(empatados, key=lambda x: abs(float(x)), reverse=True)
        except (TypeError, ValueError):
            empatados = sorted(empatados, key=lambda x: str(x))
        menos = [(self._py(v), int(minimo)) for v in empatados[:n]]
        return {"mais_frequentes": mais, "menos_frequentes": menos}

    # --- temporais --------------------------------------------------------

    def _como_datas(self, column: str) -> pd.Series:
        """Devolve a coluna como datas **sem fuso**.

        Comparar tz-aware com tz-naive levanta TypeError no pandas, e o
        perfil precisa comparar com "hoje". Descartamos o fuso após
        converter, registrando que a coluna era tz-aware.
        """
        s = self._validos(column)
        if not pd.api.types.is_datetime64_any_dtype(s):
            s = pd.to_datetime(s, errors="coerce", format="mixed").dropna()
        if getattr(s.dtype, "tz", None) is not None:
            s = s.dt.tz_convert("UTC").dt.tz_localize(None)
        return s

    def temporal_summary(self, column: str) -> dict[str, Any]:
        d = self._como_datas(column)
        bruto = self._serie(column)
        if d.empty:
            return {"n": 0}

        hoje = pd.Timestamp.now().normalize()
        idade_anos = (hoje - d).dt.days / 365.25
        horizonte = {
            f">{a} anos": int((idade_anos > a).sum()) for a in self.config.date_horizons
        }

        sentinelas = {}
        formatadas = d.dt.strftime("%Y-%m-%d")
        for data, descricao in DATAS_SENTINELA.items():
            q = int((formatadas == data).sum())
            if q:
                sentinelas[data] = {"n": q, "significado": descricao}

        n_extremos = self.config.temporal_extremes_levels
        ordenadas = d.sort_values()
        return {
            "n": int(d.size),
            "n_missing": int(bruto.isna().sum()),
            "falha_parse": int(len(bruto.dropna()) - d.size),
            "minimo": ordenadas.iloc[0].isoformat(),
            "maximo": ordenadas.iloc[-1].isoformat(),
            "amplitude_dias": int((ordenadas.iloc[-1] - ordenadas.iloc[0]).days),
            "granularidade": self._granularidade(d),
            "no_futuro": int((d > hoje).sum()),
            "pct_futuro": float((d > hoje).mean()),
            "horizonte": horizonte,
            "sentinelas": sentinelas,
            "mais_antigas": [x.isoformat() for x in ordenadas.head(n_extremos)],
            "mais_futuras": [x.isoformat() for x in ordenadas.tail(n_extremos)],
            "quebras": self._quebras_calendario(d),
            "gaps": self._gaps(d),
        }

    @staticmethod
    def _granularidade(d: pd.Series) -> str:
        if bool((d.dt.time == pd.Timestamp("00:00").time()).all()):
            if bool((d.dt.day == 1).all()):
                return "mensal"
            return "diaria"
        if bool((d.dt.second == 0).all()):
            return "minuto"
        return "segundo"

    def _quebras_calendario(self, d: pd.Series) -> dict[str, Any]:
        """Rebase do Spark, lacuna gregoriana e limites do dtype (§4.1)."""
        corte = pd.Timestamp(CORTE_GREGORIANO)
        l0, l1 = pd.Timestamp(LACUNA_GREGORIANA[0]), pd.Timestamp(LACUNA_GREGORIANA[1])
        try:
            antes_corte = int((d < corte).sum())
            na_lacuna = int(((d >= l0) & (d <= l1)).sum())
            fora_ns = int(
                ((d < pd.Timestamp(LIMITE_PANDAS_MIN))
                 | (d > pd.Timestamp(LIMITE_PANDAS_MAX))).sum()
            )
        except (OverflowError, pd.errors.OutOfBoundsDatetime):
            return {"nao_avaliado": "datas fora do alcance do dtype"}
        return {
            "rebase_spark": {
                "n": antes_corte,
                "criterio": f"anteriores a {CORTE_GREGORIANO}; mudam de valor entre "
                            "calendário híbrido e proléptico ao ler Parquet/Avro",
            },
            "lacuna_gregoriana": {
                "n": na_lacuna,
                "criterio": f"entre {LACUNA_GREGORIANA[0]} e {LACUNA_GREGORIANA[1]}, "
                            "dias que não existem no calendário híbrido",
            },
            "fora_datetime64_ns": {
                "n": fora_ns,
                "criterio": f"antes de {LIMITE_PANDAS_MIN} ou após {LIMITE_PANDAS_MAX}, "
                            "limites do datetime64[ns] do pandas",
            },
        }

    @staticmethod
    def _gaps(d: pd.Series, maximo: int = 5) -> list[dict[str, Any]]:
        """Maiores buracos entre observações consecutivas."""
        if d.size < 3:
            return []
        ordenadas = d.sort_values().drop_duplicates()
        difs = ordenadas.diff().dropna()
        if difs.empty:
            return []
        tipico = difs.median()
        relevantes = difs[difs > tipico * 3].nlargest(maximo)
        saida = []
        for idx, delta in relevantes.items():
            pos = ordenadas.index.get_loc(idx)
            saida.append({
                "de": ordenadas.iloc[pos - 1].isoformat(),
                "ate": ordenadas.iloc[pos].isoformat(),
                "dias": int(delta.days),
            })
        return saida

    def cyclic_profiles(self, column: str) -> dict[str, dict[Any, int]]:
        d = self._como_datas(column)
        if d.empty:
            return {}
        dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
        perfis = {
            "mes": {int(k): int(v) for k, v in d.dt.month.value_counts().sort_index().items()},
            "dia_semana": {
                dias[int(k)]: int(v)
                for k, v in d.dt.dayofweek.value_counts().sort_index().items()
            },
            "trimestre": {
                int(k): int(v) for k, v in d.dt.quarter.value_counts().sort_index().items()
            },
        }
        if self._granularidade(d) not in ("diaria", "mensal"):
            perfis["hora"] = {
                int(k): int(v) for k, v in d.dt.hour.value_counts().sort_index().items()
            }
        return perfis

    def counts_by_period(self, column: str, freq: str = "M") -> dict[str, int]:
        d = self._como_datas(column)
        if d.empty:
            return {}
        contagem = d.dt.to_period(freq).value_counts().sort_index()
        return {str(k): int(v) for k, v in contagem.items()}

    # --- textuais ---------------------------------------------------------

    def text_profile(self, column: str) -> dict[str, Any]:
        s = self._validos(column).astype(str)
        if s.empty:
            return {}
        comprimentos = s.str.len()
        n = self.config.textual_sample_size

        indices_curtos = comprimentos.nsmallest(n).index
        indices_longos = comprimentos.nlargest(n).index
        aleatorios = s.sample(min(n, len(s)), random_state=42)

        mascaras = s.head(20_000).map(mascara_caractere).value_counts()
        padrao, aderencia, violacoes = self._padrao_dominante(s)

        return {
            "comprimento": {
                "min": int(comprimentos.min()),
                "p25": int(comprimentos.quantile(0.25)),
                "mediana": int(comprimentos.median()),
                "p75": int(comprimentos.quantile(0.75)),
                "max": int(comprimentos.max()),
            },
            "amostras": {
                "mais_curtas": s.loc[indices_curtos].tolist(),
                "mais_longas": s.loc[indices_longos].tolist(),
                "aleatorias": aleatorios.tolist(),
            },
            "mascaras_top": [
                {"mascara": k, "n": int(v)}
                for k, v in mascaras.head(self.config.textual_mask_top_n).items()
            ],
            "padrao_dominante": {
                "tipo": padrao,
                "aderencia": aderencia,
                "amostra_violacoes": violacoes,
            },
        }

    def _padrao_dominante(
        self, s: pd.Series
    ) -> tuple[str | None, float | None, list[str]]:
        """Aderência e amostra das violações juntas — decisão de 2026-08-17:
        'contaminações devem surgir nesses relatórios'."""
        melhor, melhor_taxa = None, 0.0
        for nome, regex in PADROES_DOMINANTES:
            bateu = self._contains(s, regex)
            if bateu is None:
                continue
            taxa = float(bateu.mean())
            if taxa > melhor_taxa:
                melhor, melhor_taxa = nome, taxa
        if melhor is None or melhor_taxa < 0.5:
            return None, None, []
        regex = dict(PADROES_DOMINANTES)[melhor]
        violacoes = s[~self._contains(s, regex)]
        amostra = violacoes.head(self.config.textual_sample_size).tolist()
        return melhor, melhor_taxa, amostra

    def text_checks(self, column: str) -> list[dict[str, Any]]:
        """Roda sempre na base inteira: exatidão acima de velocidade."""
        s = self._validos(column).astype(str)
        if s.empty:
            return []
        n = len(s)
        todas = list(CHECAGENS_TEXTO) + [
            (c.nome, c.regex, c.descricao) for c in self.config.textual_extra_checks
        ]
        resultados = []
        for nome, regex, descricao in todas:
            bateu = self._contains(s, regex)
            if bateu is None:
                continue
            qtd = int(bateu.sum())
            if not qtd:
                continue
            resultados.append({
                "nome": nome,
                "descricao": descricao,
                "n": qtd,
                "pct": float(qtd / n),
                "amostra": s[bateu].head(self.config.textual_sample_size).tolist(),
            })
        return resultados

    @staticmethod
    def _contains(s: pd.Series, regex: str) -> pd.Series | None:
        """`str.contains` com fallback para o motor de regex do Python.

        No pandas 3.x as strings usam PyArrow por padrão, e o motor RE2 do
        Arrow **não suporta retrovisor** — `(.)\1{3,}` (4 caracteres iguais
        seguidos) falha lá e precisa do `re` nativo.
        """
        import warnings

        try:
            with warnings.catch_warnings():
                # grupos de captura são intencionais em algumas checagens
                warnings.simplefilter("ignore", UserWarning)
                return s.str.contains(regex, regex=True, na=False)
        except Exception:  # noqa: BLE001 — RE2 recusa; tentamos o motor Python
            try:
                padrao = re.compile(regex)
            except re.error:
                return None
            return s.map(lambda v: bool(padrao.search(v)))

    # --- identificadores --------------------------------------------------

    def identifier_summary(self, column: str) -> dict[str, Any]:
        s = self._validos(column)
        vc = s.value_counts()
        duplicados = vc[vc > 1]
        return {
            "n": int(s.size),
            "n_distinct": int(vc.size),
            "unico": bool(duplicados.empty),
            "n_colisoes": int(duplicados.size),
            "linhas_por_valor": float(s.size / vc.size) if vc.size else 0.0,
            "amostra_colisoes": [
                {"valor": self._py(k), "n": int(v)} for k, v in duplicados.head(5).items()
            ],
        }

    # --- amostragem -------------------------------------------------------

    def sample(self, columns: list[str], n: int) -> list[dict[str, Any]]:
        alvo = self.df[columns]
        if len(alvo) > n:
            alvo = alvo.sample(n, random_state=42)
        return [
            {k: self._py(v) for k, v in linha.items()}
            for linha in alvo.to_dict(orient="records")
        ]

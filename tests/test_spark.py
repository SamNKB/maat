"""Paridade entre os backends pandas e PySpark.

A promessa central do maat é "a mesma API nos dois motores" — estes testes
protegem isso. São pulados quando PySpark ou Java não estão disponíveis.

Divergência esperada e declarada: quantis no Spark são aproximados
(`approxQuantile`), então contagens derivadas deles (atípicos) podem diferir
em poucas unidades. O campo `quantile_error` reporta o erro usado.
"""

from __future__ import annotations

import os
import sys

import pytest

from conftest import FIXTURES

pyspark = pytest.importorskip("pyspark", reason="PySpark não instalado")
pytestmark = pytest.mark.spark


@pytest.fixture(scope="module")
def spark():
    """Sessão local; pula a suíte se o Java não estiver acessível."""
    from pyspark.sql import SparkSession

    for candidato in (
        os.environ.get("JAVA_HOME"),
        r"C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot",
    ):
        if candidato and os.path.exists(candidato):
            os.environ["JAVA_HOME"] = candidato
            break
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    try:
        sessao = (
            SparkSession.builder.appName("maat-testes")
            .master("local[2]")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
    except Exception as e:  # noqa: BLE001 — sem Java, pulamos
        pytest.skip(f"Spark indisponível: {type(e).__name__}")
    sessao.sparkContext.setLogLevel("ERROR")
    yield sessao
    sessao.stop()


@pytest.fixture(scope="module")
def titanic_spark(spark):
    return spark.read.csv(
        str(FIXTURES / "titanic.csv"), header=True, inferSchema=True
    )


@pytest.fixture(scope="module")
def titanic_pandas():
    from conftest import carregar_fixture

    return carregar_fixture("titanic")


def test_classificacao_identica_nos_dois_backends(titanic_spark, titanic_pandas):
    """A promessa central: mesma API, mesma classificação."""
    import maat

    pandas_schema = maat.describe(titanic_pandas).schema
    spark_schema = maat.describe(titanic_spark).schema

    assert set(pandas_schema) == set(spark_schema)
    for coluna, vt_pandas in pandas_schema.items():
        vt_spark = spark_schema[coluna]
        assert vt_spark.var_class is vt_pandas.var_class, coluna
        assert vt_spark.subtype is vt_pandas.subtype, coluna
        assert vt_spark.regime is vt_pandas.regime, coluna


def test_narrativa_identica_nos_dois_backends(titanic_spark, titanic_pandas):
    """Contagens exatas: a prosa tem que sair igual."""
    import maat

    p = maat.describe(titanic_pandas)
    s = maat.describe(titanic_spark)
    assert p["Survived"].narrative == s["Survived"].narrative
    assert p["SibSp"].narrative == s["SibSp"].narrative


def test_spark_reporta_erro_do_quantil(titanic_spark):
    """§0.4: aproximação declarada, nunca escondida."""
    import maat

    perfil = maat.describe(titanic_spark)["Fare"]
    assert perfil.quality["quantile_error"] > 0


def test_pandas_reporta_quantil_exato(titanic_pandas):
    import maat

    perfil = maat.describe(titanic_pandas)["Fare"]
    assert perfil.quality["quantile_error"] == 0.0


def test_spark_gera_os_quatro_formatos(titanic_spark):
    import json

    import maat

    perfil = maat.describe(titanic_spark)
    assert json.loads(perfil.to_json())
    assert perfil.to_markdown().startswith("# Perfil de dados")
    assert perfil.to_html().startswith("<!DOCTYPE html>")


def test_spark_tolera_data_malformada(spark):
    """Spark 4 usa modo ANSI: `to_timestamp` levantaria exceção em vez de
    devolver NULL. O backend usa `try_to_timestamp`."""
    import maat

    df = spark.createDataFrame(
        [("12/1/2010 8:26",), ("13/25/2010 9:00",), ("lixo",)], ["quando"]
    )
    perfil = maat.describe(df)  # não pode levantar
    assert "quando" in perfil.columns

"""Mede o custo real da bateria de checagens do regime textual (§2.4).

A pergunta que motivou: a bateria fica computacionalmente cara? Medimos em
dados reais do benchmark em vez de especular.

Uso: python scripts/custo_bateria_textual.py
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

DS = Path(__file__).resolve().parent.parent / "datasets"

# (nome, regex, descrição) — todas vetorizadas via str.contains, uma passada cada.
CHECAGENS: list[tuple[str, str, str]] = [
    ("espaco_borda", r"^\s|\s$", "espaço no início ou fim"),
    ("espaco_duplo", r"\s{2,}", "espaços consecutivos"),
    ("invisivel", r"[​-‏  ‪-‮﻿\xa0]", "zero-width, NBSP, BOM"),
    ("nao_imprimivel", r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "controle / lixo binário"),
    ("repeticao", r"(.)\1{3,}", "4+ caracteres iguais seguidos"),
    ("mojibake", r"Ã[\x80-\xbf]|â€|Â[\x80-\xbf]", "dupla codificação UTF-8/Latin-1"),
    ("html_residual", r"&[a-z]{2,6};|<[a-z/][^>]{0,40}>", "entidade ou tag HTML"),
    ("url", r"https?://|www\.[a-z0-9-]+\.", "URL embutida"),
    ("markdown", r"\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|^#{1,6}\s|```", "sintaxe markdown"),
    ("pix_brcode", r"br\.gov\.bcb\.pix|^000201.*6304[0-9A-Fa-f]{4}$", "payload PIX copia-e-cola"),
    ("base64_longo", r"[A-Za-z0-9+/]{60,}={0,2}", "possível payload codificado"),
    ("json_embutido", r'^\s*[\{\[].*[\}\]]\s*$', "JSON/lista dentro da célula"),
    ("cpf_cnpj_mascara", r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "CPF/CNPJ mascarado"),
    ("placeholder", r"(?i)^\s*(teste?|test|asd+|qwe+|x{3,}|abc+|123123|0{3,}|n/?a|nao se aplica|sem informa|nenhum|vazio|null|none|-{2,}|\.{2,})\s*$", "preenchimento de teste ou vazio disfarçado"),
    ("misto_alfabeto", r"(?=.*[a-zA-Z])(?=.*[Ѐ-ӿͰ-Ͽ])", "latino + cirílico/grego"),
]


def rodar(nome: str, serie: pd.Series) -> None:
    s = serie.dropna().astype(str)
    n = len(s)
    print(f"\n== {nome}: {n:,} strings".replace(",", "."))

    t0 = time.perf_counter()
    achados = {}
    for chave, padrao, _ in CHECAGENS:
        achados[chave] = int(s.str.contains(padrao, regex=True, na=False).sum())
    t_bateria = time.perf_counter() - t0

    t0 = time.perf_counter()
    mascara = (s.str.replace(r"[a-záàâãéêíóôõúüç]", "a", regex=True)
                .str.replace(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]", "A", regex=True)
                .str.replace(r"\d", "9", regex=True))
    top_mascaras = mascara.value_counts().head(3)
    t_mascara = time.perf_counter() - t0

    t0 = time.perf_counter()
    comp = s.str.len()
    _ = (s.iloc[comp.nsmallest(5).index.map(s.index.get_loc)],
         s.iloc[comp.nlargest(5).index.map(s.index.get_loc)],
         s.sample(min(5, n), random_state=42))
    t_amostras = time.perf_counter() - t0

    disparou = {k: v for k, v in achados.items() if v}
    print(f"   bateria de {len(CHECAGENS)} regex: {t_bateria*1000:7.0f} ms "
          f"({t_bateria/n*1e6:.2f} µs por string)")
    print(f"   máscara de caractere:       {t_mascara*1000:7.0f} ms")
    print(f"   amostras dirigidas:         {t_amostras*1000:7.0f} ms")
    print(f"   checagens que dispararam: {disparou if disparou else 'nenhuma'}")
    print(f"   top máscaras: {dict(top_mascaras)}")


def main() -> None:
    nyc = pd.read_csv(DS / "nyc-airbnb" / "AB_NYC_2019.csv")
    rodar("nyc-airbnb / name", nyc["name"])

    sms = pd.read_csv(DS / "sms-spam" / "spam.csv", encoding="latin-1")
    rodar("sms-spam / mensagem", sms[sms.columns[1]])

    cam = pd.read_csv(DS / "gov-camara-cota" / "Ano-2025.csv", sep=";", low_memory=False)
    rodar("gov-camara-cota / txtFornecedor", cam["txtFornecedor"])

    play = pd.read_csv(DS / "google-play" / "googleplaystore.csv")
    rodar("google-play / App", play["App"])

    # escala: repete a maior coluna ate ~2 milhoes de strings
    grande = pd.concat([cam["txtFornecedor"].dropna()] * 10, ignore_index=True)
    rodar("escala simulada (fornecedor x10)", grande)


if __name__ == "__main__":
    main()

"""Gera um explorador navegável do repositório, na identidade visual do maat.

Lê os arquivos versionados (`git ls-files`), monta a árvore de diretórios e
embute o conteúdo de cada um numa página HTML autocontida: árvore à esquerda,
arquivo à direita, com tamanho, nº de linhas e o último commit que o tocou.

Uso: python scripts/gera_explorador.py
Saída: explorador.html (na raiz, fora do git — regenere quando quiser)
"""

from __future__ import annotations

import html
import json
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "explorador.html"
LIMITE_BYTES = 400_000  # arquivos maiores entram só com metadados

LINGUAGEM = {
    ".py": "python", ".md": "markdown", ".html": "html", ".css": "css",
    ".toml": "toml", ".svg": "svg", ".json": "json", ".txt": "texto",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout


def ultimos_commits() -> dict[str, dict]:
    """Último commit que tocou cada arquivo, numa passada só pelo log."""
    bruto = git("log", "--pretty=format:\x01%h\x02%ad\x02%s", "--date=short", "--name-only")
    visto: dict[str, dict] = {}
    atual: dict | None = None
    for linha in bruto.splitlines():
        if linha.startswith("\x01"):
            h, data, assunto = linha[1:].split("\x02", 2)
            atual = {"hash": h, "data": data, "assunto": assunto}
        elif linha.strip() and atual and linha not in visto:
            visto[linha] = atual
    return visto


def main() -> int:
    arquivos = [a for a in git("ls-files").splitlines() if a.strip()]
    commits = ultimos_commits()
    total_commits = len(git("log", "--oneline").splitlines())

    dados: dict[str, dict] = {}
    for rel in arquivos:
        caminho = RAIZ / rel
        if not caminho.exists():
            continue
        tamanho = caminho.stat().st_size
        info = {
            "bytes": tamanho,
            "linguagem": LINGUAGEM.get(caminho.suffix, caminho.suffix.lstrip(".") or "—"),
            "commit": commits.get(rel, {}),
        }
        if tamanho <= LIMITE_BYTES:
            try:
                texto = caminho.read_text(encoding="utf-8")
                info["linhas"] = texto.count("\n") + 1
                info["conteudo"] = texto
            except UnicodeDecodeError:
                info["conteudo"] = None
        else:
            info["conteudo"] = None
        dados[rel] = info

    bytes_totais = sum(d["bytes"] for d in dados.values())
    linhas_totais = sum(d.get("linhas", 0) for d in dados.values())

    # O conteúdo embutido inclui páginas HTML: um "</script>" literal fecharia
    # o bloco antes da hora. U+2028/2029 também quebram o parser de JS.
    embutido = (
        json.dumps(dados, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )

    modelo = (RAIZ / "scripts" / "_explorador_modelo.html").read_text(encoding="utf-8")
    saida = (
        modelo
        .replace("__DADOS__", embutido)
        .replace("__N_ARQUIVOS__", str(len(dados)))
        .replace("__N_COMMITS__", str(total_commits))
        .replace("__KB__", f"{bytes_totais / 1024:.0f}")
        .replace("__LINHAS__", f"{linhas_totais:,}".replace(",", "."))
        .replace("__BRANCH__", html.escape(git("branch", "--show-current").strip()))
    )
    SAIDA.write_text(saida, encoding="utf-8")
    print(f"{SAIDA}: {len(dados)} arquivos, {bytes_totais/1024:.0f} KB de código e docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

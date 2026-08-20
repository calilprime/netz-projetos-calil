# -*- coding: utf-8 -*-
"""
Prepara as ferramentas do hub nesta máquina
===========================================

Clona (ou atualiza) os repositórios das automações dentro da pasta do hub,
com os nomes que o ``hub_app.py`` procura, e instala as dependências Python.

    py preparar.py

Precisa de Git e Python instalados. Os repositórios são privados, então o
Git vai pedir suas credenciais do GitHub na primeira vez — ou use o
``gh auth login`` antes, se tiver o GitHub CLI.

O que este script NÃO faz, de propósito: criar o ``.env`` da Recompra. As
credenciais do banco da Vórtx não passam por script nem por repositório;
copie o ``.env.exemplo`` e preencha à mão.
"""

import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

ALVOS = [
    {
        "rotulo": "Recompra FIDC · Leve Saúde",
        "repo": "https://github.com/calilprime/recompra-leve-saude.git",
        "pasta": AQUI / "Recompra - Leve Saude" / "Código VS CODE",
        "requirements": True,
    },
    {
        "rotulo": "Extração FIDC · FNET",
        "repo": "https://github.com/calilprime/Extracao-Fundos-NET.git",
        "pasta": AQUI / "Extração Fundos.NET" / "Cód" / "Atual",
        "requirements": False,
    },
]


def rodar(comando, cwd=None):
    print("   $", " ".join(str(c) for c in comando))
    return subprocess.call([str(c) for c in comando], cwd=str(cwd) if cwd else None)


def main():
    if rodar(["git", "--version"]) != 0:
        print("\nGit não encontrado. Instale em https://git-scm.com/download/win")
        return 1

    problemas = []
    for alvo in ALVOS:
        print()
        print("=" * 68)
        print(f"  {alvo['rotulo']}")
        print("=" * 68)

        if (alvo["pasta"] / ".git").exists():
            print("   Já existe: atualizando com git pull.")
            if rodar(["git", "pull", "--ff-only"], cwd=alvo["pasta"]) != 0:
                problemas.append(f"{alvo['rotulo']}: git pull falhou")
        else:
            alvo["pasta"].parent.mkdir(parents=True, exist_ok=True)
            if rodar(["git", "clone", alvo["repo"], alvo["pasta"]]) != 0:
                problemas.append(f"{alvo['rotulo']}: git clone falhou")
                continue

        if alvo["requirements"] and (alvo["pasta"] / "requirements.txt").exists():
            print("   Instalando dependências…")
            if rodar([sys.executable, "-m", "pip", "install", "-r",
                      "requirements.txt"], cwd=alvo["pasta"]) != 0:
                problemas.append(f"{alvo['rotulo']}: pip install falhou")

    print()
    print("=" * 68)
    if problemas:
        print("  Terminou com pendências:")
        for p in problemas:
            print("   ·", p)
    else:
        print("  Tudo pronto.")
    print()
    print("  Falta ainda, só para a Recompra:")
    print("   1. copiar '.env.exemplo' para '.env' e preencher as credenciais;")
    print("   2. colocar o template oficial em 'templates/';")
    print("   3. na primeira vez, rodar 'Popular o histórico' na tela.")
    print()
    print("  Para abrir: duplo clique em 'Abrir Ferramentas Netz.bat'")
    print("=" * 68)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

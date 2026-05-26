#!/usr/bin/env python3
"""
Agente PRADA — Projeto de Regularização Ambiental (MT)
Powered by Claude + SIMCAR-MT Flow

Uso:
    python main.py [diretorio]
    python main.py C:\projetos\fazenda-rio-verde

Variáveis de ambiente:
    ANTHROPIC_API_KEY  — obrigatória
    PRADA_MODEL        — modelo Claude a usar (padrão: claude-sonnet-4-6)
"""

import sys
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def verificar_dependencias():
    ausentes = []
    for pkg in ["anthropic", "requests", "rich"]:
        try:
            __import__(pkg)
        except ImportError:
            ausentes.append(pkg)
    if ausentes:
        console.print(f"[red]Dependências ausentes: {', '.join(ausentes)}[/red]")
        console.print("Execute: pip install -r requirements.txt")
        sys.exit(1)


def main():
    verificar_dependencias()

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]Variável ANTHROPIC_API_KEY não definida.[/red]")
        console.print("Defina com: set ANTHROPIC_API_KEY=sua-chave")
        sys.exit(1)

    from agent import PRADAAgent

    console.print(
        Panel(
            "[bold green]AGENTE PRADA — Projeto de Regularização Ambiental MT[/bold green]\n"
            "[dim]Fluxo SIMCAR-MT · 8 Abas · Human-in-the-Loop[/dim]",
            border_style="green",
            padding=(1, 4)
        )
    )

    # Diretório de trabalho
    if len(sys.argv) > 1:
        diretorio = sys.argv[1]
    else:
        console.print("\n[bold]Diretório de trabalho[/bold] (Enter = diretório atual): ", end="")
        entrada = input().strip()
        diretorio = entrada if entrada else "."

    diretorio = str(Path(diretorio).resolve())

    if not Path(diretorio).exists():
        console.print(f"[red]Diretório não encontrado: {diretorio}[/red]")
        sys.exit(1)

    console.print(f"\n[dim]Diretório: {diretorio}[/dim]")
    console.print(f"[dim]Modelo   : {os.getenv('PRADA_MODEL', 'claude-sonnet-4-6')}[/dim]\n")

    agente = PRADAAgent()
    agente.executar(diretorio)


if __name__ == "__main__":
    main()

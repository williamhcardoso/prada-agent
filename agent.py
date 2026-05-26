"""
Agente PRADA — loop principal com Anthropic SDK.
Executa o fluxo de 8 abas do SIMCAR-MT com tool use e Human-in-the-Loop.
"""

import json
import os
from pathlib import Path

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from tools import TOOL_DEFINITIONS, execute_tool

console = Console()

PROMPT_PATH = Path(__file__).parent.parent / "Downloads" / "gemini-code-1779741641022.md"

MODEL = os.getenv("PRADA_MODEL", "claude-sonnet-4-6")


def _load_system_prompt() -> str:
    base = ""
    if PROMPT_PATH.exists():
        base = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        console.print(
            f"[yellow]Aviso: prompt base não encontrado em {PROMPT_PATH}. "
            "Usando prompt mínimo.[/yellow]"
        )

    ferramentas = """
---

# FERRAMENTAS DISPONÍVEIS (USE ESTAS — não invente dados)

| Ferramenta | Quando usar |
|---|---|
| `ler_arquivos_projeto` | Primeiro passo: escaneia diretório por .shp e .pdf |
| `ler_shapefile` | Lê geometrias, IDs de polígonos e centroide |
| `ler_pdf_simcar` | Extrai dados cadastrais e quadro de áreas do relatório SIMCAR |
| `consultar_mapbiomas_alerta` | Marco temporal e tipologia do desmatamento |
| `consultar_gbif` | Lista de espécies nativas no raio de 50km |
| `consultar_flora_brasil` | Hábito e grupo sucessional de cada espécie |
| `salvar_draft` | Salva prada_draft.json (obrigatório antes do documento final) |
| `ler_draft` | Lê o draft atual para verificação |
| `pausar_para_revisao` | HITL — exibe resumo e aguarda confirmação do usuário |
| `gerar_documento_final` | Gera PRADA.md após confirmação do usuário |

## REGRAS DE EXECUÇÃO
1. Execute as ferramentas na ordem lógica das 8 abas do SIMCAR.
2. Se uma API retornar erro ou timeout, registre no draft e PAUSE para informar o usuário.
3. NUNCA invente espécies, dados cadastrais ou datas de desmatamento.
4. Sempre chame `salvar_draft` antes de `pausar_para_revisao`.
5. Só chame `gerar_documento_final` após a confirmação explícita do usuário.
"""
    return base + ferramentas


class PRADAAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.messages: list = []
        self.system_prompt = _load_system_prompt()
        self.diretorio = "."
        self._aguardando_hitl = False

    def executar(self, diretorio: str):
        self.diretorio = diretorio
        self.messages.append({
            "role": "user",
            "content": (
                f"Inicie o projeto PRADA para o diretório: {diretorio}\n"
                "Siga o fluxo completo das 8 abas do SIMCAR-MT conforme as instruções."
            )
        })
        self._loop()

    def _loop(self):
        while True:
            console.print("\n[dim]Consultando agente...[/dim]")

            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=8096,
                    system=[
                        {
                            "type": "text",
                            "text": self.system_prompt,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                    tools=TOOL_DEFINITIONS,
                    messages=self.messages
                )
            except anthropic.APIError as e:
                console.print(f"[red]Erro na API Anthropic: {e}[/red]")
                break

            # Adiciona resposta do assistente ao histórico
            self.messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Exibe blocos de texto
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    console.print(f"\n{block.text}")

            if response.stop_reason == "end_turn":
                console.print(
                    Panel(
                        "[green]Agente PRADA concluiu a execução.[/green]",
                        border_style="green"
                    )
                )
                break

            if response.stop_reason == "tool_use":
                tool_results = self._executar_ferramentas(response.content)
                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })

    def _executar_ferramentas(self, content_blocks) -> list:
        """Executa as ferramentas solicitadas e retorna os resultados."""
        results = []

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            console.print(
                f"\n[cyan]⚙  {block.name}[/cyan]"
                + (f" → {list(block.input.keys())}" if block.input else "")
            )

            # HITL: pausar_para_revisao precisa de input do usuário
            if block.name == "pausar_para_revisao":
                result = execute_tool(block.name, block.input, self.diretorio)
                user_input = self._coletar_resposta_usuario()
                result["resposta_usuario"] = user_input
            else:
                result = execute_tool(block.name, block.input, self.diretorio)

            # Exibe erros ou avisos relevantes
            if "erro" in result:
                console.print(f"  [red]✗ Erro: {result['erro']}[/red]")
                if "instrucao" in result:
                    console.print(f"  [yellow]→ {result['instrucao']}[/yellow]")
            else:
                console.print(f"  [green]✓ OK[/green]")

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False, default=str)
            })

        return results

    def _coletar_resposta_usuario(self) -> str:
        """Lê a resposta do usuário no terminal (HITL)."""
        console.print("\n[bold]Sua resposta:[/bold] ", end="")
        try:
            return input().strip()
        except (EOFError, KeyboardInterrupt):
            return "cancelar"

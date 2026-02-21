# CLI principal do assistente (REPL interativo + ingestão de docs).

from __future__ import annotations

import argparse
import uuid

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.config import DATA_DIR, logger
from src.core.graph import build_graph
from src.core.llm_factory import LLMFactory
from src.utils.vector_store import VectorManager

console = Console()


def _ingest_documents(vector_manager: VectorManager) -> None:
    """Ingere todos os arquivos da pasta ``data/``."""
    if not DATA_DIR.exists() or not any(DATA_DIR.iterdir()):
        console.print(
            "[yellow][!] Pasta 'data/' vazia ou inexistente. "
            "Adicione seus .pdf, .md ou .txt e rode novamente com --ingest.[/yellow]"
        )
        return
    total = vector_manager.ingest_directory(DATA_DIR)
    console.print(f"[green][OK] {total} chunks ingeridos com sucesso no Qdrant.[/green]")


def _print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]ABI Smart Assistant[/bold cyan]\n[dim]Digite sua pergunta ou 'sair' para encerrar.[/dim]",
            border_style="cyan",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ABI Smart Assistant")
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest documents from data/ before starting the REPL.",
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Ingest documents and exit (no REPL).",
    )
    args = parser.parse_args()

    console.print("[dim]Inicializando componentes…[/dim]")
    factory = LLMFactory()
    vectors = VectorManager()

    if args.ingest or args.ingest_only:
        _ingest_documents(vectors)
        if args.ingest_only:
            console.print("[green]Ingestão finalizada. Encerrando.[/green]")
            return

    graph = build_graph(llm_factory=factory, vector_manager=vectors)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    _print_banner()

    while True:
        try:
            question = console.input("\n[bold green]Você:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Até logo![/dim]")
            break

        if not question:
            continue
        if question.lower() in {"sair", "exit", "quit", "q"}:
            console.print("[dim]Até logo![/dim]")
            break

        initial_state = {
            "question": question,
            "compliance_approved": False,
            "compliance_reason": "",
            "route": "",
            "needs_rag": False,
            "documents": [],
            "answer": "",
            "steps_taken": [],
            "sources_cited": [],
            "validation_passed": None,
            "validation_notes": "",
        }

        try:
            result = graph.invoke(initial_state, config=config)
        except Exception as exc:
            logger.error("Pipeline error: %s", exc, exc_info=True)
            console.print(f"[red][ERROR] Erro no pipeline: {exc}[/red]")
            continue

        answer = result.get("answer", "Sem resposta.")
        steps = result.get("steps_taken", [])

        console.print()
        console.print(
            Panel(
                Markdown(answer),
                title="[bold cyan]Assistente ABI[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print(f"[dim]Fluxo: {' → '.join(steps)}[/dim]")


if __name__ == "__main__":
    main()

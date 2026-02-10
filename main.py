# src/main.py
"""
Sena Entry Point

Handles CLI arguments and initializes the appropriate mode:
- CLI Mode: Rich terminal interface
- Test Mode: Full system with debug UI
- Normal Mode: Production mode (TBD)
"""

import asyncio
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.bootstrapper import Bootstrapper
from src.core.sena import Sena
from src.utils.logger import setup_logger, logger

# Initialize Rich console
console = Console()

# CLI App
app = typer.Typer(
    name="sena",
    help="Sena - Self-Evolving AI Assistant",
    add_completion=False,
    rich_markup_mode="rich",
)


class RunMode(str, Enum):
    """Available run modes for Sena."""
    CLI = "cli"
    TEST = "test"
    NORMAL = "normal"


def display_banner() -> None:
    """Display the Sena startup banner."""
    banner_text = Text()
    banner_text.append("╔═══════════════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("║                                                           ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("███████╗███████╗███╗   ██╗ █████╗ ", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("██╔════╝██╔════╝████╗  ██║██╔══██╗", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("███████╗█████╗  ██╔██╗ ██║███████║", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("╚════██║██╔══╝  ██║╚██╗██║██╔══██║", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("███████║███████╗██║ ╚████║██║  ██║", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝", style="bold white")
    banner_text.append("                  ║\n", style="bold cyan")
    banner_text.append("║                                                           ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("Self-Evolving AI Assistant", style="bold magenta")
    banner_text.append("                            ║\n", style="bold cyan")
    banner_text.append("║   ", style="bold cyan")
    banner_text.append("Version 1.0.0", style="dim white")
    banner_text.append("                                          ║\n", style="bold cyan")
    banner_text.append("╚═══════════════════════════════════════════════════════════╝", style="bold cyan")
    
    console.print(banner_text)
    console.print()


async def run_bootstrap(verbose: bool = False) -> bool:
    """
    Run bootstrapper checks.
    
    Args:
        verbose: Whether to show detailed output
        
    Returns:
        True if all checks pass, False otherwise
    """
    bootstrapper = Bootstrapper(verbose=verbose)
    return await bootstrapper.run()


async def run_cli_mode() -> None:
    """Run Sena in CLI mode with rich terminal interface."""
    from src.ui.cli.interface import CLIInterface
    
    interface = CLIInterface()
    await interface.run()


async def run_test_mode() -> None:
    """Run Sena in test mode with debug UI."""
    import subprocess
    import webbrowser
    from src.api.server import start_server
    
    console.print("[bold yellow]Starting Sena in Test Mode...[/bold yellow]")
    console.print("[dim]This will start the API server and open Behind-The-Sena debug UI[/dim]")
    console.print()
    
    # Start Behind-The-Sena UI in background
    ui_path = Path(__file__).parent / "ui" / "behind-the-sena"
    if ui_path.exists():
        console.print("[cyan]Starting Behind-The-Sena UI...[/cyan]")
        # Start npm dev server in background
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=ui_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        # Open browser after a short delay
        await asyncio.sleep(2)
        webbrowser.open("http://localhost:3000")
    
    # Start API server (blocking)
    console.print("[cyan]Starting API server on http://localhost:8000[/cyan]")
    await start_server()


async def run_normal_mode() -> None:
    """Run Sena in normal production mode."""
    console.print("[bold yellow]Normal mode is not yet implemented.[/bold yellow]")
    console.print("[dim]Please use --cli or --test mode for now.[/dim]")


@app.command()
def main(
    cli: bool = typer.Option(False, "--cli", "-c", help="Run in CLI mode with rich terminal interface"),
    test: bool = typer.Option(False, "--test", "-t", help="Run in test mode with debug UI"),
    bootstrap: bool = typer.Option(False, "--bootstrap", "-b", help="Run bootstrapper checks only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    skip_bootstrap: bool = typer.Option(False, "--skip-bootstrap", help="Skip bootstrap checks on startup"),
) -> None:
    """
    Sena - Self-Evolving AI Assistant
    
    Run Sena in different modes:
    
    \b
    • CLI Mode (--cli): Rich terminal interface for direct interaction
    • Test Mode (--test): Full system with Behind-The-Sena debug UI
    • Bootstrap (--bootstrap): Run system checks without starting Sena
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(level=log_level)
    
    # Display banner
    display_banner()
    
    # Determine run mode
    if bootstrap:
        # Run bootstrap only
        console.print("[bold cyan]Running Bootstrap Checks...[/bold cyan]\n")
        success = asyncio.run(run_bootstrap(verbose=verbose))
        if success:
            console.print("\n[bold green]✓ All bootstrap checks passed![/bold green]")
            raise typer.Exit(0)
        else:
            console.print("\n[bold red]✗ Some bootstrap checks failed.[/bold red]")
            raise typer.Exit(1)
    
    # Run bootstrap checks before starting (unless skipped)
    if not skip_bootstrap:
        console.print("[bold cyan]Running Bootstrap Checks...[/bold cyan]\n")
        success = asyncio.run(run_bootstrap(verbose=verbose))
        if not success:
            console.print("\n[bold red]✗ Bootstrap checks failed. Use --skip-bootstrap to bypass.[/bold red]")
            raise typer.Exit(1)
        console.print("\n[bold green]✓ Bootstrap checks passed![/bold green]\n")
    
    # Run in appropriate mode
    if cli:
        console.print("[bold green]Starting Sena in CLI Mode...[/bold green]\n")
        asyncio.run(run_cli_mode())
    elif test:
        console.print("[bold green]Starting Sena in Test Mode...[/bold green]\n")
        asyncio.run(run_test_mode())
    else:
        # Default to CLI mode for now
        console.print("[bold yellow]No mode specified. Defaulting to CLI mode.[/bold yellow]")
        console.print("[dim]Use --help to see available options.[/dim]\n")
        asyncio.run(run_cli_mode())


if __name__ == "__main__":
    app()
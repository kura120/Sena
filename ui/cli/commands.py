# src/ui/cli/commands.py
"""
CLI Command Handlers

Additional command implementations for the CLI interface.
"""

from typing import Any, Callable, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class CommandRegistry:
    """Registry for CLI commands."""
    
    def __init__(self):
        self._commands: dict[str, Callable] = {}
        self._aliases: dict[str, str] = {}
        self._help_texts: dict[str, str] = {}
    
    def register(
        self,
        name: str,
        handler: Callable,
        help_text: str = "",
        aliases: Optional[list[str]] = None,
    ) -> None:
        """Register a command."""
        self._commands[name] = handler
        self._help_texts[name] = help_text
        
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name
    
    def get_handler(self, command: str) -> Optional[Callable]:
        """Get handler for a command."""
        # Check aliases first
        if command in self._aliases:
            command = self._aliases[command]
        
        return self._commands.get(command)
    
    def get_all_commands(self) -> dict[str, str]:
        """Get all commands with help texts."""
        return self._help_texts.copy()


# Default command registry
default_registry = CommandRegistry()


def register_default_commands() -> CommandRegistry:
    """Register default CLI commands."""
    registry = CommandRegistry()
    
    registry.register(
        "help",
        cmd_help,
        "Show available commands",
        aliases=["h", "?"],
    )
    
    registry.register(
        "quit",
        cmd_quit,
        "Exit the CLI",
        aliases=["q", "exit"],
    )
    
    registry.register(
        "clear",
        cmd_clear,
        "Clear the screen",
        aliases=["cls"],
    )
    
    registry.register(
        "stats",
        cmd_stats,
        "Show session statistics",
    )
    
    registry.register(
        "history",
        cmd_history,
        "Show conversation history",
    )
    
    registry.register(
        "models",
        cmd_models,
        "List available models",
    )
    
    registry.register(
        "extensions",
        cmd_extensions,
        "List loaded extensions",
    )
    
    registry.register(
        "memory",
        cmd_memory,
        "Manage memory system",
    )
    
    registry.register(
        "debug",
        cmd_debug,
        "Toggle debug mode",
    )
    
    return registry


async def cmd_help(ctx: Any, args: str) -> None:
    """Display help information."""
    table = Table(title="Sena CLI Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description")
    
    commands = [
        ("/help", "Show this help message"),
        ("/quit", "Exit Sena CLI"),
        ("/clear", "Clear the screen"),
        ("/stats", "Show session statistics"),
        ("/history [n]", "Show last n messages (default: 10)"),
        ("/models", "List available LLM models"),
        ("/extensions", "List loaded extensions"),
        ("/memory", "Show memory system status"),
        ("/memory clear", "Clear short-term memory"),
        ("/memory search <query>", "Search memories"),
        ("/debug", "Toggle debug mode"),
        ("/stream <message>", "Chat with streaming response"),
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)
    console.print()
    console.print("[dim]You can also just type your message to chat with Sena.[/dim]")


async def cmd_quit(ctx: Any, args: str) -> None:
    """Quit command handler."""
    console.print("[yellow]Goodbye![/yellow]")
    ctx._running = False


async def cmd_clear(ctx: Any, args: str) -> None:
    """Clear screen command handler."""
    console.clear()


async def cmd_stats(ctx: Any, args: str) -> None:
    """Show statistics command handler."""
    if not ctx.sena:
        console.print("[yellow]Sena not initialized[/yellow]")
        return
    
    stats = ctx.sena.get_stats()
    
    table = Table(title="Session Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("Session ID", stats.get("session_id", "N/A"))
    table.add_row("Messages Processed", str(stats.get("message_count", 0)))
    table.add_row("Status", "✓ Active" if stats.get("initialized") else "✗ Inactive")
    
    console.print(table)


async def cmd_history(ctx: Any, args: str) -> None:
    """Show conversation history."""
    if not ctx.sena:
        console.print("[yellow]Sena not initialized[/yellow]")
        return
    
    try:
        limit = int(args) if args else 10
    except ValueError:
        limit = 10
    
    history = await ctx.sena.get_conversation_history(limit=limit)
    
    if not history:
        console.print("[dim]No conversation history yet[/dim]")
        return
    
    for conv in reversed(history):
        console.print(f"[cyan]You:[/cyan] {conv.user_input[:100]}...")
        console.print(f"[green]Sena:[/green] {conv.sena_response[:100]}...")
        console.print(f"[dim]({conv.timestamp.strftime('%H:%M:%S')})[/dim]")
        console.print()


async def cmd_models(ctx: Any, args: str) -> None:
    """List available models."""
    console.print("[dim]Model listing not yet implemented[/dim]")


async def cmd_extensions(ctx: Any, args: str) -> None:
    """List loaded extensions."""
    console.print("[dim]Extension listing not yet implemented[/dim]")


async def cmd_memory(ctx: Any, args: str) -> None:
    """Memory management command."""
    if not args:
        # Show memory status
        console.print("[dim]Memory status not yet implemented[/dim]")
        return
    
    subcommand = args.split()[0].lower()
    
    if subcommand == "clear":
        if ctx.sena:
            await ctx.sena.clear_short_term_memory()
            console.print("[green]✓ Short-term memory cleared[/green]")
    elif subcommand == "search":
        query = " ".join(args.split()[1:])
        if query:
            console.print(f"[dim]Searching for: {query}[/dim]")
            # TODO: Implement memory search
        else:
            console.print("[yellow]Usage: /memory search <query>[/yellow]")
    else:
        console.print(f"[yellow]Unknown memory command: {subcommand}[/yellow]")


async def cmd_debug(ctx: Any, args: str) -> None:
    """Toggle debug mode."""
    console.print("[dim]Debug mode toggle not yet implemented[/dim]")
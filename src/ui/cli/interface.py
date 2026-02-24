# src/ui/cli/interface.py
"""
Rich Terminal CLI Interface for Sena

Provides an interactive terminal interface with:
- Rich formatting and colors
- Real-time streaming
- Processing status display
- Command history
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.syntax import Syntax

from src.core.constants import ProcessingStage
from src.core.sena import Sena
from src.utils.logger import logger


console = Console()


class ProcessingStatus:
    """Tracks and displays processing status."""
    
    def __init__(self) -> None:
        self.stage = ProcessingStage.IDLE
        self.details = ""
        self.tokens: list[str] = []
        self.start_time: Optional[datetime] = None
    
    def update(self, stage: ProcessingStage, details: str = "") -> None:
        """Update the current stage."""
        self.stage = stage
        self.details = details
        
        if stage == ProcessingStage.RECEIVING:
            self.start_time = datetime.now()
            self.tokens = []
    
    def add_token(self, token: str) -> None:
        """Add a streamed token."""
        self.tokens.append(token)
    
    @property
    def response_text(self) -> str:
        """Get accumulated response text."""
        return "".join(self.tokens)
    
    def get_display(self) -> Panel:
        """Get rich display panel."""
        stage_colors = {
            ProcessingStage.IDLE: "dim",
            ProcessingStage.RECEIVING: "cyan",
            ProcessingStage.INTENT_CLASSIFICATION: "yellow",
            ProcessingStage.MEMORY_RETRIEVAL: "blue",
            ProcessingStage.EXTENSION_EXECUTION: "magenta",
            ProcessingStage.LLM_PROCESSING: "green",
            ProcessingStage.LLM_STREAMING: "green",
            ProcessingStage.POST_PROCESSING: "cyan",
            ProcessingStage.COMPLETE: "green",
            ProcessingStage.ERROR: "red",
        }
        
        color = stage_colors.get(self.stage, "white")
        
        if self.stage == ProcessingStage.LLM_STREAMING:
            # Show streaming response
            content = Text(self.response_text)
            title = f"[{color}]● Streaming Response[/{color}]"
        elif self.stage == ProcessingStage.COMPLETE:
            content = Text(f"✓ {self.details}")
            title = f"[{color}]Complete[/{color}]"
        else:
            content = Text(f"{self.stage.value}: {self.details}")
            title = f"[{color}]● Processing[/{color}]"
        
        return Panel(
            content,
            title=title,
            border_style=color,
        )


class CLIInterface:
    """
    Rich CLI interface for Sena.
    
    Provides interactive chat with real-time feedback.
    """
    
    def __init__(self) -> None:
        self.sena: Optional[Sena] = None
        self.status = ProcessingStatus()
        self._running = False
        self._command_history: list[str] = []
    
    async def run(self) -> None:
        """Run the CLI interface."""
        self._running = True
        
        # Display welcome message
        self._display_welcome()
        
        # Initialize Sena
        await self._initialize_sena()
        
        if not self.sena or not self.sena.is_initialized:
            console.print("[red]Failed to initialize Sena. Exiting.[/red]")
            return
        
        # Main loop
        try:
            await self._main_loop()
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        finally:
            await self._shutdown()
    
    def _display_welcome(self) -> None:
        """Display welcome message."""
        welcome = Panel(
            Text.from_markup(
                "[bold cyan]Welcome to Sena CLI[/bold cyan]\n\n"
                "Type your message and press Enter to chat.\n"
                "Type [bold]/help[/bold] for commands or [bold]/quit[/bold] to exit.\n\n"
                "[dim]Tip: Use /stream for streaming mode[/dim]"
            ),
            title="[bold magenta]Sena[/bold magenta]",
            subtitle="[dim]Self-Evolving AI Assistant[/dim]",
            border_style="cyan",
        )
        console.print(welcome)
        console.print()
    
    async def _initialize_sena(self) -> None:
        """Initialize Sena with loading animation."""
        with console.status("[cyan]Initializing Sena...[/cyan]", spinner="dots"):
            try:
                self.sena = Sena()
                
                # Set up callbacks
                self.sena.set_stage_callback(self._on_stage_change)
                self.sena.set_token_callback(self._on_token)
                
                await self.sena.initialize()
                
                console.print("[green]✓ Sena initialized successfully[/green]\n")
                
            except Exception as e:
                console.print(f"[red]✗ Initialization failed: {e}[/red]\n")
                logger.error(f"CLI initialization error: {e}")
    
    async def _main_loop(self) -> None:
        """Main interaction loop."""
        while self._running:
            try:
                # Get user input
                user_input = await self._get_input()
                
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue
                
                # Add to history
                self._command_history.append(user_input)
                
                # Process message
                await self._process_message(user_input)
                
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"CLI loop error: {e}")
    
    async def _get_input(self) -> str:
        """Get user input with prompt."""
        try:
            # Run in thread to not block
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(
                None,
                lambda: Prompt.ask("\n[bold cyan]You[/bold cyan]")
            )
            return user_input.strip()
        except KeyboardInterrupt:
            return "/quit"
    
    async def _handle_command(self, command: str) -> None:
        """Handle CLI commands."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ("help", "h", "?"):
            await self._cmd_help(args)
        elif cmd in ("quit", "exit", "q"):
            await self._cmd_quit(args)
        elif cmd in ("clear", "cls"):
            await self._cmd_clear(args)
        elif cmd == "history":
            await self._cmd_history(args)
        elif cmd == "stats":
            await self._cmd_stats(args)
        elif cmd == "stream":
            await self._cmd_stream(args)
        elif cmd == "memory":
            await self._cmd_memory(args)
        else:
            console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            console.print("[dim]Type /help for available commands[/dim]")
    
    async def _cmd_help(self, args: str) -> None:
        """Show help."""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row("/help", "Show this help message")
        table.add_row("/quit, /exit", "Exit Sena CLI")
        table.add_row("/clear", "Clear the screen")
        table.add_row("/history", "Show command history")
        table.add_row("/stats", "Show session statistics")
        table.add_row("/stream [message]", "Process message with streaming")
        table.add_row("/memory", "Show memory status")
        
        console.print(table)
    
    async def _cmd_quit(self, args: str) -> None:
        """Quit the CLI."""
        self._running = False
        console.print("[yellow]Goodbye![/yellow]")
    
    async def _cmd_clear(self, args: str) -> None:
        """Clear the screen."""
        console.clear()
        self._display_welcome()
    
    async def _cmd_history(self, args: str) -> None:
        """Show command history."""
        if not self._command_history:
            console.print("[dim]No history yet[/dim]")
            return
        
        table = Table(title="Command History", show_header=True)
        table.add_column("#", style="dim")
        table.add_column("Message")
        
        for i, msg in enumerate(self._command_history[-20:], 1):
            display_msg = msg[:80] + ("..." if len(msg) > 80 else "")
            table.add_row(str(i), display_msg)
        
        console.print(table)
    
    async def _cmd_stats(self, args: str) -> None:
        """Show session statistics."""
        if not self.sena:
            console.print("[yellow]Sena not initialized[/yellow]")
            return
        
        stats = self.sena.get_stats()
        
        table = Table(title="Session Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        
        table.add_row("Session ID", str(stats.get("session_id", "N/A")))
        table.add_row("Messages", str(stats.get("message_count", 0)))
        table.add_row("Initialized", "✓" if stats.get("initialized") else "✗")
        
        if "llm" in stats:
            llm_stats = stats["llm"]
            if isinstance(llm_stats, dict) and "active_model" in llm_stats:
                table.add_row("Active Model", str(llm_stats["active_model"] or "None"))
        
        console.print(table)
    
    async def _cmd_stream(self, args: str) -> None:
        """Process message with streaming."""
        if not args:
            console.print("[yellow]Usage: /stream <message>[/yellow]")
            return
        
        await self._process_message(args, stream=True)
    
    async def _cmd_memory(self, args: str) -> None:
        """Show memory status."""
        console.print("[dim]Memory status not yet implemented[/dim]")
    
    async def _process_message(self, user_input: str, stream: bool = False) -> None:
        """Process a user message."""
        if not self.sena:
            console.print("[red]Sena not initialized[/red]")
            return
        
        self.status = ProcessingStatus()
        self.status.update(ProcessingStage.RECEIVING, "Processing...")
        
        try:
            if stream:
                # Streaming mode
                response_text = ""
                
                console.print()
                console.print("[bold green]Sena:[/bold green]", end=" ")
                
                async for token in self.sena.stream(user_input):
                    response_text += token
                    console.print(token, end="", markup=False)
                
                console.print()  # Newline after response
                
            else:
                # Non-streaming mode with status updates
                with console.status("[cyan]Processing...[/cyan]", spinner="dots"):
                    response = await self.sena.process(user_input)
                    
                    # Display response
                    console.print()
                    self._display_response(response.content)
                    
                    # Show timing
                    console.print(
                        f"[dim]({response.duration_ms:.0f}ms, "
                        f"model: {response.model})[/dim]"
                    )
                    
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.error(f"Processing error: {e}")
    
    def _display_response(self, content: str) -> None:
        """Display Sena's response with formatting."""
        # Check if response contains code blocks
        if "```" in content:
            # Render as markdown
            console.print("[bold green]Sena:[/bold green]")
            console.print(Markdown(content))
        else:
            # Plain text with wrapping
            console.print(Panel(
                content,
                title="[bold green]Sena[/bold green]",
                border_style="green",
                padding=(0, 1),
            ))
    
    async def _on_stage_change(self, stage: ProcessingStage, details: str = "") -> None:
        """Handle stage change callback."""
        self.status.update(stage, details)
    
    async def _on_token(self, token: str, is_final: bool = False) -> None:
        """Handle token stream callback."""
        self.status.add_token(token)
    
    async def _shutdown(self) -> None:
        """Shutdown the CLI."""
        console.print("\n[cyan]Shutting down...[/cyan]")
        
        if self.sena:
            await self.sena.shutdown()
        
        console.print("[green]Goodbye! 👋[/green]")
#!/usr/bin/env python3
"""
ShellPilot - AI-Powered Linux System Administration CLI
"""

import typer
from typing import Optional
from enum import Enum
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import print

from shellpilot import __version__
from shellpilot.config import Config, get_config
# TODO: Import these when we create the modules
# from shellpilot.ui.interactive import InteractiveSession
# from shellpilot.core.executor import CommandExecutor
# from shellpilot.utils.logger import setup_logger

# Initialize rich console
console = Console()

# Create the main CLI app
app = typer.Typer(
    name="shellpilot",
    help="🚁 ShellPilot - AI-Powered Linux System Administration",
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]}
)

class LLMProvider(str, Enum):
    """Available LLM providers"""
    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"
    gemini = "gemini"

class LogLevel(str, Enum):
    """Log levels"""
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"

def version_callback(value: bool):
    """Show version and exit"""
    if value:
        print(f"[bold green]ShellPilot[/bold green] v{__version__}")
        print("[dim]AI-Powered Linux System Administration[/dim]")
        raise typer.Exit()

@app.callback()
def common(
    version: Optional[bool] = typer.Option(
        None,
        "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    ),
):
    """ShellPilot - AI-Powered Linux System Administration"""
    pass

@app.command()
def run(
    query: str = typer.Argument(
        ...,
        help="Query or command to execute"
    ),
    provider: LLMProvider = typer.Option(
        LLMProvider.openai,
        "--provider", "-p",
        help="LLM provider to use"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Specific model to use (e.g., gpt-4, claude-3-sonnet)"
    ),
    safe_mode: bool = typer.Option(
        True,
        "--safe-mode/--unsafe",
        help="Enable safety confirmations for destructive operations"
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.info,
        "--log-level", "-l",
        help="Set logging level"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Show what would be executed without running commands"
    )
):
    """
    Execute a single query or command using AI

    Examples:
    \b
        shellpilot run "check system performance"
        shellpilot run "install nginx" --provider anthropic
        shellpilot run "clean up logs" --unsafe
        shellpilot run "show disk usage" --dry-run
    """
    # Setup logging (placeholder for now)
    # logger = setup_logger(log_level.value)
    print(f"Log level: {log_level.value}")  # Temporary placeholder

    # Show header
    console.print(Panel(
        f"[bold green]ShellPilot[/bold green] v{__version__}\n"
        f"[cyan]Provider:[/cyan] {provider.value}\n"
        f"[cyan]Safe Mode:[/cyan] {'✅ Enabled' if safe_mode else '❌ Disabled'}\n"
        f"[cyan]Dry Run:[/cyan] {'✅ Yes' if dry_run else '❌ No'}",
        title="🚁 AI System Administration",
        border_style="green"
    ))

    try:
        # Load configuration
        config = get_config()

        # TODO: Implement when we create the executor module
        console.print("[yellow]⚠️  Command execution not implemented yet![/yellow]")
        console.print(f"[dim]Would execute: {query}[/dim]")
        console.print(f"[dim]Provider: {provider.value}[/dim]")
        console.print(f"[dim]Safe mode: {safe_mode}[/dim]")
        console.print(f"[dim]Dry run: {dry_run}[/dim]")

        # # Initialize executor
        # executor = CommandExecutor(
        #     provider=provider.value,
        #     model=model,
        #     safe_mode=safe_mode,
        #     dry_run=dry_run,
        #     config=config
        # )
        #
        # # Execute query
        # result = executor.execute(query)
        #
        # # Display results
        # console.print("\n[bold green]✅ Execution completed[/bold green]")
        # if result.output:
        #     console.print(f"[dim]{result.output}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        # logger.error(f"Execution failed: {e}")  # TODO: Uncomment when logger exists
        raise typer.Exit(1)

@app.command()
def chat(
    provider: LLMProvider = typer.Option(
        LLMProvider.openai,
        "--provider", "-p",
        help="LLM provider to use"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Specific model to use"
    ),
    safe_mode: bool = typer.Option(
        True,
        "--safe-mode/--unsafe",
        help="Enable safety confirmations"
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.info,
        "--log-level", "-l",
        help="Set logging level"
    )
):
    """
    Start interactive chat session with AI

    Examples:
    \b
        shellpilot chat
        shellpilot chat --provider anthropic
        shellpilot chat --unsafe --model gpt-4
    """
    # Setup logging (placeholder for now)
    # logger = setup_logger(log_level.value)
    print(f"Log level: {log_level.value}")  # Temporary placeholder

    try:
        # Load configuration
        config = get_config()

        # TODO: Implement when we create the interactive module
        console.print("[yellow]⚠️  Interactive chat not implemented yet![/yellow]")
        console.print(f"[dim]Provider: {provider.value}[/dim]")
        console.print(f"[dim]Safe mode: {safe_mode}[/dim]")

        # # Start interactive session
        # session = InteractiveSession(
        #     provider=provider.value,
        #     model=model,
        #     safe_mode=safe_mode,
        #     config=config
        # )
        #
        # session.start()

    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        # logger.error(f"Chat session failed: {e}")  # TODO: Uncomment when logger exists
        raise typer.Exit(1)

@app.command()
def config(
    show: bool = typer.Option(
        False,
        "--show", "-s",
        help="Show current configuration"
    ),
    set_provider: Optional[LLMProvider] = typer.Option(
        None,
        "--set-provider",
        help="Set default LLM provider"
    ),
    set_model: Optional[str] = typer.Option(
        None,
        "--set-model",
        help="Set default model"
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--set-api-key",
        help="Set API key for current provider"
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset configuration to defaults"
    )
):
    """
    Manage ShellPilot configuration

    Examples:
    \b
        shellpilot config --show
        shellpilot config --set-provider anthropic
        shellpilot config --set-model gpt-4-turbo
        shellpilot config --set-api-key your-api-key
    """
    config_obj = get_config()

    if reset:
        config_obj.reset()
        console.print("[green]✅ Configuration reset to defaults[/green]")
        return

    if set_provider:
        config_obj.set_default_provider(set_provider.value)
        console.print(f"[green]✅ Default provider set to {set_provider.value}[/green]")

    if set_model:
        config_obj.set_default_model(set_model)
        console.print(f"[green]✅ Default model set to {set_model}[/green]")

    if api_key:
        provider = config_obj.get_default_provider()
        config_obj.set_api_key(provider, api_key)
        console.print(f"[green]✅ API key set for {provider}[/green]")

    if show or not any([set_provider, set_model, api_key, reset]):
        config_obj.show()

if __name__ == "__main__":
    app()
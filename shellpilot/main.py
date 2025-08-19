#!/usr/bin/env python3
"""
ShellPilot - AI-Powered Linux System Administration CLI
"""

import typer
import time
from typing import Optional
from enum import Enum
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import print
from dataclasses import dataclass, asdict   # ✅ Correct
from shellpilot import __version__
from shellpilot.config import Config, get_config
from shellpilot.core.session import get_session_store

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
    deepseek = "deepseek"
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
    provider: Optional[LLMProvider] = typer.Option(
        None,
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
    ),
    clear_context: bool = typer.Option(
        False,
        "--clear-context",
        help="Clear session context before running"
    )
):
    """
    Execute a single query or command using AI with session memory

    Examples:
    \b
        shellpilot run "check system performance"
        shellpilot run "install nginx" --provider deepseek
        shellpilot run "clean up logs" --unsafe
        shellpilot run "show disk usage" --dry-run
        shellpilot run "continue from where we left off" --clear-context
    """
    start_time = time.time()

    try:
        # Initialize session store
        session_store = get_session_store()

        # Clear context if requested
        if clear_context:
            session_store.clear_session()

        # Load configuration
        config = get_config()

        # Override config with CLI options if provided
        if provider:
            config.set_default_provider(provider.value)
        if model:
            config.set_default_model(model)

        # Get actual values from config
        actual_provider = config.get_default_provider()
        actual_model = config.get_default_model() or "default"

        # Show header with session info
        session_info = session_store.get_session_info()
        console.print(Panel(
            f"[bold green]ShellPilot[/bold green] v{__version__}\n"
            f"[cyan]Provider:[/cyan] {actual_provider}\n"
            f"[cyan]Model:[/cyan] {actual_model}\n"
            f"[cyan]Safe Mode:[/cyan] {'✅ Enabled' if safe_mode else '❌ Disabled'}\n"
            f"[cyan]Dry Run:[/cyan] {'✅ Yes' if dry_run else '❌ No'}\n"
            f"[dim]Session: {session_info['session_id']} | Commands: {session_info['total_commands']}[/dim]",
            title="🚁 AI System Administration",
            border_style="green"
        ))

        # Import core modules
        from shellpilot.core.llm import LLMManager
        from shellpilot.core.executor import CommandExecutor

        # Initialize components
        llm_manager = LLMManager(config)
        executor = CommandExecutor(safe_mode=safe_mode, dry_run=dry_run)

        # Get session context for AI
        context = session_store.get_context_summary()

        # Generate commands using AI with context
        console.print(f"[cyan]🤖 Analyzing:[/cyan] {query}")
        if context and "No previous commands" not in context:
            console.print(f"[dim]📋 Using session context ({len(session_store.get_recent_commands())} recent commands)[/dim]")

        llm_response = llm_manager.generate_command(query, context if context else None)

        if not llm_response.commands:
            console.print("[yellow]No commands generated.[/yellow]")
            if llm_response.content:
                console.print(Panel(
                    llm_response.content,
                    title="🤖 AI Response",
                    border_style="yellow"
                ))

            # Still record the query attempt
            session_store.add_command(
                query=query,
                commands=[],
                success=False,
                ai_summary="No commands generated",
                execution_time=time.time() - start_time
            )
            return

        # Show AI response
        console.print(Panel(
            llm_response.content,
            title="🤖 AI Analysis",
            border_style="blue"
        ))

        # Execute commands
        console.print(f"\n[green]Generated {len(llm_response.commands)} command(s):[/green]")
        for i, cmd in enumerate(llm_response.commands, 1):
            console.print(f"  {i}. [cyan]{cmd}[/cyan]")

        results = executor.execute_multiple(llm_response.commands)

        # Calculate success
        successful = sum(1 for r in results if r.success)
        overall_success = successful == len(results)

        # Create AI summary of what was accomplished
        ai_summary = f"Executed {successful}/{len(results)} commands successfully"
        if llm_response.content:
            # Extract a brief summary from AI response (first sentence)
            first_sentence = llm_response.content.split('.')[0]
            if len(first_sentence) < 100:
                ai_summary = first_sentence.strip()

        # Record in session
        session_store.add_command(
            query=query,
            commands=llm_response.commands,
            success=overall_success,
            ai_summary=ai_summary,
            execution_time=time.time() - start_time
        )

        # Summary
        console.print(f"\n[green]✅ {successful}/{len(results)} commands executed successfully[/green]")
        console.print(f"[dim]📝 Session updated | Total commands this session: {session_store.get_session_info()['total_commands']}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)



@app.command()
def context(
    show_full: bool = typer.Option(
        False,
        "--full",
        help="Show full session history"
    ),
    clear: bool = typer.Option(
        False,
        "--clear",
        help="Clear session context"
    )
):
    """
    Show or manage session context

    Examples:
    \b
        shellpilot context              # Show recent commands
        shellpilot context --full       # Show full session history
        shellpilot context --clear      # Clear session memory
    """
    session_store = get_session_store()

    if clear:
        session_store.clear_session()
        return

    session_info = session_store.get_session_info()

    # Show session header
    console.print(Panel(
        f"[bold blue]Session Information[/bold blue]\n"
        f"[cyan]Session ID:[/cyan] {session_info['session_id']}\n"
        f"[cyan]Started:[/cyan] {session_info['start_time']}\n"
        f"[cyan]Total Commands:[/cyan] {session_info['total_commands']}\n"
        f"[cyan]Current Directory:[/cyan] {session_info['current_working_dir']}\n"
        f"[cyan]Last Updated:[/cyan] {session_info['last_updated']}",
        title="🧠 Session Context",
        border_style="blue"
    ))

    # Show command history
    recent_commands = session_store.get_recent_commands(20 if show_full else 10)

    if not recent_commands:
        console.print("[dim]No commands in session history[/dim]")
        return

    console.print(f"\n[bold]Recent Commands ({'Full History' if show_full else 'Last 10'}):[/bold]\n")

    for i, cmd in enumerate(recent_commands, 1):
        status_icon = "✅" if cmd.success else "❌"
        timestamp = cmd.timestamp.split('T')[1][:8]  # Just time portion

        console.print(f"{i:2d}. {status_icon} [{timestamp}] [cyan]{cmd.query}[/cyan]")

        # Show commands executed
        for j, command in enumerate(cmd.commands[:3]):  # Show max 3 commands
            console.print(f"    └─ [dim]{command}[/dim]")
        if len(cmd.commands) > 3:
            console.print(f"    └─ [dim]... and {len(cmd.commands) - 3} more[/dim]")

        # Show AI summary if available
        if cmd.ai_summary:
            console.print(f"    [dim italic]Summary: {cmd.ai_summary}[/dim italic]")

        console.print()  # Empty line between commands



@app.command()
def chat(
    provider: Optional[LLMProvider] = typer.Option(  # FIXED: Made optional
        None,  # FIXED: Default to None
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
        shellpilot chat --provider deepseek
        shellpilot chat --unsafe --model deepseek-chat
    """
    try:
        # Load configuration
        config = get_config()

        # Override config with CLI options if provided
        if provider:
            config.set_default_provider(provider.value)
        if model:
            config.set_default_model(model)

        console.print("[yellow]⚠️  Interactive chat not implemented yet![/yellow]")
        console.print(f"[dim]Provider: {config.get_default_provider()}[/dim]")
        console.print(f"[dim]Safe mode: {safe_mode}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
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
        shellpilot config --set-provider deepseek
        shellpilot config --set-model deepseek-chat
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
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
from dataclasses import dataclass, asdict

from shellpilot import __version__
from shellpilot.config import Config, get_config
from shellpilot.core.session import get_session_store
from shellpilot.core.workflow import WorkflowEngine

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
    ),
    workflow_mode: bool = typer.Option(
        False,
        "--workflow", "-w",
        help="Execute as intelligent multi-step workflow"
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
        shellpilot run "set up web server" --workflow
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
            f"[cyan]Workflow:[/cyan] {'🔄 Enabled' if workflow_mode else '📋 Standard'}\n"
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

        # Choose execution mode: Workflow vs Standard
        if workflow_mode or len(llm_response.commands) > 6:
            # WORKFLOW MODE for complex tasks
            console.print(f"\n[blue]🔄 Workflow Mode:[/blue] {len(llm_response.commands)} commands → Intelligent workflow")

            # Initialize workflow components
            from shellpilot.core.safety import SafetyChecker
            safety_checker = SafetyChecker(safe_mode)
            workflow_engine = WorkflowEngine(executor, safety_checker)

            # Create workflow from AI response
            workflow = workflow_engine.create_workflow_from_llm_response(
                query,
                llm_response,
                ai_plan=llm_response.content
            )

            # Execute workflow
            overall_success = workflow_engine.execute_workflow(
                workflow,
                interactive=(not dry_run and safe_mode)
            )

            # Calculate results for session tracking
            successful_steps = sum(1 for step in workflow.steps if step.status.value == "success")
            total_steps = len(workflow.steps)

        else:
            # STANDARD MODE for simple tasks
            console.print(f"\n[green]📋 Standard Mode:[/green] {len(llm_response.commands)} commands")
            for i, cmd in enumerate(llm_response.commands, 1):
                console.print(f"  {i}. [cyan]{cmd}[/cyan]")

            results = executor.execute_multiple(llm_response.commands)

            # Calculate success
            successful_steps = sum(1 for r in results if r.success)
            total_steps = len(results)
            overall_success = successful_steps == total_steps

        # Create AI summary
        mode_text = "workflow steps" if (workflow_mode or len(llm_response.commands) > 6) else "commands"
        ai_summary = f"Executed {successful_steps}/{total_steps} {mode_text} successfully"

        if llm_response.content:
            # Extract brief summary from AI response
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

        # Final summary
        mode_icon = "🔄" if (workflow_mode or len(llm_response.commands) > 6) else "📋"
        console.print(f"\n[green]✅ {successful_steps}/{total_steps} {mode_text} executed successfully[/green]")
        console.print(f"[dim]{mode_icon} Session updated | Total commands: {session_store.get_session_info()['total_commands']}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)

@app.command()
def workflow(
    query: str = typer.Argument(
        ...,
        help="Complex task to execute as intelligent workflow"
    ),
    provider: Optional[LLMProvider] = typer.Option(
        None,
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Show workflow plan without executing"
    ),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve", "-y",
        help="Auto-approve non-critical steps"
    )
):
    """
    Execute complex multi-step workflows with intelligent planning

    Examples:
    \b
        shellpilot workflow "set up NGINX with SSL certificate"
        shellpilot workflow "secure Ubuntu server" --dry-run
        shellpilot workflow "install Docker and containers" --auto-approve
        shellpilot workflow "backup and optimize system"
    """
    start_time = time.time()

    try:
        # Initialize components
        session_store = get_session_store()
        config = get_config()

        # Override config with CLI options
        if provider:
            config.set_default_provider(provider.value)
        if model:
            config.set_default_model(model)

        # Show workflow header
        console.print(Panel(
            f"[bold blue]🔄 ShellPilot Workflow Engine[/bold blue] v{__version__}\n"
            f"[cyan]Provider:[/cyan] {config.get_default_provider()}\n"
            f"[cyan]Model:[/cyan] {config.get_default_model() or 'default'}\n"
            f"[cyan]Mode:[/cyan] {'🔍 Planning' if dry_run else '⚡ Execution'}\n"
            f"[cyan]Safety:[/cyan] {'✅ Interactive' if safe_mode and not auto_approve else '🚀 Auto-approve'}",
            title="🧠 Intelligent Multi-Step Workflows",
            border_style="blue"
        ))

        # Import core modules
        from shellpilot.core.llm import LLMManager
        from shellpilot.core.executor import CommandExecutor
        from shellpilot.core.safety import SafetyChecker
        from shellpilot.core.workflow import WorkflowEngine

        # Initialize workflow system
        llm_manager = LLMManager(config)
        safety_checker = SafetyChecker(safe_mode)
        executor = CommandExecutor(safe_mode=safe_mode, dry_run=dry_run)
        workflow_engine = WorkflowEngine(executor, safety_checker)

        # Get session context
        context = session_store.get_context_summary()

        # Enhanced prompt for better workflow planning
        workflow_prompt = f"""
MULTI-STEP WORKFLOW PLANNING:

Task: {query}

Please create a comprehensive step-by-step plan for this complex task. Structure your response with clear phases:

### Step 1: [Phase Name]
Brief description of what this phase accomplishes.
```bash
command1
command2
```

### Step 2: [Phase Name]
Brief description of what this phase accomplishes.
```bash
command3
command4
```

Important considerations:
1. Break down into logical, sequential phases
2. Each step should have clear dependencies
3. Include verification commands where appropriate
4. Consider error handling and rollback scenarios
5. Use safe, standard Linux practices
6. Include explanations for complex operations

Context from recent session:
{context if context and "No previous commands" not in context else "No previous session context."}
"""

        # Generate comprehensive workflow plan
        console.print(f"[cyan]🧠 Planning multi-step workflow:[/cyan] {query}")
        console.print("[dim]Analyzing task complexity and dependencies...[/dim]")

        llm_response = llm_manager.generate_command(workflow_prompt)

        if not llm_response.commands:
            console.print("[yellow]❌ Could not generate workflow plan.[/yellow]")
            console.print("[dim]Try rephrasing your request or breaking it into smaller tasks.[/dim]")
            return

        # Show comprehensive AI analysis
        console.print(Panel(
            llm_response.content,
            title="🧠 Workflow Intelligence & Planning",
            border_style="blue"
        ))

        # Create intelligent workflow
        workflow = workflow_engine.create_workflow_from_llm_response(
            query,
            llm_response,
            ai_plan=llm_response.content
        )

        console.print(f"\n[green]🎯 Generated workflow with {len(workflow.steps)} intelligent steps[/green]")

        if dry_run:
            # DRY RUN: Show plan only
            console.print("\n[yellow]🔍 DRY RUN MODE - Workflow Plan Preview[/yellow]")
            workflow_engine._display_workflow_plan(workflow)

            console.print(f"\n[blue]💡 To execute this workflow:[/blue]")
            console.print(f"[cyan]shellpilot workflow \"{query}\"[/cyan]")

            # Record planning in session
            session_store.add_command(
                query=f"[WORKFLOW PLAN] {query}",
                commands=llm_response.commands,
                success=True,
                ai_summary=f"Planned {len(workflow.steps)} step workflow",
                execution_time=time.time() - start_time
            )
        else:
            # EXECUTE: Run the workflow
            success = workflow_engine.execute_workflow(
                workflow,
                interactive=(not auto_approve and safe_mode)
            )

            # Record execution in session
            successful_steps = sum(1 for step in workflow.steps if step.status.value == "success")
            session_store.add_command(
                query=f"[WORKFLOW] {query}",
                commands=llm_response.commands,
                success=success,
                ai_summary=f"Executed {successful_steps}/{len(workflow.steps)} workflow steps",
                execution_time=time.time() - start_time
            )

            # Final success message
            if success:
                console.print(f"\n[bold green]🎉 Workflow completed successfully![/bold green]")
                console.print(f"[green]✅ All {len(workflow.steps)} steps executed without errors[/green]")
            else:
                console.print(f"\n[yellow]⚠️  Workflow completed with some issues[/yellow]")
                console.print(f"[cyan]💡 Check individual step results above[/cyan]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Workflow cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Workflow error: {str(e)}[/red]")
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
    provider: Optional[LLMProvider] = typer.Option(
        None,
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
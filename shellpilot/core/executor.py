"""
Command executor for ShellPilot
"""

import subprocess
import shlex
import sys
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .safety import SafetyChecker, SafetyResult

console = Console()

@dataclass
class ExecutionResult:
    """Result of command execution"""
    command: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float

class CommandExecutor:
    """Executes shell commands with safety checks"""

    def __init__(self, safe_mode: bool = True, dry_run: bool = False):
        self.safe_mode = safe_mode
        self.dry_run = dry_run
        self.safety_checker = SafetyChecker(safe_mode)

    def execute_single(self, command: str, timeout: int = 30) -> ExecutionResult:
        """Execute a single command"""
        import time
        start_time = time.time()

        # Safety check
        safety_result = self.safety_checker.check_command(command)

        if not safety_result.is_safe:
            return ExecutionResult(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command blocked for safety: {safety_result.reason}",
                execution_time=time.time() - start_time
            )

        # Show warnings if any
        if safety_result.warnings:
            for warning in safety_result.warnings:
                console.print(warning)

        # Get user approval if needed
        if self.safe_mode and not self._get_user_approval(command, safety_result):
            return ExecutionResult(
                command=command,
                success=False,
                exit_code=-2,
                stdout="",
                stderr="Command cancelled by user",
                execution_time=time.time() - start_time
            )

        # Dry run mode
        if self.dry_run:
            console.print(f"[dim][DRY RUN] Would execute: {command}[/dim]")
            return ExecutionResult(
                command=command,
                success=True,
                exit_code=0,
                stdout=f"[DRY RUN] Command: {command}",
                stderr="",
                execution_time=time.time() - start_time
            )

        # Execute the command
        try:
            # Use shell=True carefully with shlex.quote for safety
            quoted_command = shlex.quote(command) if not command.startswith('sudo') else command

            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit
            )

            return ExecutionResult(
                command=command,
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                execution_time=time.time() - start_time
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                command=command,
                success=False,
                exit_code=-3,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                execution_time=timeout
            )
        except Exception as e:
            return ExecutionResult(
                command=command,
                success=False,
                exit_code=-4,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def execute_multiple(self, commands: List[str]) -> List[ExecutionResult]:
        """Execute multiple commands in sequence"""
        results = []

        for command in commands:
            console.print(f"\n[cyan]Executing:[/cyan] {command}")
            result = self.execute_single(command)
            results.append(result)

            # Display result
            self._display_result(result)

            # Stop on failure if in safe mode
            if not result.success and self.safe_mode:
                console.print("[red]❌ Stopping execution due to failure[/red]")
                break

        return results

    def _get_user_approval(self, command: str, safety_result: SafetyResult) -> bool:
        """Get user approval for command execution"""
        if safety_result.risk_level == "critical":
            console.print(f"[red]CRITICAL: Command blocked for safety![/red]")
            return False

        elif safety_result.risk_level == "high":
            console.print(f"[red]HIGH RISK:[/red] {command}")
            console.print("[yellow]This command could be dangerous![/yellow]")
            response = Prompt.ask(
                "Type 'yes' to execute anyway",
                default="no"
            )
            return response.lower() == "yes"

        elif safety_result.risk_level == "medium":
            console.print(f"[yellow]MEDIUM RISK:[/yellow] {command}")
            return Confirm.ask("Execute this command?", default=False)

        else:
            # Low risk - just confirm
            return Confirm.ask(f"Execute: {command}?", default=True)

    def _display_result(self, result: ExecutionResult) -> None:
        """Display execution result"""
        if result.success:
            console.print("[green]✅ Success[/green]")
            if result.stdout:
                console.print(Panel(
                    result.stdout,
                    title="Output",
                    border_style="green"
                ))
        else:
            console.print(f"[red]❌ Failed (exit code: {result.exit_code})[/red]")
            if result.stderr:
                console.print(Panel(
                    result.stderr,
                    title="Error",
                    border_style="red"
                ))

        # Show execution time for long-running commands
        if result.execution_time > 1.0:
            console.print(f"[dim]Execution time: {result.execution_time:.2f}s[/dim]")

    def test_execution(self) -> bool:
        """Test if command execution is working"""
        try:
            result = self.execute_single("echo 'ShellPilot test'")
            return result.success and "ShellPilot test" in result.stdout
        except Exception:
            return False
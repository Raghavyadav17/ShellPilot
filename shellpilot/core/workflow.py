"""
Multi-step workflow execution for ShellPilot
Handles complex tasks with dependencies, conditional logic, and error recovery
"""

import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table

console = Console()

class StepStatus(str, Enum):
    """Status of a workflow step"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

class StepType(str, Enum):
    """Type of workflow step"""
    COMMAND = "command"
    CONDITION = "condition"
    PARALLEL = "parallel"
    ROLLBACK = "rollback"

@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    name: str
    description: str
    commands: List[str]
    step_type: StepType = StepType.COMMAND
    status: StepStatus = StepStatus.PENDING
    depends_on: List[str] = None  # Step IDs this depends on
    retry_count: int = 0
    max_retries: int = 2
    timeout: int = 300  # 5 minutes default
    rollback_commands: List[str] = None
    condition: Optional[str] = None  # For conditional steps
    error_message: Optional[str] = None
    output: Optional[str] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.rollback_commands is None:
            self.rollback_commands = []

@dataclass
class Workflow:
    """Represents a complete multi-step workflow"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: StepStatus = StepStatus.PENDING
    current_step_index: int = 0
    created_by_query: str = ""
    ai_plan: str = ""

class WorkflowEngine:
    """Executes and manages multi-step workflows"""

    def __init__(self, executor, safety_checker):
        self.executor = executor
        self.safety_checker = safety_checker
        self.console = console

    def create_workflow_from_llm_response(self, query: str, llm_response, ai_plan: str = "") -> Workflow:
        """Create a workflow from LLM response with intelligent step grouping"""

        # Try to parse structured workflow from AI response
        workflow_steps = self._parse_workflow_structure(llm_response.content, llm_response.commands)

        # If no structure found, create simple sequential workflow
        if not workflow_steps:
            workflow_steps = self._create_simple_workflow(llm_response.commands)

        workflow = Workflow(
            id=f"workflow_{'_'.join(query.split()[:3])}_{hash(query)%10000}",
            name=f"Workflow: {query[:50]}{'...' if len(query) > 50 else ''}",
            description=f"Multi-step execution for: {query}",
            steps=workflow_steps,
            created_by_query=query,
            ai_plan=ai_plan or llm_response.content[:500]
        )

        return workflow

    def _parse_workflow_structure(self, ai_content: str, commands: List[str]) -> List[WorkflowStep]:
        """Parse AI response for workflow structure (steps, dependencies, etc.)"""
        steps = []

        # Look for structured steps in AI response
        lines = ai_content.split('\n')
        current_step = None
        step_commands = []
        step_counter = 1

        for line in lines:
            line = line.strip()

            # Detect step headers (### Step X, ## Phase X, etc.)
            if any(pattern in line.lower() for pattern in ['step ', 'phase ', 'stage ']):
                # Save previous step
                if current_step and step_commands:
                    steps.append(WorkflowStep(
                        id=f"step_{step_counter}",
                        name=current_step,
                        description=current_step,
                        commands=step_commands.copy()
                    ))
                    step_counter += 1

                # Start new step
                current_step = line.replace('#', '').strip()
                step_commands = []

            # Collect commands for current step
            elif current_step:
                for cmd in commands:
                    if cmd in line:
                        step_commands.append(cmd)

        # Add final step
        if current_step and step_commands:
            steps.append(WorkflowStep(
                id=f"step_{step_counter}",
                name=current_step,
                description=current_step,
                commands=step_commands
            ))

        # Add dependencies (each step depends on previous)
        for i in range(1, len(steps)):
            steps[i].depends_on = [steps[i-1].id]

        return steps

    def _create_simple_workflow(self, commands: List[str]) -> List[WorkflowStep]:
        """Create simple sequential workflow from commands"""
        steps = []

        # Group commands intelligently
        command_groups = self._group_related_commands(commands)

        for i, (group_name, group_commands) in enumerate(command_groups.items(), 1):
            step = WorkflowStep(
                id=f"step_{i}",
                name=group_name,
                description=f"Execute {group_name.lower()}",
                commands=group_commands,
                depends_on=[f"step_{i-1}"] if i > 1 else []
            )
            steps.append(step)

        return steps

    def _group_related_commands(self, commands: List[str]) -> Dict[str, List[str]]:
        """Group related commands into logical steps"""
        groups = {}
        current_group = "Setup"

        for cmd in commands:
            # Categorize commands
            if any(x in cmd for x in ['apt update', 'yum update', 'dnf update']):
                current_group = "System Update"
            elif any(x in cmd for x in ['apt install', 'yum install', 'dnf install']):
                current_group = "Package Installation"
            elif any(x in cmd for x in ['systemctl', 'service']):
                current_group = "Service Management"
            elif any(x in cmd for x in ['ufw', 'iptables', 'firewall']):
                current_group = "Firewall Configuration"
            elif any(x in cmd for x in ['nginx', 'apache', 'httpd']):
                current_group = "Web Server Setup"
            elif any(x in cmd for x in ['docker', 'container']):
                current_group = "Container Setup"
            elif any(x in cmd for x in ['git clone', 'git']):
                current_group = "Repository Setup"
            elif any(x in cmd for x in ['chmod', 'chown', 'mkdir']):
                current_group = "File System Setup"
            else:
                current_group = "Configuration"

            if current_group not in groups:
                groups[current_group] = []
            groups[current_group].append(cmd)

        return groups

    def execute_workflow(self, workflow: Workflow, interactive: bool = True) -> bool:
        """Execute a complete workflow with dependency handling"""
        console.print(Panel(
            f"[bold blue]Starting Workflow Execution[/bold blue]\n"
            f"[cyan]Name:[/cyan] {workflow.name}\n"
            f"[cyan]Steps:[/cyan] {len(workflow.steps)}\n"
            f"[cyan]Query:[/cyan] {workflow.created_by_query}",
            title="🔄 Multi-Step Workflow",
            border_style="blue"
        ))

        workflow.status = StepStatus.RUNNING

        # Show workflow plan
        self._display_workflow_plan(workflow)

        if interactive:
            if not console.input("\n[cyan]Execute this workflow? [Y/n]: [/cyan]").lower() in ['', 'y', 'yes']:
                console.print("[yellow]Workflow cancelled[/yellow]")
                return False

        # Execute steps in dependency order
        success = True
        with Progress() as progress:
            task = progress.add_task("[cyan]Executing workflow...", total=len(workflow.steps))

            for step in workflow.steps:
                if not self._can_execute_step(step, workflow):
                    step.status = StepStatus.SKIPPED
                    console.print(f"[yellow]⏭️  Skipping {step.name} (dependencies not met)[/yellow]")
                    progress.advance(task)
                    continue

                step_success = self._execute_step(step, workflow, interactive)

                if not step_success:
                    success = False
                    if self._should_stop_on_failure(step, workflow):
                        console.print(f"[red]❌ Workflow stopped due to critical failure in: {step.name}[/red]")
                        break

                progress.advance(task)

        # Final status
        workflow.status = StepStatus.SUCCESS if success else StepStatus.FAILED
        self._display_workflow_summary(workflow)

        return success

    def _display_workflow_plan(self, workflow: Workflow) -> None:
        """Display the workflow execution plan"""
        table = Table(title="📋 Workflow Execution Plan")
        table.add_column("Step", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Commands", style="dim")
        table.add_column("Dependencies", style="yellow")

        for i, step in enumerate(workflow.steps, 1):
            commands_preview = ", ".join(step.commands[:2])
            if len(step.commands) > 2:
                commands_preview += f"... (+{len(step.commands) - 2} more)"

            dependencies = ", ".join(step.depends_on) if step.depends_on else "None"

            table.add_row(
                str(i),
                step.name,
                commands_preview,
                dependencies
            )

        console.print(table)

    def _can_execute_step(self, step: WorkflowStep, workflow: Workflow) -> bool:
        """Check if step dependencies are satisfied"""
        if not step.depends_on:
            return True

        for dep_id in step.depends_on:
            dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != StepStatus.SUCCESS:
                return False

        return True

    def _execute_step(self, step: WorkflowStep, workflow: Workflow, interactive: bool = True) -> bool:
        """Execute a single workflow step"""
        console.print(f"\n[bold cyan]🔄 Executing Step: {step.name}[/bold cyan]")
        console.print(f"[dim]{step.description}[/dim]")

        step.status = StepStatus.RUNNING

        # Execute commands in the step
        all_success = True
        step_output = []

        for cmd in step.commands:
            # Safety check
            if not self.safety_checker.is_safe_to_execute(cmd):
                console.print(f"[red]❌ Command blocked for safety: {cmd}[/red]")
                step.status = StepStatus.FAILED
                step.error_message = f"Command blocked for safety: {cmd}"
                return False

            # Interactive confirmation for critical commands
            if interactive and self._is_critical_command(cmd):
                if not console.input(f"[yellow]Execute: {cmd}? [Y/n]: [/yellow]").lower() in ['', 'y', 'yes']:
                    console.print(f"[yellow]⏭️  Skipped: {cmd}[/yellow]")
                    continue

            # Execute command
            result = self.executor.execute_single(cmd)
            step_output.append(f"Command: {cmd}\nOutput: {result.stdout}\nError: {result.stderr}")

            if not result.success:
                console.print(f"[red]❌ Command failed: {cmd}[/red]")
                step.status = StepStatus.FAILED
                step.error_message = result.stderr
                all_success = False

                # Try retry logic
                if step.retry_count < step.max_retries:
                    console.print(f"[yellow]🔄 Retrying step {step.name} ({step.retry_count + 1}/{step.max_retries})[/yellow]")
                    step.retry_count += 1
                    step.status = StepStatus.RETRYING
                    return self._execute_step(step, workflow, interactive)

                break
            else:
                console.print(f"[green]✅ {cmd}[/green]")

        if all_success:
            step.status = StepStatus.SUCCESS
            step.output = "\n".join(step_output)
            console.print(f"[green]✅ Step completed: {step.name}[/green]")

        return all_success

    def _is_critical_command(self, cmd: str) -> bool:
        """Check if command needs extra confirmation"""
        critical_patterns = [
            'rm ', 'del ', 'format', 'mkfs',
            'systemctl stop', 'service stop',
            'ufw disable', 'iptables -F',
            'chmod 777', 'chown root'
        ]
        return any(pattern in cmd.lower() for pattern in critical_patterns)

    def _should_stop_on_failure(self, step: WorkflowStep, workflow: Workflow) -> bool:
        """Determine if workflow should stop on this step's failure"""
        # Critical steps that should stop the workflow
        critical_keywords = ['install', 'update', 'setup', 'configure']
        return any(keyword in step.name.lower() for keyword in critical_keywords)

    def _display_workflow_summary(self, workflow: Workflow) -> None:
        """Display workflow execution summary"""
        successful_steps = sum(1 for step in workflow.steps if step.status == StepStatus.SUCCESS)
        failed_steps = sum(1 for step in workflow.steps if step.status == StepStatus.FAILED)
        skipped_steps = sum(1 for step in workflow.steps if step.status == StepStatus.SKIPPED)

        summary_panel = Panel(
            f"[bold]Workflow Summary[/bold]\n"
            f"[green]✅ Successful: {successful_steps}[/green]\n"
            f"[red]❌ Failed: {failed_steps}[/red]\n"
            f"[yellow]⏭️  Skipped: {skipped_steps}[/yellow]\n"
            f"[cyan]📊 Overall: {'SUCCESS' if workflow.status == StepStatus.SUCCESS else 'FAILED'}[/cyan]",
            title="🏁 Workflow Complete",
            border_style="green" if workflow.status == StepStatus.SUCCESS else "red"
        )

        console.print(summary_panel)
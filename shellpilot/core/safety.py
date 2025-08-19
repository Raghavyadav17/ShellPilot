"""
Safety checker for validating commands before execution
"""

import re
import shlex
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()

@dataclass
class SafetyResult:
    """Result of safety check"""
    is_safe: bool
    risk_level: str  # "low", "medium", "high", "critical"
    warnings: List[str]
    reason: Optional[str] = None

class SafetyChecker:
    """Validates commands for safety before execution"""

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.blocked_commands = self._get_blocked_commands()
        self.high_risk_patterns = self._get_high_risk_patterns()
        self.medium_risk_patterns = self._get_medium_risk_patterns()

    def _get_blocked_commands(self) -> Set[str]:
        """Commands that are completely blocked"""
        return {
            "rm -rf /",
            "rm -rf /*",
            ":(){ :|:& };:",  # Fork bomb
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda",
            "fdisk /dev/sda",
            "parted /dev/sda",
        }

    def _get_high_risk_patterns(self) -> List[str]:
        """Regex patterns for high-risk commands"""
        return [
            r'rm\s+-rf\s+/',  # Recursive delete from root
            r'dd\s+if=/dev/(?:zero|random)\s+of=/dev/(?:sd[a-z]|hd[a-z])',  # Disk overwrite
            r'mkfs\.\w+\s+/dev/',  # Format filesystem
            r'fdisk\s+.*-.*',  # Partition manipulation
            r'parted\s+/dev/',  # Partition editing
            r'>\s*/dev/(?:sd[a-z]|hd[a-z])',  # Write to disk device
            r'chmod\s+777\s+/',  # Dangerous permissions on root
            r'chown\s+.*:\s*/',  # Change ownership of root
            r'curl.*\|\s*(?:bash|sh)',  # Pipe curl to shell
            r'wget.*\|\s*(?:bash|sh)',  # Pipe wget to shell
        ]

    def _get_medium_risk_patterns(self) -> List[str]:
        """Regex patterns for medium-risk commands"""
        return [
            r'sudo\s+rm\s+-rf',  # Recursive delete with sudo
            r'rm\s+-rf\s+\S+',  # Any recursive delete
            r'chmod\s+[0-7]{3}\s+/',  # Permission change on root
            r'systemctl\s+(?:stop|disable|mask)',  # Stop/disable services
            r'ufw\s+(?:disable|reset)',  # Firewall changes
            r'iptables\s+.*-j\s+DROP',  # Firewall rules
            r'crontab\s+-r',  # Remove all cron jobs
            r'userdel\s+',  # Delete user
            r'groupdel\s+',  # Delete group
        ]

    def check_command(self, command: str) -> SafetyResult:
        """Check if a command is safe to execute"""
        command = command.strip()
        warnings = []

        # Check blocked commands
        if command in self.blocked_commands:
            return SafetyResult(
                is_safe=False,
                risk_level="critical",
                warnings=["This command is completely blocked for safety"],
                reason="Command in blocked list"
            )

        # Check high-risk patterns
        for pattern in self.high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                if self.safe_mode:
                    return SafetyResult(
                        is_safe=False,
                        risk_level="high",
                        warnings=[f"High-risk command detected: {pattern}"],
                        reason="Matches high-risk pattern"
                    )
                else:
                    warnings.append(f"⚠️  High-risk command: {command}")

        # Check medium-risk patterns
        for pattern in self.medium_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                warnings.append(f"⚠️  Medium-risk command: {command}")

        # Additional checks
        warnings.extend(self._additional_checks(command))

        # Determine risk level
        risk_level = "low"
        if warnings:
            if any("High-risk" in w for w in warnings):
                risk_level = "high"
            elif any("Medium-risk" in w for w in warnings):
                risk_level = "medium"

        return SafetyResult(
            is_safe=True,
            risk_level=risk_level,
            warnings=warnings
        )

    def _additional_checks(self, command: str) -> List[str]:
        """Additional safety checks"""
        warnings = []

        # Check for suspicious sudo usage
        if command.startswith('sudo') and 'rm' in command:
            warnings.append("⚠️  Using sudo with rm - be careful!")

        # Check for network commands that could be dangerous
        if re.search(r'curl.*\|.*sh', command):
            warnings.append("⚠️  Piping network content to shell - verify source!")

        # Check for permission changes
        if 'chmod 777' in command:
            warnings.append("⚠️  Setting 777 permissions - security risk!")

        # Check for system file modifications
        system_paths = ['/etc/', '/usr/', '/var/', '/boot/']
        for path in system_paths:
            if path in command and any(op in command for op in ['rm', 'mv', 'cp']):
                warnings.append(f"⚠️  Modifying system directory: {path}")

        return warnings

    def validate_command_list(self, commands: List[str]) -> Dict[str, SafetyResult]:
        """Validate a list of commands"""
        results = {}

        for i, command in enumerate(commands):
            results[f"command_{i}"] = self.check_command(command)

        return results

    def is_safe_to_execute(self, command: str) -> bool:
        """Simple boolean check if command is safe"""
        result = self.check_command(command)
        return result.is_safe

    def get_approval_prompt(self, command: str) -> str:
        """Get appropriate prompt for user approval"""
        result = self.check_command(command)

        if result.risk_level == "critical":
            return f"[red]CRITICAL:[/red] {command}\n[red]This command is blocked for safety![/red]"
        elif result.risk_level == "high":
            return f"[red]HIGH RISK:[/red] {command}\n[yellow]Are you absolutely sure? (type 'yes' to confirm)[/yellow]"
        elif result.risk_level == "medium":
            return f"[yellow]MEDIUM RISK:[/yellow] {command}\n[cyan]Execute this command? [y/N][/cyan]"
        else:
            return f"[green]Execute:[/green] {command} [cyan][Y/n][/cyan]"
"""
LLM Provider base class and utilities for ShellPilot
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from rich.console import Console

console = Console()

@dataclass
class LLMResponse:
    """Response from LLM provider"""
    content: str
    commands: List[str]
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    raw_response: Optional[str] = None

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.base_url = kwargs.get('base_url')
        self.timeout = kwargs.get('timeout', 30)
        self.max_tokens = kwargs.get('max_tokens', 1000)
        self.temperature = kwargs.get('temperature', 0.1)

    @abstractmethod
    def generate_command(self, query: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate command(s) from natural language query"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration (API key, connectivity, etc.)"""
        pass

    def get_system_prompt(self) -> str:
        """Get the system prompt for Linux command generation"""
        return """You are ShellPilot, an AI assistant that helps users with Linux system administration.

Your job is to convert natural language requests into appropriate Linux commands.

Guidelines:
1. Generate safe, correct Linux commands
2. Explain what each command does
3. Use standard Linux utilities (apt, systemctl, ps, etc.)
4. For dangerous operations, provide warnings
5. Format commands clearly using backticks

Response format:
- Brief explanation of what you'll do
- Commands to execute (use ```bash blocks)
- Any warnings or notes

Example:
User: "check system memory usage"
Response: "I'll show you the current memory usage using the free command.

```bash
free -h
```

This displays memory usage in human-readable format."
"""

    def _extract_commands(self, content: str) -> List[str]:
        """Extract shell commands from LLM response"""
        commands = []

        # Look for code blocks with bash/shell
        bash_pattern = r'```(?:bash|shell|sh)?\n(.*?)\n```'
        matches = re.findall(bash_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            # Split by lines and clean up
            lines = match.strip().split('\n')
            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    commands.append(line)

        # If no code blocks found, look for lines starting with common commands
        if not commands:
            common_commands = ['sudo', 'apt', 'yum', 'systemctl', 'docker', 'git', 'ls', 'cd', 'cp', 'mv', 'rm', 'chmod', 'chown', 'ps', 'top', 'grep', 'find', 'curl', 'wget']
            lines = content.split('\n')

            for line in lines:
                line = line.strip()
                if any(line.startswith(cmd) for cmd in common_commands):
                    commands.append(line)

        return commands

    def _validate_commands(self, commands: List[str]) -> List[str]:
        """Basic validation and filtering of commands"""
        safe_commands = []
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'dd\s+if=',
            r'mkfs',
            r'fdisk.*-.*',
            r'format',
            r'>>\s*/dev/null',
            r':\(\)\{.*\|\&\}',  # Fork bomb pattern
        ]

        for cmd in commands:
            # Check for dangerous patterns
            is_dangerous = any(re.search(pattern, cmd, re.IGNORECASE) for pattern in dangerous_patterns)

            if not is_dangerous:
                safe_commands.append(cmd)
            else:
                console.print(f"[yellow]⚠️  Filtered dangerous command: {cmd}[/yellow]")

        return safe_commands

class LLMManager:
    """Manager class to handle different LLM providers"""

    def __init__(self, config):
        self.config = config
        self._provider = None

    def get_provider(self) -> LLMProvider:
        """Get the appropriate LLM provider based on config"""
        if self._provider is None:
            provider_name = self.config.get_default_provider()
            api_key = self.config.get_api_key(provider_name)

            if not api_key:
                raise ValueError(f"No API key found for provider: {provider_name}")

            # Import and create provider
            if provider_name == "deepseek":
                from shellpilot.providers.deepseek import DeepSeekProvider
                self._provider = DeepSeekProvider(
                    api_key=api_key,
                    model=self.config.get_default_model() or "deepseek/deepseek-chat"
                )
            elif provider_name == "openai":
                from shellpilot.providers.openai import OpenAIProvider
                self._provider = OpenAIProvider(
                    api_key=api_key,
                    model=self.config.get_default_model() or "gpt-4"
                )
            elif provider_name == "anthropic":
                from shellpilot.providers.anthropic import AnthropicProvider
                self._provider = AnthropicProvider(
                    api_key=api_key,
                    model=self.config.get_default_model() or "claude-3-sonnet-20240229"
                )
            elif provider_name == "ollama":
                from shellpilot.providers.ollama import OllamaProvider
                self._provider = OllamaProvider(
                    api_key=api_key or "none",  # Ollama doesn't need API key
                    model=self.config.get_default_model() or "llama2",
                    base_url="http://localhost:11434"
                )
            else:
                raise ValueError(f"Unknown provider: {provider_name}")

        return self._provider

    def generate_command(self, query: str) -> LLMResponse:
        """Generate command using the configured provider"""
        provider = self.get_provider()
        return provider.generate_command(query)

    def test_connection(self) -> bool:
        """Test if the provider is working"""
        try:
            provider = self.get_provider()
            return provider.validate_config()
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            return False
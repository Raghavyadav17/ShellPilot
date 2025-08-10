"""
Configuration management for ShellPilot
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

console = Console()

class Config(BaseModel):
    """Configuration model for ShellPilot"""

    # Default settings
    default_provider: str = "openai"
    default_model: Optional[str] = None
    safe_mode: bool = True
    log_level: str = "info"

    # API keys (will be loaded from env/config file)
    api_keys: Dict[str, str] = {}

    # Paths
    config_dir: Path = Path.home() / ".shellpilot"
    config_file: Path = config_dir / "config.json"
    log_file: Path = config_dir / "shellpilot.log"
    history_file: Path = config_dir / "history.json"

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ensure_config_dir()
        self.load_from_file()
        self.load_from_env()

    def ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True)

    def load_from_file(self) -> None:
        """Load configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except (json.JSONDecodeError, IOError) as e:
                console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")

    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        # Load .env file if it exists
        load_dotenv()

        # Map of environment variables to config keys
        env_mapping = {
            'SHELLPILOT_PROVIDER': 'default_provider',
            'SHELLPILOT_MODEL': 'default_model',
            'SHELLPILOT_SAFE_MODE': 'safe_mode',
            'SHELLPILOT_LOG_LEVEL': 'log_level',
        }

        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_key == 'safe_mode':
                    value = value.lower() in ('true', '1', 'yes', 'on')
                setattr(self, config_key, value)

        # Load API keys from environment
        api_key_mapping = {
            'OPENAI_API_KEY': 'openai',
            'ANTHROPIC_API_KEY': 'anthropic',
            'GOOGLE_API_KEY': 'gemini',
            'OLLAMA_API_KEY': 'ollama',
        }

        for env_var, provider in api_key_mapping.items():
            api_key = os.getenv(env_var)
            if api_key:
                self.api_keys[provider] = api_key

    def save_to_file(self) -> None:
        """Save current configuration to JSON file"""
        try:
            config_data = {
                'default_provider': self.default_provider,
                'default_model': self.default_model,
                'safe_mode': self.safe_mode,
                'log_level': self.log_level,
                'api_keys': self.api_keys,
            }

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

        except IOError as e:
            console.print(f"[red]Error saving config: {e}[/red]")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider"""
        return self.api_keys.get(provider)

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for a specific provider"""
        self.api_keys[provider] = api_key
        self.save_to_file()

    def get_default_provider(self) -> str:
        """Get the default LLM provider"""
        return self.default_provider

    def set_default_provider(self, provider: str) -> None:
        """Set the default LLM provider"""
        self.default_provider = provider
        self.save_to_file()

    def get_default_model(self) -> Optional[str]:
        """Get the default model for current provider"""
        return self.default_model

    def set_default_model(self, model: str) -> None:
        """Set the default model"""
        self.default_model = model
        self.save_to_file()

    def reset(self) -> None:
        """Reset configuration to defaults"""
        self.default_provider = "openai"
        self.default_model = None
        self.safe_mode = True
        self.log_level = "info"
        self.api_keys = {}

        # Remove config file
        if self.config_file.exists():
            self.config_file.unlink()

    def show(self) -> None:
        """Display current configuration"""
        table = Table(title="🚁 ShellPilot Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Source", style="dim")

        # Basic settings
        table.add_row(
            "Default Provider",
            self.default_provider,
            "config" if self.config_file.exists() else "default"
        )

        table.add_row(
            "Default Model",
            self.default_model or "[dim]Not set[/dim]",
            "config" if self.default_model else "default"
        )

        table.add_row(
            "Safe Mode",
            "✅ Enabled" if self.safe_mode else "❌ Disabled",
            "config"
        )

        table.add_row(
            "Log Level",
            self.log_level,
            "config"
        )

        # API keys (masked for security)
        for provider, key in self.api_keys.items():
            masked_key = f"{key[:8]}{'*' * (len(key) - 8)}" if len(key) > 8 else "***"
            table.add_row(
                f"{provider.title()} API Key",
                masked_key,
                "environment"
            )

        # Paths
        table.add_row("Config Directory", str(self.config_dir), "system")
        table.add_row("Config File", str(self.config_file), "system")
        table.add_row("Log File", str(self.log_file), "system")

        console.print(table)

# Global config instance
_config = None

def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config
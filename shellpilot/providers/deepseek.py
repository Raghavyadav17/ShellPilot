"""
DeepSeek provider for ShellPilot
"""

import httpx
import json
from typing import Dict, Any, Optional
from rich.console import Console

from shellpilot.core.llm import LLMProvider, LLMResponse

console = Console()

class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider implementation"""

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-chat", **kwargs):
        super().__init__(api_key, model, **kwargs)
        # Use OpenRouter endpoint instead of direct DeepSeek
        self.base_url = kwargs.get('base_url', 'https://openrouter.ai/api')
        self.api_version = kwargs.get('api_version', 'v1')

    def generate_command(self, query: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate command using DeepSeek API"""
        try:
            # Prepare the request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            # System prompt optimized for DeepSeek
            system_prompt = self.get_system_prompt()

            # Enhanced user prompt
            user_prompt = f"""
Please help me with this Linux system administration task: {query}

Requirements:
1. Provide clear, safe Linux commands
2. Explain what each command does
3. Use standard Linux utilities when possible
4. Wrap commands in ```bash code blocks
5. Include any necessary warnings

If the task involves multiple steps, break them down clearly.
"""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False
            }

            # Make the API request
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/{self.api_version}/chat/completions",
                    headers=headers,
                    json=payload
                )

                response.raise_for_status()
                result = response.json()

                # Extract response content
                content = result['choices'][0]['message']['content']

                # Extract commands from the response
                commands = self._extract_commands(content)
                commands = self._validate_commands(commands)

                return LLMResponse(
                    content=content,
                    commands=commands,
                    raw_response=json.dumps(result, indent=2)
                )

        except httpx.HTTPStatusError as e:
            error_msg = f"DeepSeek API error: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail.get('error', {}).get('message', 'Unknown error')}"
            except:
                error_msg += f" - {e.response.text}"

            console.print(f"[red]API Error: {error_msg}[/red]")
            return LLMResponse(
                content=f"Error: {error_msg}",
                commands=[],
                raw_response=str(e)
            )

        except Exception as e:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            return LLMResponse(
                content=f"Error: {str(e)}",
                commands=[],
                raw_response=str(e)
            )

    def validate_config(self) -> bool:
        """Validate DeepSeek configuration"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            # Simple test request
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "Hello, this is a test."}
                ],
                "max_tokens": 10
            }

            with httpx.Client(timeout=10) as client:
                response = client.post(
                    f"{self.base_url}/{self.api_version}/chat/completions",
                    headers=headers,
                    json=payload
                )

                return response.status_code == 200

        except Exception as e:
            console.print(f"[red]Configuration validation failed: {e}[/red]")
            return False

    def get_system_prompt(self) -> str:
        """Get system prompt optimized for DeepSeek"""
        return """You are ShellPilot, an expert Linux system administrator AI assistant.

Your role is to help users accomplish Linux system administration tasks by providing safe, accurate commands.

Core principles:
1. Always prioritize safety - avoid destructive commands
2. Provide clear explanations for each command
3. Use standard Linux utilities (apt, yum, systemctl, docker, etc.)
4. Format commands in ```bash code blocks
5. Include warnings for potentially risky operations
6. Break complex tasks into clear steps

Response format:
- Brief explanation of the task
- Step-by-step commands in ```bash blocks
- Explanation of what each command does
- Any relevant warnings or notes

Example response:
"I'll help you check system memory usage.

```bash
free -h
```

This command displays memory usage in human-readable format showing total, used, and available memory.

```bash
top -n 1 | head -20
```

This shows the top processes by memory usage to identify any memory-heavy applications."

Always be helpful, accurate, and safety-conscious."""
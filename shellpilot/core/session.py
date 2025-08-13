"""
Session management for ShellPilot.
Tracks commands, context, and state across interactions
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List,Dict, Any, Optional
from dataclasses import dataclass, asdict
from rich.console import Console

console = Console()


@dataclass
class SessionCommand:
    """Represents a command executed in the session"""
    timestamp: str
    query: str
    commands: List[str]
    working_dir: str
    success: bool
    ai_summary: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class SessionState:
    """Current session state"""
    session_id: str
    start_time: str
    current_working_dir: str
    total_commands: int
    last_updated: str
    commands_history: List[SessionCommand]

class SessionStore:
    """Manages session state and persistence"""

    def __init__(self, session_file: Optional[Path] = None):
        self.session_file = session_file or Path.home() / ".shellpilot" / "session.json"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = 50  # Keep last 50 commands
        self._session_state = self._load_session()

    def _load_session(self) -> SessionState:
        """Load session from file or create new one"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)

                # Convert command dictionaries back to SessionCommand objects
                commands = [
                    SessionCommand(**cmd) for cmd in data.get('commands_history', [])
                ]

                return SessionState(
                    session_id=data.get('session_id', self._generate_session_id()),
                    start_time=data.get('start_time', self._current_timestamp()),
                    current_working_dir=data.get('current_working_dir', os.getcwd()),
                    total_commands=data.get('total_commands', 0),
                    last_updated=data.get('last_updated', self._current_timestamp()),
                    commands_history=commands
                )
            except (json.JSONDecodeError, KeyError) as e:
                console.print(f"[yellow]Warning: Could not load session file: {e}[/yellow]")
                console.print("[yellow]Creating new session...[/yellow]")

        # Create new session
        return SessionState(
            session_id=self._generate_session_id(),
            start_time=self._current_timestamp(),
            current_working_dir=os.getcwd(),
            total_commands=0,
            last_updated=self._current_timestamp(),
            commands_history=[]
        )

    def _save_session(self) -> None:
        """Save session to file"""
        try:
            # Convert SessionCommand objects to dictionaries
            session_data = asdict(self._session_state)

            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving session: {e}[/red]")

    def _current_timestamp(self) -> str:
        """Get current timestamp as string"""
        return datetime.now().isoformat()

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def add_command(
        self,
        query: str,
        commands: List[str],
        success: bool,
        ai_summary: Optional[str] = None,
        execution_time: float = 0.0
    ) -> None:
        """Add a command to the session history"""
        command_entry = SessionCommand(
            timestamp=self._current_timestamp(),
            query=query,
            commands=commands,
            working_dir=os.getcwd(),
            success=success,
            ai_summary=ai_summary,
            execution_time=execution_time
        )

        # Add to history
        self._session_state.commands_history.append(command_entry)

        # Keep only last N commands
        if len(self._session_state.commands_history) > self.max_history:
            self._session_state.commands_history = self._session_state.commands_history[-self.max_history:]

        # Update session metadata
        self._session_state.total_commands += 1
        self._session_state.current_working_dir = os.getcwd()
        self._session_state.last_updated = self._current_timestamp()

        # Save to file
        self._save_session()

    def get_recent_commands(self, count: int = 10) -> List[SessionCommand]:
        """Get recent commands from history"""
        return self._session_state.commands_history[-count:]

    def get_context_summary(self) -> str:
        """Generate context summary for AI prompts"""
        recent_commands = self.get_recent_commands(5)

        if not recent_commands:
            return "No previous commands in this session."

        context_lines = [
            f"Session Context (Last {len(recent_commands)} commands):",
            f"Current Directory: {self._session_state.current_working_dir}",
            f"Session Started: {self._session_state.start_time}",
            ""
        ]

        for i, cmd in enumerate(recent_commands, 1):
            status = "✅" if cmd.success else "❌"
            context_lines.append(f"{i}. {status} '{cmd.query}' -> {', '.join(cmd.commands[:2])}{'...' if len(cmd.commands) > 2 else ''}")
            if cmd.ai_summary:
                context_lines.append(f"   Summary: {cmd.ai_summary}")

        return "\n".join(context_lines)

    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            "session_id": self._session_state.session_id,
            "start_time": self._session_state.start_time,
            "current_working_dir": self._session_state.current_working_dir,
            "total_commands": self._session_state.total_commands,
            "last_updated": self._session_state.last_updated,
            "commands_in_history": len(self._session_state.commands_history)
        }

    def clear_session(self) -> None:
        """Clear session history"""
        self._session_state = SessionState(
            session_id=self._generate_session_id(),
            start_time=self._current_timestamp(),
            current_working_dir=os.getcwd(),
            total_commands=0,
            last_updated=self._current_timestamp(),
            commands_history=[]
        )
        self._save_session()
        console.print("[green]✅ Session context cleared[/green]")

    def get_session_state(self) -> SessionState:
        """Get current session state"""
        return self._session_state

# Global session store instance
_session_store = None

def get_session_store() -> SessionStore:
    """Get the global session store instance"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
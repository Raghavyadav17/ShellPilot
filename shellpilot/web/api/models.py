"""
Pydantic models for ShellPilot Web API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class LLMProvider(str, Enum):
    """Available LLM providers"""
    deepseek = "deepseek"
    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"
    gemini = "gemini"

class CommandRequest(BaseModel):
    """Request to execute a command"""
    query: str = Field(..., description="Natural language query to execute")
    provider: Optional[LLMProvider] = Field(None, description="LLM provider to use")
    model: Optional[str] = Field(None, description="Specific model to use")
    safe_mode: bool = Field(True, description="Enable safety confirmations")
    dry_run: bool = Field(False, description="Show commands without executing")
    workflow_mode: bool = Field(False, description="Force workflow mode")
    clear_context: bool = Field(False, description="Clear session context first")

class WorkflowRequest(BaseModel):
    """Request to execute a workflow"""
    query: str = Field(..., description="Complex task to execute as workflow")
    provider: Optional[LLMProvider] = Field(None, description="LLM provider to use")
    model: Optional[str] = Field(None, description="Specific model to use")
    safe_mode: bool = Field(True, description="Enable safety confirmations")
    dry_run: bool = Field(False, description="Show workflow plan only")
    auto_approve: bool = Field(False, description="Auto-approve non-critical steps")

class CommandResponse(BaseModel):
    """Response from command execution"""
    success: bool
    query: str
    ai_analysis: str
    commands: List[str]
    execution_results: List[Dict[str, Any]]
    session_id: str
    execution_time: float
    mode: str  # "standard" or "workflow"

class WorkflowResponse(BaseModel):
    """Response from workflow execution"""
    success: bool
    query: str
    ai_plan: str
    workflow_id: str
    steps: List[Dict[str, Any]]
    execution_summary: Dict[str, Any]
    session_id: str
    execution_time: float

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    start_time: str
    total_commands: int
    current_directory: str
    last_updated: str

class CommandHistory(BaseModel):
    """Command history entry"""
    timestamp: str
    query: str
    commands: List[str]
    success: bool
    ai_summary: Optional[str]
    execution_time: float

class SessionResponse(BaseModel):
    """Session context response"""
    session_info: SessionInfo
    recent_commands: List[CommandHistory]
    context_summary: str

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # "command", "workflow", "status", "error", "progress"
    data: Dict[str, Any]
    timestamp: Optional[str] = None

class WebSocketResponse(BaseModel):
    """WebSocket response format"""
    type: str
    success: bool
    data: Dict[str, Any]
    timestamp: str
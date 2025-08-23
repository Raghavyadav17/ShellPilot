"""
Session API endpoints for ShellPilot Web Interface
"""

from fastapi import APIRouter, HTTPException
from typing import List

from shellpilot.core.session import get_session_store

from .models import SessionResponse, SessionInfo, CommandHistory

router = APIRouter()

@router.get("/session", response_model=SessionResponse)
async def get_session_context():
    """Get current session context and command history"""
    try:
        session_store = get_session_store()

        # Get session info
        session_info_dict = session_store.get_session_info()
        session_info = SessionInfo(
            session_id=session_info_dict["session_id"],
            start_time=session_info_dict["start_time"],
            total_commands=session_info_dict["total_commands"],
            current_directory=session_info_dict["current_working_dir"],
            last_updated=session_info_dict["last_updated"]
        )

        # Get recent commands
        recent_commands_data = session_store.get_recent_commands(10)
        recent_commands = []

        for cmd in recent_commands_data:
            recent_commands.append(CommandHistory(
                timestamp=cmd.timestamp,
                query=cmd.query,
                commands=cmd.commands,
                success=cmd.success,
                ai_summary=cmd.ai_summary,
                execution_time=cmd.execution_time
            ))

        # Get context summary
        context_summary = session_store.get_context_summary()

        return SessionResponse(
            session_info=session_info,
            recent_commands=recent_commands,
            context_summary=context_summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/history")
async def get_full_history(limit: int = 20):
    """Get full command history"""
    try:
        session_store = get_session_store()

        # Get recent commands with limit
        recent_commands_data = session_store.get_recent_commands(limit)
        history = []

        for cmd in recent_commands_data:
            history.append({
                "timestamp": cmd.timestamp,
                "query": cmd.query,
                "commands": cmd.commands,
                "success": cmd.success,
                "ai_summary": cmd.ai_summary,
                "execution_time": cmd.execution_time,
                "working_dir": cmd.working_dir
            })

        return {
            "total_commands": len(history),
            "session_id": session_store.get_session_info()["session_id"],
            "history": history
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/clear")
async def clear_session():
    """Clear current session context"""
    try:
        session_store = get_session_store()
        session_store.clear_session()

        return {
            "success": True,
            "message": "Session context cleared",
            "new_session_id": session_store.get_session_info()["session_id"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/stats")
async def get_session_stats():
    """Get session statistics"""
    try:
        session_store = get_session_store()
        session_info = session_store.get_session_info()
        recent_commands = session_store.get_recent_commands(50)  # Last 50 for stats

        # Calculate stats
        successful_commands = sum(1 for cmd in recent_commands if cmd.success)
        failed_commands = len(recent_commands) - successful_commands

        # Average execution time
        total_time = sum(cmd.execution_time for cmd in recent_commands)
        avg_execution_time = total_time / len(recent_commands) if recent_commands else 0

        # Command types
        workflow_commands = sum(1 for cmd in recent_commands if "WORKFLOW" in cmd.query)
        standard_commands = len(recent_commands) - workflow_commands

        return {
            "session_id": session_info["session_id"],
            "session_start": session_info["start_time"],
            "total_commands": session_info["total_commands"],
            "successful_commands": successful_commands,
            "failed_commands": failed_commands,
            "success_rate": (successful_commands / len(recent_commands) * 100) if recent_commands else 0,
            "average_execution_time": round(avg_execution_time, 2),
            "workflow_commands": workflow_commands,
            "standard_commands": standard_commands,
            "current_directory": session_info["current_working_dir"],
            "last_activity": session_info["last_updated"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
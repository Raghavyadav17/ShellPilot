"""
Commands API endpoints for ShellPilot Web Interface
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import time
import asyncio

from shellpilot.config import get_config
from shellpilot.core.session import get_session_store
from shellpilot.core.llm import LLMManager
from shellpilot.core.executor import CommandExecutor
from shellpilot.core.safety import SafetyChecker
from shellpilot.core.workflow import WorkflowEngine

from .models import CommandRequest, CommandResponse, WebSocketMessage

router = APIRouter()

@router.post("/run", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """Execute a ShellPilot command via API"""
    start_time = time.time()

    try:
        # Initialize components
        session_store = get_session_store()
        config = get_config()

        # Clear context if requested
        if request.clear_context:
            session_store.clear_session()

        # Override config with request parameters
        if request.provider:
            config.set_default_provider(request.provider.value)
        if request.model:
            config.set_default_model(request.model)

        # Initialize core components
        llm_manager = LLMManager(config)
        executor = CommandExecutor(safe_mode=request.safe_mode, dry_run=request.dry_run)

        # Get session context
        context = session_store.get_context_summary()

        # Generate commands using AI
        llm_response = llm_manager.generate_command(
            request.query,
            context if context and "No previous commands" not in context else None
        )

        if not llm_response.commands:
            # Record failed attempt
            session_store.add_command(
                query=request.query,
                commands=[],
                success=False,
                ai_summary="No commands generated",
                execution_time=time.time() - start_time
            )

            return CommandResponse(
                success=False,
                query=request.query,
                ai_analysis=llm_response.content,
                commands=[],
                execution_results=[],
                session_id=session_store.get_session_info()["session_id"],
                execution_time=time.time() - start_time,
                mode="standard"
            )

        # Determine execution mode
        is_workflow = request.workflow_mode or len(llm_response.commands) > 6
        execution_results = []

        if is_workflow:
            # Workflow execution
            safety_checker = SafetyChecker(request.safe_mode)
            workflow_engine = WorkflowEngine(executor, safety_checker)

            workflow = workflow_engine.create_workflow_from_llm_response(
                request.query,
                llm_response,
                ai_plan=llm_response.content
            )

            # For API, auto-approve if not in safe mode or if dry run
            auto_approve = not request.safe_mode or request.dry_run

            success = workflow_engine.execute_workflow(workflow, interactive=False)

            # Convert workflow results to execution results
            for step in workflow.steps:
                execution_results.append({
                    "step_name": step.name,
                    "commands": step.commands,
                    "status": step.status.value,
                    "success": step.status.value == "success",
                    "error_message": step.error_message,
                    "output": step.output
                })

            successful_steps = sum(1 for step in workflow.steps if step.status.value == "success")
            total_steps = len(workflow.steps)
            overall_success = successful_steps == total_steps
            mode = "workflow"

        else:
            # Standard execution
            results = executor.execute_multiple(llm_response.commands)

            # Convert to API format
            for i, result in enumerate(results):
                execution_results.append({
                    "command": result.command,
                    "success": result.success,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time
                })

            overall_success = all(r.success for r in results)
            mode = "standard"

        # Create AI summary
        ai_summary = f"Executed via API - {mode} mode"
        if llm_response.content:
            first_sentence = llm_response.content.split('.')[0]
            if len(first_sentence) < 100:
                ai_summary = first_sentence.strip()

        # Record in session
        session_store.add_command(
            query=request.query,
            commands=llm_response.commands,
            success=overall_success,
            ai_summary=ai_summary,
            execution_time=time.time() - start_time
        )

        return CommandResponse(
            success=overall_success,
            query=request.query,
            ai_analysis=llm_response.content,
            commands=llm_response.commands,
            execution_results=execution_results,
            session_id=session_store.get_session_info()["session_id"],
            execution_time=time.time() - start_time,
            mode=mode
        )

    except Exception as e:
        # Record error in session
        session_store.add_command(
            query=request.query,
            commands=[],
            success=False,
            ai_summary=f"API Error: {str(e)}",
            execution_time=time.time() - start_time
        )

        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-simple")
async def test_simple_command():
    """Test endpoint for simple command execution"""
    try:
        # Simple test command
        session_store = get_session_store()
        config = get_config()

        return {
            "status": "ready",
            "session_id": session_store.get_session_info()["session_id"],
            "provider": config.get_default_provider(),
            "model": config.get_default_model(),
            "message": "Command API is ready to execute commands"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
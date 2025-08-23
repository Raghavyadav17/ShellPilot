"""
Workflows API endpoints for ShellPilot Web Interface
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import time

from shellpilot.config import get_config
from shellpilot.core.session import get_session_store
from shellpilot.core.llm import LLMManager
from shellpilot.core.executor import CommandExecutor
from shellpilot.core.safety import SafetyChecker
from shellpilot.core.workflow import WorkflowEngine

from .models import WorkflowRequest, WorkflowResponse

router = APIRouter()

@router.post("/workflow", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    """Execute a complex workflow via API"""
    start_time = time.time()

    try:
        # Initialize components
        session_store = get_session_store()
        config = get_config()

        # Override config with request parameters
        if request.provider:
            config.set_default_provider(request.provider.value)
        if request.model:
            config.set_default_model(request.model)

        # Initialize workflow system
        llm_manager = LLMManager(config)
        safety_checker = SafetyChecker(request.safe_mode)
        executor = CommandExecutor(safe_mode=request.safe_mode, dry_run=request.dry_run)
        workflow_engine = WorkflowEngine(executor, safety_checker)

        # Get session context
        context = session_store.get_context_summary()

        # Enhanced prompt for workflow planning
        workflow_prompt = f"""
MULTI-STEP WORKFLOW PLANNING:

Task: {request.query}

Create a comprehensive step-by-step plan for this complex task. Structure with clear phases:

### Step 1: [Phase Name]
Brief description of what this phase accomplishes.
```bash
command1
command2
```

### Step 2: [Phase Name]
Brief description of what this phase accomplishes.
```bash
command3
command4
```

Important considerations:
1. Break down into logical, sequential phases
2. Each step should have clear dependencies
3. Include verification commands where appropriate
4. Use safe, standard Linux practices

Context from recent session:
{context if context and "No previous commands" not in context else "No previous session context."}
"""

        # Generate workflow plan
        llm_response = llm_manager.generate_command(workflow_prompt)

        if not llm_response.commands:
            # Record failed attempt
            session_store.add_command(
                query=f"[WORKFLOW] {request.query}",
                commands=[],
                success=False,
                ai_summary="No workflow plan generated",
                execution_time=time.time() - start_time
            )

            raise HTTPException(
                status_code=400,
                detail="Could not generate workflow plan. Try rephrasing your request."
            )

        # Create workflow
        workflow = workflow_engine.create_workflow_from_llm_response(
            request.query,
            llm_response,
            ai_plan=llm_response.content
        )

        if request.dry_run:
            # Dry run - return plan only
            steps_data = []
            for step in workflow.steps:
                steps_data.append({
                    "id": step.id,
                    "name": step.name,
                    "description": step.description,
                    "commands": step.commands,
                    "depends_on": step.depends_on,
                    "status": "planned"
                })

            # Record planning in session
            session_store.add_command(
                query=f"[WORKFLOW PLAN] {request.query}",
                commands=llm_response.commands,
                success=True,
                ai_summary=f"Planned {len(workflow.steps)} step workflow",
                execution_time=time.time() - start_time
            )

            return WorkflowResponse(
                success=True,
                query=request.query,
                ai_plan=llm_response.content,
                workflow_id=workflow.id,
                steps=steps_data,
                execution_summary={
                    "mode": "planning",
                    "total_steps": len(workflow.steps),
                    "planned_commands": len(llm_response.commands)
                },
                session_id=session_store.get_session_info()["session_id"],
                execution_time=time.time() - start_time
            )

        else:
            # Execute workflow
            success = workflow_engine.execute_workflow(
                workflow,
                interactive=False  # Non-interactive for API
            )

            # Prepare step results
            steps_data = []
            for step in workflow.steps:
                steps_data.append({
                    "id": step.id,
                    "name": step.name,
                    "description": step.description,
                    "commands": step.commands,
                    "depends_on": step.depends_on,
                    "status": step.status.value,
                    "error_message": step.error_message,
                    "output": step.output,
                    "retry_count": step.retry_count
                })

            # Execution summary
            successful_steps = sum(1 for step in workflow.steps if step.status.value == "success")
            failed_steps = sum(1 for step in workflow.steps if step.status.value == "failed")
            skipped_steps = sum(1 for step in workflow.steps if step.status.value == "skipped")

            execution_summary = {
                "mode": "execution",
                "total_steps": len(workflow.steps),
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "overall_success": success
            }

            # Record execution in session
            session_store.add_command(
                query=f"[WORKFLOW] {request.query}",
                commands=llm_response.commands,
                success=success,
                ai_summary=f"Executed {successful_steps}/{len(workflow.steps)} workflow steps",
                execution_time=time.time() - start_time
            )

            return WorkflowResponse(
                success=success,
                query=request.query,
                ai_plan=llm_response.content,
                workflow_id=workflow.id,
                steps=steps_data,
                execution_summary=execution_summary,
                session_id=session_store.get_session_info()["session_id"],
                execution_time=time.time() - start_time
            )

    except HTTPException:
        raise
    except Exception as e:
        # Record error in session
        session_store.add_command(
            query=f"[WORKFLOW ERROR] {request.query}",
            commands=[],
            success=False,
            ai_summary=f"Workflow API Error: {str(e)}",
            execution_time=time.time() - start_time
        )

        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/test")
async def test_workflow_endpoint():
    """Test endpoint for workflow functionality"""
    try:
        config = get_config()
        session_store = get_session_store()

        return {
            "status": "ready",
            "message": "Workflow API is ready to execute complex tasks",
            "session_id": session_store.get_session_info()["session_id"],
            "provider": config.get_default_provider(),
            "workflow_features": [
                "Multi-step planning",
                "Dependency resolution",
                "Error handling",
                "Progress tracking",
                "Dry-run support"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
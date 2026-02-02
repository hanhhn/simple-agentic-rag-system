"""
Agent API endpoints for agentic RAG.
"""
from fastapi import APIRouter, Depends, HTTPException

from src.core.logging import get_logger, LogTag
from src.core.exceptions import AgentError, ValidationError
from src.api.models.common import SuccessResponse, ErrorResponse
from src.api.dependencies import get_llm_service, get_vector_store, get_embedding_service
from src.services.agent_service import AgentService


logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post(
    "/query",
    response_model=SuccessResponse,
    status_code=200,
    summary="Execute agentic query",
    description="""
    Execute a query using intelligent agents with tool capabilities.
    
    This endpoint uses the ReAct (Reasoning + Acting) pattern to:
    1. Break down complex queries into steps
    2. Use appropriate tools (retrieval, calculation, summary, etc.)
    3. Reason about intermediate results
    4. Generate final comprehensive answer
    5. Reflect on and improve answer quality
    
    **Features:**
    - Multi-step reasoning
    - Tool selection and execution
    - Memory for conversation history
    - Answer reflection and self-improvement
    - Detailed execution trace
    
    **Parameters:**
    - `query`: Natural language question or task
    - `collection`: Collection name to search
    - `agent_type`: Type of agent ("react")
    - `temperature`: LLM temperature (0.0-1.0)
    - `enable_reflection`: Whether to enable answer evaluation (default: true)
    """
)
async def agent_query(
    query: str,
    collection: str,
    agent_type: str = "react",
    temperature: float = 0.7,
    enable_reflection: bool = True,
    llm_service = Depends(get_llm_service),
    vector_store = Depends(get_vector_store),
    embedding_service = Depends(get_embedding_service)
):
    """
    Execute an agentic query.
    
    Args:
        query: User query
        collection: Collection name
        agent_type: Agent type to use
        temperature: LLM temperature
        
    Returns:
        Success response with agent results
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        if not collection or not collection.strip():
            raise ValidationError("Collection name cannot be empty")
        
        if agent_type not in ["react"]:
            raise ValidationError(f"Unknown agent type: {agent_type}")
        
        logger.bind(tag=LogTag.API.value).info(
            "Agent query request received",
            query=query[:100],
            query_length=len(query),
            collection=collection,
            agent_type=agent_type,
            temperature=temperature,
            enable_reflection=enable_reflection
        )
        
        # Create agent service
        logger.bind(tag=LogTag.API.value).info("Creating agent service")
        agent_service = AgentService(
            llm_service=llm_service,
            vector_store=vector_store,
            embedding_service=embedding_service,
            use_memory=True,
            verbose=True
        )
        
        # Execute query
        logger.bind(tag=LogTag.API.value).info("Executing agent query")
        result = await agent_service.query(
            query=query,
            collection=collection,
            agent_type=agent_type,
            enable_reflection=enable_reflection
        )
        
        logger.bind(tag=LogTag.API.value).info(
            "Agent query response prepared",
            success=result.get("success", False),
            answer_length=len(result.get("answer", "")) if result.get("answer") else 0,
            actions_count=len(result.get("actions", [])),
            confidence=result.get("confidence", 0.0)
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error_code": "AGENT_ERROR",
                    "message": result.get("error", "Agent execution failed")
                }
            )
        
        # Format response
        return SuccessResponse(
            success=True,
            data=result
        )
        
    except ValidationError as e:
        logger.bind(tag=LogTag.VALIDATION.value).error("Agent query validation failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    except AgentError as e:
        logger.bind(tag=LogTag.AGENT.value).error("Agent execution error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.bind(tag=LogTag.ERROR.value).error("Unexpected error in agent query", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to execute agent query: {str(e)}"
            }
        )


@router.post("/plan", response_model=SuccessResponse)
async def plan_query(
    query: str,
    collection: str = None,
    llm_service = Depends(get_llm_service),
    vector_store = Depends(get_vector_store),
    embedding_service = Depends(get_embedding_service)
):
    """
    Plan a query without executing it.
    
    Args:
        query: User query
        collection: Collection name (optional)
        
    Returns:
        Success response with execution plan
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        logger.bind(tag=LogTag.API.value).info(
            "Query plan request",
            query=query[:100],
            collection=collection
        )
        
        # Create agent service
        agent_service = AgentService(
            llm_service=llm_service,
            vector_store=vector_store,
            embedding_service=embedding_service,
            use_memory=False
        )
        
        # Plan query
        result = await agent_service.plan_query(
            query=query,
            collection=collection
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error_code": "PLANNING_ERROR",
                    "message": result.get("error", "Query planning failed")
                }
            )
        
        return SuccessResponse(
            success=True,
            data=result
        )
        
    except ValidationError as e:
        logger.bind(tag=LogTag.VALIDATION.value).error("Query plan validation failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.bind(tag=LogTag.ERROR.value).error("Unexpected error in query planning", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to plan query: {str(e)}"
            }
        )


@router.get("/tools", response_model=SuccessResponse)
async def list_tools(
    llm_service = Depends(get_llm_service),
    vector_store = Depends(get_vector_store),
    embedding_service = Depends(get_embedding_service)
):
    """
    List available agent tools.
    
    Returns:
        Success response with list of tools
    """
    try:
        # Create agent service
        agent_service = AgentService(
            llm_service=llm_service,
            vector_store=vector_store,
            embedding_service=embedding_service,
            use_memory=False
        )
        
        # Get tools
        tools = agent_service.get_available_tools()
        
        return SuccessResponse(
            success=True,
            data={
                "tools": tools,
                "count": len(tools)
            }
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.ERROR.value).error("Failed to list tools", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to list tools: {str(e)}"
            }
        )


@router.delete("/memory", response_model=SuccessResponse)
async def clear_agent_memory(
    llm_service = Depends(get_llm_service),
    vector_store = Depends(get_vector_store),
    embedding_service = Depends(get_embedding_service)
):
    """
    Clear agent conversation memory.
    
    Returns:
        Success response
    """
    try:
        # Create agent service
        agent_service = AgentService(
            llm_service=llm_service,
            vector_store=vector_store,
            embedding_service=embedding_service,
            use_memory=True
        )
        
        # Clear memory
        agent_service.clear_memory()
        
        return SuccessResponse(
            success=True,
            data={"message": "Agent memory cleared successfully"}
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.ERROR.value).error("Failed to clear memory", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to clear memory: {str(e)}"
            }
        )

"""
Health check endpoints.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.core.logging import get_logger
from src.core.config import get_config
from src.api.models.common import HealthResponse


logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "", 
    response_model=HealthResponse,
    status_code=200,
    summary="Health check",
    description="""
    Check the overall health status of the system and dependent services.
    
    **Checks:**
    - Qdrant vector database connectivity
    - Ollama LLM service availability
    - Embedding model availability
    
    **Returns:**
    - Overall system status (healthy/degraded)
    - Status of each dependent service
    - API version and timestamp
    """
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns overall system health and status of dependent services.
    
    Returns:
        HealthResponse with system status
    """
    config = get_config()
    
    # Check dependent services
    services_status = {}
    
    # Check Qdrant
    try:
        from src.services.vector_store import VectorStore
        store = VectorStore()
        store.list_collections()
        services_status["qdrant"] = "healthy"
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        services_status["qdrant"] = f"unhealthy: {str(e)}"
    
    # Check Ollama
    try:
        from src.services.llm_service import LLMService
        llm = LLMService()
        llm.list_models()
        services_status["ollama"] = "healthy"
    except Exception as e:
        logger.error("Ollama health check failed", error=str(e))
        services_status["ollama"] = f"unhealthy: {str(e)}"
    
    # Check embedding model
    try:
        from src.services.embedding_service import EmbeddingService
        from src.embedding.models.granite_embedding import GraniteEmbeddingModel

        # Directly test Granite model (avoid service overhead)
        model = GraniteEmbeddingModel()
        model.get_dimension()
        services_status["embeddings"] = "healthy"
    except Exception as e:
        logger.error("Embedding model health check failed", error=str(e))
        services_status["embeddings"] = f"unhealthy: {str(e)}"
    
    # Determine overall status
    all_healthy = all(status == "healthy" for status in services_status.values())
    overall_status = "healthy" if all_healthy else "degraded"
    
    logger.info(
        "Health check completed",
        status=overall_status,
        services=services_status
    )
    
    return HealthResponse(
        status=overall_status,
        version=config.app.api_version,
        timestamp=datetime.utcnow(),
        services=services_status
    )


@router.get(
    "/ready", 
    response_model=dict,
    status_code=200,
    summary="Readiness check",
    description="""
    Simple readiness check to verify the application is ready to handle requests.
    
    This is a lightweight endpoint useful for load balancers and orchestration systems.
    
    **Returns:**
    - Readiness status and timestamp
    """
)
async def readiness_check() -> dict:
    """
    Readiness check endpoint.
    
    Simple check if application is ready to handle requests.
    
    Returns:
        Dictionary with readiness status
    """
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }

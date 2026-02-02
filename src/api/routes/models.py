"""
Model management endpoints for LLM and embedding models.
"""
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.core.logging import get_logger, LogTag
from src.core.exceptions import LLMError
from src.api.models.common import SuccessResponse
from src.services.llm_service import LLMService
from src.services.embedding_service import EmbeddingService
from src.api.models.task import TaskResponse, TaskStatus
from src.core.metrics import llm_generation_total, llm_generation_errors

logger = get_logger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "/",
    response_model=dict,
    status_code=200,
    summary="List available LLM models",
    description="""
    List all available LLM models from Ollama.

    **Returns:**
    - Dictionary with available models and current model

    **Example:**
    ```json
    {
        "available": ["llama2", "mistral", "phi"],
        "current": "llama2"
    }
    ```
    """
)
async def list_llm_models(
    llm_service = LLMService()
) -> dict:
    """
    List all available LLM models.

    Returns:
        Dictionary with available and current models
    """
    try:
        logger.bind(tag=LogTag.API.value).info("Listing available LLM models")

        models = llm_service.list_models()
        current = llm_service.get_model_name()

        logger.bind(tag=LogTag.API.value).info(
            "LLM models listed",
            count=len(models),
            current=current
        )

        return {
            "available": models,
            "current": current
        }

    except LLMError as e:
        logger.bind(tag=LogTag.API.value).error("Failed to list LLM models", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Unexpected error listing LLM models", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to list models: {str(e)}"
            }
        )


@router.post(
    "/switch",
    response_model=SuccessResponse,
    status_code=200,
    summary="Switch active LLM model",
    description="""
    Switch the active LLM model used for generation.

    **Parameters:**
    - `model`: Model name to switch to (must be available in Ollama)

    **Returns:**
    - Success response confirming model switch

    **Example:**
    ```json
    {
        "success": true,
        "message": "Switched to model 'mistral'"
    }
    ```
    """
)
async def switch_llm_model(
    model: str,
    llm_service = LLMService()
) -> SuccessResponse:
    """
    Switch the active LLM model.

    Args:
        model: Model name to switch to

    Returns:
        SuccessResponse
    """
    try:
        logger.bind(tag=LogTag.API.value).info("Switching LLM model", model=model)

        llm_service.set_model(model)

        logger.bind(tag=LogTag.API.value).info("LLM model switched successfully", model=model)

        return SuccessResponse(
            success=True,
            message=f"Switched to model '{model}'"
        )

    except LLMError as e:
        logger.bind(tag=LogTag.API.value).error("Failed to switch LLM model", model=model, error=str(e))
        llm_generation_errors.labels(
            model=model,
            error_type="switch_failed"
        ).inc()
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Unexpected error switching LLM model", model=model, error=str(e))
        llm_generation_errors.labels(
            model=model,
            error_type="unexpected_error"
        ).inc()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to switch model to '{model}': {str(e)}"
            }
        )


@router.get(
    "/embedding",
    response_model=dict,
    status_code=200,
    summary="Get embedding model information",
    description="""
    Get information about the current embedding model.

    **Returns:**
    - Dictionary with model information including name, dimension, and cache status

    **Example:**
    ```json
    {
        "model_name": "ibm-granite/granite-embedding-small-english-r2",
        "dimension": 384,
        "cache_enabled": true,
        "cache_stats": {
            "entries": 42,
            "max_size": 1000,
            "cache_hit_rate": 0.85
        }
    }
    ```
    """
)
async def get_embedding_info(
    embedding_service = EmbeddingService()
) -> dict:
    """
    Get embedding model information.

    Returns:
        Dictionary with embedding model information
    """
    try:
        logger.bind(tag=LogTag.API.value).info("Getting embedding model info")

        model_name = embedding_service.get_model_name()
        dimension = embedding_service.get_dimension()
        cache_stats = embedding_service.get_cache_stats()

        logger.bind(tag=LogTag.API.value).info(
            "Embedding model info retrieved",
            model=model_name,
            dimension=dimension,
            cache_enabled=cache_stats.get("entries", 0) > 0
        )

        return {
            "model_name": model_name,
            "dimension": dimension,
            "cache_enabled": cache_stats.get("entries", 0) > 0,
            "cache_stats": cache_stats
        }

    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get embedding model info", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to get embedding info: {str(e)}"
            }
        )


@router.delete(
    "/embedding/cache",
    response_model=SuccessResponse,
    status_code=200,
    summary="Clear embedding cache",
    description="""
    Clear the embedding cache to force recomputation of embeddings.

    **Warning:** This will slow down subsequent queries until cache is rebuilt.

    **Returns:**
    - Success response confirming cache clear

    **Example:**
    ```json
    {
        "success": true,
        "message": "Embedding cache cleared successfully"
    }
    ```
    """
)
async def clear_embedding_cache(
    embedding_service = EmbeddingService()
) -> SuccessResponse:
    """
    Clear the embedding cache.

    Returns:
        SuccessResponse
    """
    try:
        logger.bind(tag=LogTag.API.value).info("Clearing embedding cache")

        embedding_service.clear_cache()

        logger.bind(tag=LogTag.API.value).info("Embedding cache cleared successfully")

        return SuccessResponse(
            success=True,
            message="Embedding cache cleared successfully"
        )

    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to clear embedding cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to clear embedding cache: {str(e)}"
            }
        )

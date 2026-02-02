"""
Collection management endpoints.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.core.logging import get_logger
from src.core.exceptions import (
    CollectionNotFoundError,
    CollectionCreationError,
    ServiceError,
    ValidationError
)
from src.api.models.collection import (
    CollectionCreateRequest,
    CollectionInfo,
    CollectionListResponse,
    CollectionResponse
)
from src.api.models.common import SuccessResponse
from src.api.dependencies import get_vector_store, get_embedding_service, get_storage_manager
from src.utils.validators import CollectionValidator


logger = get_logger(__name__)

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.post(
    "", 
    response_model=CollectionResponse,
    status_code=201,
    summary="Create a new collection",
    description="""
    Create a new vector collection for storing document embeddings.
    
    **Parameters:**
    - `name`: Collection name (alphanumeric, underscores, hyphens allowed)
    - `dimension`: Embedding dimension (auto-detected from model if not provided)
    - `distance_metric`: Distance metric for similarity search (Cosine, Euclid, or Dot)
    
    **Returns:**
    - Collection information including name, dimension, and status
    """
)
async def create_collection(
    request: CollectionCreateRequest,
    vector_store = Depends(get_vector_store),
    embedding_service = Depends(get_embedding_service)
) -> CollectionResponse:
    """
    Create a new collection.
    
    Args:
        request: Collection creation request
        
    Returns:
        CollectionResponse with collection information
    """
    validator = CollectionValidator()
    
    try:
        # Validate collection name
        validator.validate_collection_name(request.name)
        
        # Validate dimension if provided
        if request.dimension:
            validator.validate_embedding_dimension(request.dimension)
        else:
            # Use embedding service dimension
            request.dimension = embedding_service.get_dimension()
        
        logger.info(
            "Creating collection",
            name=request.name,
            dimension=request.dimension,
            distance_metric=request.distance_metric
        )
        
        # Create collection
        vector_store.create_collection(
            collection_name=request.name,
            dimension=request.dimension,
            distance_metric=request.distance_metric
        )
        
        logger.info("Collection created successfully", name=request.name)
        
        return CollectionResponse(
            collection=CollectionInfo(
                name=request.name,
                vector_count=0,
                dimension=request.dimension,
                status="ready",
                created_at=datetime.utcnow(),
                distance_metric=request.distance_metric
            ),
            message=f"Collection '{request.name}' created successfully"
        )
        
    except ValidationError as e:
        logger.error("Collection validation failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    except CollectionCreationError as e:
        logger.error("Collection creation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error during collection creation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to create collection: {str(e)}"
            }
        )


@router.get(
    "", 
    response_model=CollectionListResponse,
    status_code=200,
    summary="List all collections",
    description="""
    Retrieve a list of all available vector collections.
    
    **Returns:**
    - List of collections with metadata (name, vector count, dimension, status)
    """
)
async def list_collections(
    vector_store = Depends(get_vector_store)
) -> CollectionListResponse:
    """
    List all collections.
    
    Returns:
        CollectionListResponse with all collections
    """
    try:
        logger.info("Listing collections")
        
        # Get collections from Qdrant
        collection_names = vector_store.list_collections()
        
        # Get collection info for each
        collections = []
        for name in collection_names:
            try:
                info = vector_store.get_collection_info(name)
                collections.append(CollectionInfo(
                    name=info["name"],
                    vector_count=info["vector_count"],
                    dimension=info.get("dimension", 0),
                    status=info["status"],
                    created_at=datetime.utcnow(),
                    distance_metric="Cosine"  # Default, would need to store this
                ))
            except Exception as e:
                logger.warning("Failed to get collection info", collection=name, error=str(e))
                # Still include basic info
                collections.append(CollectionInfo(
                    name=name,
                    vector_count=0,
                    dimension=0,
                    status="unknown",
                    created_at=datetime.utcnow(),
                    distance_metric="Cosine"
                ))
        
        logger.info("Collections listed successfully", count=len(collections))
        
        return CollectionListResponse(
            collections=collections,
            total=len(collections)
        )
        
    except Exception as e:
        logger.error("Failed to list collections", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to list collections: {str(e)}"
            }
        )


@router.get(
    "/{collection_name}", 
    response_model=CollectionResponse,
    status_code=200,
    summary="Get collection information",
    description="""
    Retrieve detailed information about a specific collection.
    
    **Parameters:**
    - `collection_name`: Name of the collection to retrieve
    
    **Returns:**
    - Collection details including vector count, dimension, and status
    """
)
async def get_collection(
    collection_name: str,
    vector_store = Depends(get_vector_store)
) -> CollectionResponse:
    """
    Get collection information.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        CollectionResponse with collection details
    """
    validator = CollectionValidator()
    
    try:
        # Validate collection name
        validator.validate_collection_name(collection_name)
        
        logger.info("Getting collection info", collection=collection_name)
        
        # Get collection info
        info = vector_store.get_collection_info(collection_name)
        
        return CollectionResponse(
            collection=CollectionInfo(
                name=info["name"],
                vector_count=info["vector_count"],
                dimension=info.get("dimension", 0),
                status=info["status"],
                created_at=datetime.utcnow(),
                distance_metric="Cosine"
            ),
            message="Collection information retrieved successfully"
        )
        
    except CollectionNotFoundError as e:
        logger.error("Collection not found", collection=collection_name, error=str(e))
        raise HTTPException(
            status_code=404,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Failed to get collection", collection=collection_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to get collection: {str(e)}"
            }
        )


@router.delete(
    "/{collection_name}", 
    response_model=SuccessResponse,
    status_code=200,
    summary="Delete a collection",
    description="""
    Delete a collection and all its associated documents and vectors.
    
    **Warning:** This action is irreversible and will delete all documents and embeddings in the collection.
    
    **Parameters:**
    - `collection_name`: Name of the collection to delete
    
    **Returns:**
    - Success response confirming deletion
    """
)
async def delete_collection(
    collection_name: str,
    vector_store = Depends(get_vector_store),
    storage_manager = Depends(get_storage_manager)
) -> SuccessResponse:
    """
    Delete a collection and all its documents.
    
    Args:
        collection_name: Name of the collection to delete
        
    Returns:
        SuccessResponse
    """
    validator = CollectionValidator()
    
    try:
        # Validate collection name
        validator.validate_collection_name(collection_name)
        
        logger.info("Deleting collection", collection=collection_name)
        
        # Delete from vector store
        vector_store.delete_collection(collection_name)
        
        # Delete from storage
        storage_manager.delete_collection(collection_name)
        
        logger.info("Collection deleted successfully", collection=collection_name)
        
        return SuccessResponse(
            success=True,
            message=f"Collection '{collection_name}' deleted successfully"
        )
        
    except CollectionNotFoundError as e:
        logger.error("Collection not found", collection=collection_name, error=str(e))
        raise HTTPException(
            status_code=404,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Failed to delete collection", collection=collection_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to delete collection: {str(e)}"
            }
        )

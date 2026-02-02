"""
Embedding generation tasks for Celery.

This module contains Celery tasks for asynchronous embedding generation
and vector storage operations.
"""
from typing import List, Dict, Any, Optional

from src.tasks.celery_app import celery_app
from src.core.logging import get_logger
from src.core.exceptions import EmbeddingError, VectorStoreError
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore


logger = get_logger(__name__)


@celery_app.task(
    name="src.tasks.embedding_tasks.generate_embeddings_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="embeddings"
)
def generate_embeddings_task(
    self,
    chunks_data: List[Dict[str, Any]],
    collection: str,
    document_id: Optional[str] = None,
    filename: Optional[str] = None,
    model_name: Optional[str] = None,
    batch_size: int = 32
) -> Dict[str, Any]:
    """
    Generate embeddings for document chunks and store them in vector store.
    
    This task generates embeddings for all chunks and inserts them into
    the Qdrant vector store.
    
    Args:
        chunks_data: List of chunk dictionaries with text and metadata
        collection: Collection name to store vectors in
        document_id: Optional document ID
        filename: Optional filename
        model_name: Optional embedding model name override
        batch_size: Batch size for embedding generation
        
    Returns:
        Dictionary with embedding generation results
        
    Raises:
        EmbeddingError: If embedding generation fails
        VectorStoreError: If vector storage fails
    """
    try:
        logger.info(
            "Starting embedding generation task",
            collection=collection,
            chunk_count=len(chunks_data),
            document_id=document_id,
            filename=filename,
            task_id=self.request.id
        )

        if not chunks_data:
            logger.warning("No chunks to process", task_id=self.request.id)
            return {
                "success": True,
                "task_id": self.request.id,
                "collection": collection,
                "chunk_count": 0,
                "vectors_inserted": 0
            }

        # Validate chunks data
        for i, chunk in enumerate(chunks_data):
            if not isinstance(chunk, dict):
                logger.error(
                    f"Invalid chunk at index {i}: not a dictionary",
                    task_id=self.request.id
                )
                raise EmbeddingError(f"Chunk at index {i} is not a dictionary")
            if "text" not in chunk or not chunk["text"]:
                logger.error(
                    f"Invalid chunk at index {i}: missing or empty text",
                    task_id=self.request.id
                )
                raise EmbeddingError(f"Chunk at index {i} has missing or empty text")

        # Initialize services
        try:
            embedding_service = EmbeddingService(model_name=model_name)
            vector_store = VectorStore()
        except Exception as e:
            logger.error(
                "Failed to initialize services",
                error=str(e),
                error_type=type(e).__name__,
                task_id=self.request.id
            )
            raise EmbeddingError(f"Failed to initialize services: {str(e)}")

        # Extract chunk texts
        chunk_texts = [chunk["text"] for chunk in chunks_data]

        # Validate that we have text to embed
        if not chunk_texts or all(not text.strip() for text in chunk_texts):
            logger.error(
                "No valid text content found in chunks",
                chunk_count=len(chunk_texts),
                task_id=self.request.id
            )
            raise EmbeddingError("No valid text content found in chunks")

        # Generate embeddings with additional error handling
        try:
            embeddings = embedding_service.generate_embeddings(
                texts=chunk_texts,
                batch_size=batch_size
            )
        except Exception as e:
            logger.error(
                "Failed to generate embeddings",
                error=str(e),
                error_type=type(e).__name__,
                task_id=self.request.id,
                exc_info=True
            )
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")

        # Validate embeddings output
        if not embeddings:
            logger.error(
                "Embeddings generation returned empty list",
                chunk_count=len(chunk_texts),
                task_id=self.request.id
            )
            raise EmbeddingError("Embeddings generation returned empty list")

        if len(embeddings) != len(chunk_texts):
            logger.error(
                "Embeddings count mismatch",
                expected=len(chunk_texts),
                actual=len(embeddings),
                task_id=self.request.id
            )
            raise EmbeddingError(
                f"Embeddings count mismatch: expected {len(chunk_texts)}, got {len(embeddings)}"
            )

        logger.info(
            "Embeddings generated",
            collection=collection,
            chunk_count=len(chunks_data),
            embedding_count=len(embeddings),
            task_id=self.request.id
        )
        
        # Ensure collection exists
        if not vector_store.collection_exists(collection):
            vector_store.create_collection(
                collection_name=collection,
                dimension=embedding_service.get_dimension()
            )
            logger.info(
                "Collection created",
                collection=collection,
                dimension=embedding_service.get_dimension()
            )
        
        # Prepare payloads with metadata
        payloads = []
        for i, chunk_data in enumerate(chunks_data):
            payload = chunk_data.get("metadata", {}).copy()
            payload.update({
                "document_id": document_id or chunk_data.get("document_id"),
                "filename": filename or chunk_data.get("filename"),
                "chunk_index": chunk_data.get("chunk_index", i),
                "chunk_text": chunk_data["text"],
                "collection": collection
            })
            payloads.append(payload)
        
        # Insert vectors into Qdrant
        vector_store.insert_vectors(
            collection_name=collection,
            vectors=embeddings,
            payloads=payloads
        )
        
        logger.info(
            "Embedding generation and storage completed",
            collection=collection,
            chunk_count=len(chunks_data),
            vectors_inserted=len(embeddings),
            task_id=self.request.id
        )
        
        return {
            "success": True,
            "task_id": self.request.id,
            "collection": collection,
            "chunk_count": len(chunks_data),
            "vectors_inserted": len(embeddings),
            "document_id": document_id,
            "filename": filename
        }
        
    except (EmbeddingError, VectorStoreError) as e:
        logger.error(
            "Embedding generation failed",
            collection=collection,
            chunk_count=len(chunks_data) if chunks_data else 0,
            error=str(e),
            error_type=type(e).__name__,
            task_id=self.request.id,
            exc_info=True
        )
        # Don't retry on service errors - these are usually configuration or data issues
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in embedding generation task",
            collection=collection,
            chunk_count=len(chunks_data) if chunks_data else 0,
            error=str(e),
            error_type=type(e).__name__,
            task_id=self.request.id,
            exc_info=True
        )
        # Retry on unexpected errors (e.g., network issues)
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying embedding generation task",
                attempt=self.request.retries + 1,
                max_retries=self.max_retries,
                task_id=self.request.id
            )
            raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))
        else:
            logger.error(
                "Max retries exceeded for embedding generation task",
                collection=collection,
                task_id=self.request.id
            )
            raise


@celery_app.task(
    name="src.tasks.embedding_tasks.delete_vectors_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30
)
def delete_vectors_task(
    self,
    collection: str,
    filter_criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Delete vectors from vector store based on filter criteria.
    
    This task deletes vectors matching the provided filter criteria,
    typically used when deleting documents.
    
    Args:
        collection: Collection name
        filter_criteria: Dictionary with filter criteria (e.g., {"filename": "doc.pdf"})
        
    Returns:
        Dictionary with deletion results
    """
    try:
        logger.info(
            "Starting vector deletion task",
            collection=collection,
            filter_criteria=filter_criteria,
            task_id=self.request.id
        )
        
        vector_store = VectorStore()
        
        # Delete vectors
        vector_store.delete_vectors(
            collection_name=collection,
            payload_filter=filter_criteria
        )
        
        logger.info(
            "Vector deletion completed",
            collection=collection,
            filter_criteria=filter_criteria,
            task_id=self.request.id
        )
        
        return {
            "success": True,
            "task_id": self.request.id,
            "collection": collection,
            "filter_criteria": filter_criteria
        }
        
    except Exception as e:
        logger.error(
            "Error in vector deletion task",
            collection=collection,
            filter_criteria=filter_criteria,
            error=str(e),
            task_id=self.request.id,
            exc_info=True
        )
        raise self.retry(exc=e)

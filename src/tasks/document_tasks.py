"""
Document processing tasks for Celery.

This module contains Celery tasks for asynchronous document processing,
including parsing, chunking, and preparation for embedding.
"""
from pathlib import Path
from typing import Dict, Optional, Any

from src.tasks.celery_app import celery_app
from src.core.logging import get_logger
from src.core.exceptions import DocumentProcessingError
from src.services.document_processor import DocumentProcessor
from src.services.storage_manager import StorageManager


logger = get_logger(__name__)


@celery_app.task(
    name="src.tasks.document_tasks.process_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="documents"
)
def process_document_task(
    self,
    storage_path: str,
    collection: str,
    filename: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    chunker_type: str = "sentence",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a document asynchronously.
    
    This task parses a document, chunks it, and prepares it for embedding.
    After processing, it queues embedding generation tasks.
    
    Args:
        storage_path: Path to the stored document file
        collection: Collection name
        filename: Original filename
        chunk_size: Optional chunk size override
        chunk_overlap: Optional chunk overlap override
        chunker_type: Type of chunker to use
        metadata: Optional metadata to attach
        
    Returns:
        Dictionary with processing results including chunks
        
    Raises:
        DocumentProcessingError: If processing fails
    """
    try:
        logger.info(
            "Starting document processing task",
            storage_path=storage_path,
            collection=collection,
            filename=filename,
            task_id=self.request.id
        )
        
        # Initialize processor with parameters
        processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunker_type=chunker_type
        )
        
        # Process document
        result = processor.process_document(
            filepath=Path(storage_path),
            metadata=metadata
        )
        
        # Prepare chunk data for embedding
        chunks_data = []
        for i, chunk in enumerate(result["chunks"]):
            chunk_data = {
                "text": chunk.text,
                "metadata": chunk.metadata.copy(),
                "chunk_index": i,
                "document_id": metadata.get("document_id") if metadata else None,
                "filename": filename,
                "collection": collection
            }
            chunks_data.append(chunk_data)
        
        # Queue embedding generation task
        # Import here to avoid circular dependency
        from src.tasks import embedding_tasks

        # Queue the task - queue is specified in the task decorator
        embedding_task = embedding_tasks.generate_embeddings_task.apply_async(
            args=[chunks_data, collection],
            kwargs={
                "document_id": metadata.get("document_id") if metadata else None,
                "filename": filename
            }
        )
        
        logger.info(
            "Document processing completed, embedding task queued",
            storage_path=storage_path,
            collection=collection,
            filename=filename,
            chunk_count=len(chunks_data),
            embedding_task_id=embedding_task.id,
            task_id=self.request.id
        )
        
        return {
            "success": True,
            "task_id": self.request.id,
            "storage_path": storage_path,
            "collection": collection,
            "filename": filename,
            "chunk_count": len(chunks_data),
            "chunks": chunks_data,
            "embedding_task_id": embedding_task.id,
            "metadata": result.get("metadata", {})
        }
        
    except DocumentProcessingError as e:
        logger.error(
            "Document processing failed",
            storage_path=storage_path,
            collection=collection,
            filename=filename,
            error=str(e),
            task_id=self.request.id
        )
        # Don't retry on validation/processing errors
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in document processing task",
            storage_path=storage_path,
            collection=collection,
            filename=filename,
            error=str(e),
            task_id=self.request.id,
            exc_info=True
        )
        # Retry on unexpected errors
        raise self.retry(exc=e)


@celery_app.task(
    name="src.tasks.document_tasks.delete_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30
)
def delete_document_task(
    self,
    collection: str,
    filename: str
) -> Dict[str, Any]:
    """
    Delete a document and its associated data asynchronously.
    
    This task deletes the document file and removes associated vectors
    from the vector store.
    
    Args:
        collection: Collection name
        filename: Document filename
        
    Returns:
        Dictionary with deletion results
    """
    try:
        logger.info(
            "Starting document deletion task",
            collection=collection,
            filename=filename,
            task_id=self.request.id
        )
        
        # Initialize storage manager
        storage_manager = StorageManager()
        
        # Delete file from storage
        storage_manager.delete_file(filename, collection)
        
        # Delete vectors will be handled by a separate task or endpoint
        # to avoid circular dependencies
        
        logger.info(
            "Document deletion completed",
            collection=collection,
            filename=filename,
            task_id=self.request.id
        )
        
        return {
            "success": True,
            "task_id": self.request.id,
            "collection": collection,
            "filename": filename
        }
        
    except Exception as e:
        logger.error(
            "Error in document deletion task",
            collection=collection,
            filename=filename,
            error=str(e),
            task_id=self.request.id,
            exc_info=True
        )
        raise self.retry(exc=e)

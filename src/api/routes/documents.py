"""
Document management endpoints.
"""
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse

from src.core.logging import get_logger
from src.core.exceptions import (
    DocumentValidationError,
    DocumentProcessingError,
    ServiceError,
    FileNotFoundError as CoreFileNotFoundError
)
from src.utils.helpers import generate_id
from src.core.config import get_config
from src.api.models.document import (
    DocumentUploadRequest,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunkResponse,
    DocumentUploadTaskResponse
)
from src.api.models.task import TaskResponse, TaskStatus
from src.tasks.document_tasks import process_document_task
from celery.result import AsyncResult
from src.api.models.common import SuccessResponse
from src.api.dependencies import (
    get_storage_manager,
    get_document_processor,
    get_embedding_service,
    get_vector_store
)
from src.utils.validators import DocumentValidator


logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload", 
    response_model=DocumentUploadTaskResponse,
    status_code=202,
    summary="Upload a document",
    description="""
    Upload a document for asynchronous processing.
    
    This endpoint accepts a file upload (PDF, TXT, MD, DOCX), saves it to storage, 
    and queues it for background processing (parse, chunk, embed, store).
    
    **Supported file formats:** PDF, TXT, Markdown, DOCX
    
    **Parameters:**
    - `file`: Document file to upload
    - `collection`: Collection name to store the document in
    - `chunk_size`: Chunk size in characters (default: 1000)
    - `chunk_overlap`: Chunk overlap in characters (default: 200)
    - `chunker_type`: Type of chunker (character, word, sentence, paragraph, recursive)
    
    **Returns:**
    - Task response with task_id (use this to check processing status via Tasks API)
    """
)
async def upload_document(
    file: UploadFile,
    collection: str = Form(...),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
    chunker_type: str = Form("sentence"),
    storage_manager = Depends(get_storage_manager)
) -> DocumentUploadTaskResponse:
    """
    Upload a document for asynchronous processing.
    
    This endpoint accepts a file upload, saves it to storage, and queues
    it for background processing (parse, chunk, embed, store).
    
    Args:
        file: Uploaded file
        collection: Collection to store document in
        chunk_size: Optional chunk size
        chunk_overlap: Optional chunk overlap
        chunker_type: Type of chunker to use
        
    Returns:
        DocumentUploadTaskResponse with task ID and status
    """
    config = get_config()
    validator = DocumentValidator()
    
    try:
        # Read file content first to get accurate file size
        content = await file.read()
        file_size = len(content)
        
        # Validate file
        validator.validate_document(file.filename, file_size)
        
        logger.info(
            "Document upload requested",
            filename=file.filename,
            collection=collection,
            file_size=file_size
        )
        
        # Save file to storage
        storage_path = storage_manager.save_file(content, file.filename, collection)
        
        # Generate document ID
        document_id = generate_id()
        
        # Prepare metadata
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "collection": collection,
            "file_size": file_size
        }
        
        # Queue document processing task
        task = process_document_task.delay(
            storage_path=str(storage_path),
            collection=collection,
            filename=file.filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunker_type=chunker_type,
            metadata=metadata
        )
        
        logger.info(
            "Document upload task queued",
            filename=file.filename,
            collection=collection,
            document_id=document_id,
            task_id=task.id
        )
        
        return DocumentUploadTaskResponse(
            task_id=task.id,
            document_id=document_id,
            filename=file.filename,
            collection=collection,
            status="PENDING",
            message="Document upload queued for processing"
        )
        
    except (DocumentValidationError, DocumentProcessingError) as e:
        logger.error("Document validation/processing failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    except ServiceError as e:
        logger.error("Document service error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error during document upload", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to upload document: {str(e)}"
            }
        )


@router.get(
    "/list/{collection}", 
    response_model=DocumentListResponse,
    status_code=200,
    summary="List documents in a collection",
    description="""
    Retrieve a list of all documents in a specific collection.
    
    **Parameters:**
    - `collection`: Name of the collection
    
    **Returns:**
    - List of documents with metadata (filename, document_id, chunk_count)
    """
)
async def list_documents(
    collection: str,
    storage_manager = Depends(get_storage_manager)
) -> DocumentListResponse:
    """
    List all documents in a collection.
    
    Args:
        collection: Collection name
        
    Returns:
        DocumentListResponse with documents
    """
    try:
        logger.info("Listing documents", collection=collection)
        
        # Get files from storage
        files = storage_manager.list_files(collection)
        
        # Prepare document responses
        documents = []
        for filename in files:
            documents.append(DocumentResponse(
                document_id=generate_id(),
                filename=filename,
                collection=collection,
                chunk_count=0,  # Would need metadata for actual count
                metadata={}
            ))
        
        logger.info("Documents listed successfully", collection=collection, count=len(documents))
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            collection=collection
        )
        
    except Exception as e:
        logger.error("Failed to list documents", collection=collection, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to list documents: {str(e)}"
            }
        )


@router.delete(
    "/{collection}/{filename}", 
    response_model=SuccessResponse,
    status_code=200,
    summary="Delete a document",
    description="""
    Delete a document and all its associated chunks from the vector store.
    
    **Warning:** This action is irreversible and will remove the document and all its embeddings.
    
    **Parameters:**
    - `collection`: Collection name
    - `filename`: Document filename to delete
    
    **Returns:**
    - Success response confirming deletion
    """
)
async def delete_document(
    collection: str,
    filename: str,
    storage_manager = Depends(get_storage_manager),
    vector_store = Depends(get_vector_store)
) -> SuccessResponse:
    """
    Delete a document and its chunks from vector store.
    
    Args:
        collection: Collection name
        filename: Document filename
        
    Returns:
        SuccessResponse
    """
    try:
        logger.info("Deleting document", collection=collection, filename=filename)
        
        # Delete file from storage
        storage_manager.delete_file(filename, collection)
        
        # Delete vectors from vector store (by filename filter)
        vector_store.delete_vectors(
            collection_name=collection,
            payload_filter={"filename": filename}
        )
        
        logger.info(
            "Document deleted successfully",
            collection=collection,
            filename=filename
        )
        
        return SuccessResponse(
            success=True,
            message=f"Document '{filename}' deleted successfully from collection '{collection}'"
        )
        
    except CoreFileNotFoundError as e:
        logger.error("Document not found", collection=collection, filename=filename, error=str(e))
        raise HTTPException(
            status_code=404,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Failed to delete document", collection=collection, filename=filename, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to delete document: {str(e)}"
            }
        )


@router.get(
    "/download/{collection}/{filename}",
    status_code=200,
    summary="Download a document",
    description="""
    Download the original document file from storage.
    
    **Parameters:**
    - `collection`: Collection name
    - `filename`: Document filename to download
    
    **Returns:**
    - File response with the document content
    """
)
async def download_document(
    collection: str,
    filename: str,
    storage_manager = Depends(get_storage_manager)
) -> FileResponse:
    """
    Download a document file.
    
    Args:
        collection: Collection name
        filename: Document filename
        
    Returns:
        File response with document content
    """
    try:
        logger.info("Downloading document", collection=collection, filename=filename)
        
        # Get file content
        content = storage_manager.get_file(filename, collection)
        
        # Get file path for proper MIME type
        config = get_config()
        collection_path = Path(config.storage.storage_path) / collection / filename
        
        # Determine MIME type based on extension
        ext = filename.split(".")[-1].lower()
        mime_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "md": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        media_type = mime_types.get(ext, "application/octet-stream")
        
        logger.info("Document download successful", collection=collection, filename=filename)
        
        return FileResponse(
            path=str(collection_path),
            media_type=media_type,
            filename=filename
        )
        
    except CoreFileNotFoundError as e:
        logger.error("Document not found", collection=collection, filename=filename, error=str(e))
        raise HTTPException(
            status_code=404,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Failed to download document", collection=collection, filename=filename, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to download document: {str(e)}"
            }
        )

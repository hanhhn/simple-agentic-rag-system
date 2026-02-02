"""
Query processor service for RAG pipeline.
"""
import time
from typing import List, Dict, Optional

from src.core.logging import get_logger
from src.core.exceptions import ServiceError
from src.core.config import get_config
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore
from src.services.llm_service import LLMService
from src.services.storage_manager import StorageManager
from src.utils.validators import QueryValidator


logger = get_logger(__name__)


class QueryProcessor:
    """
    Service for processing queries through the RAG pipeline.
    
    This class orchestrates the complete RAG pipeline:
    1. Embed the query
    2. Search for relevant documents
    3. Generate response using LLM with context
    
    Example:
        >>> processor = QueryProcessor()
        >>> result = processor.process_query("What is RAG?", "my_collection")
        >>> print(result["answer"])
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        llm_service: Optional[LLMService] = None
    ) -> None:
        """
        Initialize query processor.
        
        Args:
            embedding_service: Service for generating embeddings
            vector_store: Service for vector operations
            llm_service: Service for LLM generation
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.llm_service = llm_service or LLMService()
        
        self.validator = QueryValidator()
        
        logger.info("Query processor initialized")
    
    def process_query(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        use_rag: bool = True
    ) -> Dict[str, any]:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query: User's question
            collection_name: Collection to search
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score
            use_rag: Whether to use RAG (otherwise return raw results)
            
        Returns:
            Dictionary with query results including answer, retrieved documents, etc.
            
        Example:
            >>> processor = QueryProcessor()
            >>> result = processor.process_query("What is RAG?", "my_collection")
            >>> print(result["answer"])
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            validation_start = time.time()
            self.validator.validate_search_params(query, top_k, score_threshold)
            validation_elapsed = time.time() - validation_start
            
            logger.info(
                "Starting RAG query processing",
                query=query[:100],
                query_length=len(query),
                collection=collection_name,
                top_k=top_k,
                score_threshold=score_threshold,
                use_rag=use_rag
            )
            
            # Embed query
            embedding_start = time.time()
            query_embedding = self.embedding_service.generate_embedding(query)
            embedding_elapsed = time.time() - embedding_start
            
            logger.info(
                "Query embedded",
                embedding_dimension=len(query_embedding),
                embedding_time=f"{embedding_elapsed:.4f}s"
            )
            
            # Search for similar documents
            search_start = time.time()
            search_results = self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                top_k=top_k,
                score_threshold=score_threshold
            )
            search_elapsed = time.time() - search_start
            
            logger.info(
                "Vector search completed",
                collection=collection_name,
                results_count=len(search_results),
                search_time=f"{search_elapsed:.4f}s",
                avg_score=f"{sum(doc.get('score', 0) for doc in search_results) / len(search_results):.4f}" if search_results else "0"
            )
            
            # Prepare result
            result = {
                "query": query,
                "collection": collection_name,
                "retrieved_documents": search_results,
                "retrieval_count": len(search_results),
                "top_k": top_k,
                "score_threshold": score_threshold
            }
            
            rag_start = time.time()
            if use_rag and search_results:
                # Generate RAG response
                contexts = [doc.get("payload", {}).get("text", "") for doc in search_results]
                total_context_length = sum(len(ctx) for ctx in contexts)
                
                logger.info(
                    "Preparing RAG context",
                    context_count=len(contexts),
                    total_context_length=total_context_length
                )
                
                answer = self.llm_service.generate_rag(query, contexts)
                rag_elapsed = time.time() - rag_start
                
                result["answer"] = answer
                result["context_count"] = len(contexts)
                
                logger.info(
                    "RAG generation completed",
                    answer_length=len(answer),
                    rag_time=f"{rag_elapsed:.4f}s"
                )
            else:
                rag_elapsed = 0
                result["answer"] = None
                result["context_count"] = 0
                logger.info("Skipping RAG generation", reason="use_rag=False or no results")
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Query processed successfully",
                query=query[:100],
                collection=collection_name,
                retrieval_count=len(search_results),
                has_answer=use_rag and bool(search_results),
                validation_time=f"{validation_elapsed:.6f}s",
                embedding_time=f"{embedding_elapsed:.4f}s",
                search_time=f"{search_elapsed:.4f}s",
                rag_time=f"{rag_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s"
            )
            
            return result
            
        except ServiceError:
            elapsed = time.time() - start_time
            logger.error(
                "Query processing failed (ServiceError)",
                query=query[:100],
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to process query",
                query=query[:100],
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise ServiceError(
                f"Failed to process query: {str(e)}",
                details={
                    "query": query[:100],
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def process_query_stream(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> Dict[str, any]:
        """
        Process a query with streaming RAG response.
        
        Args:
            query: User's question
            collection_name: Collection to search
            top_k: Number of documents to retrieve
            score_threshold: Minimum similarity score
            
        Returns:
            Dictionary with query results including streaming answer chunks
            
        Example:
            >>> processor = QueryProcessor()
            >>> result = processor.process_query_stream("What is RAG?", "my_collection")
            >>> for chunk in result["answer_chunks"]:
            ...     print(chunk, end='')
        """
        try:
            # Validate inputs
            self.validator.validate_search_params(query, top_k, score_threshold)
            
            logger.info(
                "Processing query (streaming)",
                query=query[:100],
                collection=collection_name,
                top_k=top_k
            )
            
            # Embed query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search for similar documents
            search_results = self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            # Prepare result
            result = {
                "query": query,
                "collection": collection_name,
                "retrieved_documents": search_results,
                "retrieval_count": len(search_results),
                "top_k": top_k,
                "score_threshold": score_threshold
            }
            
            if search_results:
                # Generate streaming RAG response
                contexts = [doc.get("payload", {}).get("text", "") for doc in search_results]
                answer_chunks = self.llm_service.generate_rag_stream(query, contexts)
                result["answer_chunks"] = answer_chunks
                result["answer"] = "".join(answer_chunks)
                result["context_count"] = len(contexts)
            else:
                result["answer_chunks"] = []
                result["answer"] = None
                result["context_count"] = 0
            
            logger.info(
                "Query processed successfully (streaming)",
                query=query[:100],
                retrieval_count=len(search_results),
                chunk_count=len(result.get("answer_chunks", []))
            )
            
            return result
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error("Failed to process query stream", query=query[:100], error=str(e))
            raise ServiceError(
                f"Failed to process query stream: {str(e)}",
                details={"query": query[:100], "error": str(e)}
            )
    
    def create_collection(
        self,
        collection_name: str,
        dimension: Optional[int] = None
    ) -> None:
        """
        Create a new vector collection.
        
        Args:
            collection_name: Name of the collection
            dimension: Embedding dimension (uses model default if None)
        """
        try:
            # Get dimension from embedding service
            dim = dimension or self.embedding_service.get_dimension()
            
            self.vector_store.create_collection(collection_name, dim)
            
            logger.info("Collection created for queries", collection=collection_name, dimension=dim)
            
        except Exception as e:
            logger.error("Failed to create collection", collection=collection_name, error=str(e))
            raise ServiceError(
                f"Failed to create collection: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )

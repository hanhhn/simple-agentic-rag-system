"""
Vector store service using Qdrant.
"""
import uuid
from typing import List, Optional, Dict, Any

import httpx
from qdrant_client import QdrantClient, models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.logging import get_logger
from src.core.exceptions import (
    VectorStoreError,
    CollectionNotFoundError,
    CollectionCreationError,
    VectorInsertionError,
    VectorSearchError,
    VectorStoreConnectionError
)
from src.core.config import get_config


logger = get_logger(__name__)


class VectorStore:
    """
    Qdrant vector store for embeddings.
    
    This class manages Qdrant operations including creating collections,
    inserting vectors, searching, and managing metadata.
    
    Example:
        >>> store = VectorStore()
        >>> store.create_collection("my_collection", dimension=384)
        >>> results = store.search("my_collection", query_vector, top_k=5)
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> None:
        """
        Initialize Qdrant client.
        
        Args:
            url: Qdrant server URL (uses config default if None)
            api_key: Qdrant API key (uses config default if None)
            timeout: Request timeout (uses config default if None)
        """
        config = get_config()
        
        self.url = url or config.qdrant.url
        self.api_key = api_key or config.qdrant.api_key
        self.timeout = timeout or config.qdrant.timeout
        
        # Initialize Qdrant client
        try:
            if self.api_key:
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=self.timeout
                )
            else:
                self.client = QdrantClient(
                    url=self.url,
                    timeout=self.timeout
                )
            
            # Test connection
            self.client.get_collections()
            
            logger.info(
                "Qdrant client initialized",
                url=self.url,
                timeout=self.timeout
            )
            
        except Exception as e:
            logger.error("Failed to connect to Qdrant", error=str(e))
            raise VectorStoreConnectionError(
                f"Failed to connect to Qdrant: {str(e)}",
                details={"url": self.url, "error": str(e)}
            )
    
    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        distance_metric: str = "Cosine"
    ) -> None:
        """
        Create a new collection in Qdrant.
        
        Args:
            collection_name: Name of the collection
            dimension: Vector dimension
            distance_metric: Distance metric ("Cosine", "Euclid", "Dot")
            
        Raises:
            CollectionCreationError: If creation fails
            
        Example:
            >>> store = VectorStore()
            >>> store.create_collection("my_collection", dimension=384)
        """
        from src.utils.validators import CollectionValidator
        
        validator = CollectionValidator()
        validator.validate_collection_name(collection_name)
        validator.validate_embedding_dimension(dimension)
        
        try:
            # Map distance metric
            distance_map = {
                "Cosine": qdrant_models.Distance.COSINE,
                "Euclid": qdrant_models.Distance.EUCLID,
                "Dot": qdrant_models.Distance.DOT
            }
            
            if distance_metric not in distance_map:
                raise ValueError(f"Invalid distance metric: {distance_metric}")
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=dimension,
                    distance=distance_map[distance_metric]
                )
            )
            
            logger.info(
                "Collection created successfully",
                collection=collection_name,
                dimension=dimension,
                distance_metric=distance_metric
            )
            
        except UnexpectedResponse as e:
            if e.status_code == 400:
                logger.warning(
                    "Collection already exists",
                    collection=collection_name,
                    error=str(e)
                )
                # Collection already exists, this is okay
                return
            raise
        except Exception as e:
            logger.error("Failed to create collection", collection=collection_name, error=str(e))
            raise CollectionCreationError(
                f"Failed to create collection '{collection_name}': {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection from Qdrant.
        
        Args:
            collection_name: Name of the collection
            
        Example:
            >>> store = VectorStore()
            >>> store.delete_collection("my_collection")
        """
        try:
            self.client.delete_collection(collection_name=collection_name)
            
            logger.info("Collection deleted successfully", collection=collection_name)
            
        except Exception as e:
            logger.error("Failed to delete collection", collection=collection_name, error=str(e))
            raise VectorStoreError(
                f"Failed to delete collection '{collection_name}': {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.get_collections()
            return collection_name in [c.name for c in collections.collections]
        except Exception as e:
            logger.error("Failed to check collection existence", collection=collection_name, error=str(e))
            return False
    
    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Insert vectors into a collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of embedding vectors
            payloads: Optional list of payload dictionaries
            ids: Optional list of point IDs
            
        Raises:
            VectorInsertionError: If insertion fails
            
        Example:
            >>> store = VectorStore()
            >>> store.insert_vectors(
            ...     collection_name="my_collection",
            ...     vectors=[[0.1, 0.2], [0.3, 0.4]],
            ...     payloads=[{"text": "doc1"}, {"text": "doc2"}]
            ... )
        """
        if not vectors:
            logger.warning("No vectors to insert", collection=collection_name)
            return
        
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' does not exist",
                details={"collection": collection_name}
            )
        
        try:
            # Validate vectors
            if not vectors or len(vectors) == 0:
                logger.warning("No vectors to insert", collection=collection_name)
                return
            
            # Validate vector dimensions (check first vector)
            if vectors[0] and len(vectors[0]) > 0:
                vector_dim = len(vectors[0])
                logger.info(
                    "Validating vectors",
                    collection=collection_name,
                    count=len(vectors),
                    dimension=vector_dim
                )
            
            # Generate IDs if not provided
            if ids is None:
                ids = []
                for i in range(len(vectors)):
                    # Use UUID for each point (most reliable format)
                    point_id = str(uuid.uuid4())
                    ids.append(point_id)
            
            logger.info(
                "Preparing points for insertion",
                collection=collection_name,
                point_count=len(vectors),
                sample_ids=ids[:3] if len(ids) > 3 else ids
            )
            
            # Create points
            points = []
            for i, (vector, point_id) in enumerate(zip(vectors, ids)):
                point = qdrant_models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payloads[i] if payloads and i < len(payloads) else None
                )
                points.append(point)
            
            # Insert points
            logger.info(
                "Inserting points into Qdrant",
                collection=collection_name,
                point_count=len(points)
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(
                "Vectors inserted successfully",
                collection=collection_name,
                count=len(vectors)
            )
            
        except Exception as e:
            logger.error("Failed to insert vectors", collection=collection_name, error=str(e))
            raise VectorInsertionError(
                f"Failed to insert vectors: {str(e)}",
                details={"collection": collection_name, "count": len(vectors), "error": str(e)}
            )
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        payload_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in a collection.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            payload_filter: Optional filter for payload fields
            
        Returns:
            List of search results with scores and payloads
            
        Raises:
            VectorSearchError: If search fails
            CollectionNotFoundError: If collection doesn't exist
            
        Example:
            >>> store = VectorStore()
            >>> results = store.search(
            ...     collection_name="my_collection",
            ...     query_vector=[0.1, 0.2, ...],
            ...     top_k=5
            ... )
        """
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' does not exist",
                details={"collection": collection_name}
            )
        
        try:
            # Search vectors
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=self._build_filter(payload_filter) if payload_filter else None
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload or {},
                    "vector": result.vector
                })
            
            logger.info(
                "Search completed successfully",
                collection=collection_name,
                results=len(formatted_results),
                top_k=top_k
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error("Search failed", collection=collection_name, error=str(e))
            raise VectorSearchError(
                f"Search failed: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def delete_vectors(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        payload_filter: Optional[Dict] = None
    ) -> None:
        """
        Delete vectors from a collection.
        
        Args:
            collection_name: Name of the collection
            ids: Optional list of point IDs to delete
            payload_filter: Optional filter for payload fields
            
        Example:
            >>> store = VectorStore()
            >>> store.delete_vectors(
            ...     collection_name="my_collection",
            ...     ids=["point_1", "point_2"]
            ... )
        """
        if not self.collection_exists(collection_name):
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' does not exist",
                details={"collection": collection_name}
            )
        
        try:
            if ids:
                # Delete by IDs
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=qdrant_models.PointIdsList(ids=ids)
                )
                
                logger.info(
                    "Vectors deleted by ID",
                    collection=collection_name,
                    count=len(ids)
                )
            elif payload_filter:
                # Delete by filter
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=self._build_filter(payload_filter)
                )
                
                logger.info(
                    "Vectors deleted by filter",
                    collection=collection_name,
                    filter=payload_filter
                )
            else:
                logger.warning("No IDs or filter provided for deletion")
                
        except Exception as e:
            logger.error("Failed to delete vectors", collection=collection_name, error=str(e))
            raise VectorStoreError(
                f"Failed to delete vectors: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection information
            
        Raises:
            CollectionNotFoundError: If collection doesn't exist
        """
        try:
            # Use raw API call to avoid Pydantic validation issues with Qdrant client
            response = httpx.get(
                f"{self.url}/collections/{collection_name}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            result = data.get("result", {})
            config = result.get("config", {})
            params = config.get("params", {})
            vectors = params.get("vectors", {})
            
            # Handle both dict and object formats
            if isinstance(vectors, dict):
                dimension = vectors.get("size")
            else:
                dimension = getattr(vectors, "size", None)
            
            return {
                "name": collection_name,
                "dimension": dimension,
                "vector_count": result.get("points_count", 0),
                "status": result.get("status", "unknown"),
                "optimizer_status": result.get("optimizer_status", {}),
                "indexed": result.get("indexed_vectors_count", 0)
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CollectionNotFoundError(
                    f"Collection '{collection_name}' does not exist",
                    details={"collection": collection_name}
                )
            logger.error("Failed to get collection info", collection=collection_name, error=str(e))
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' not found: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
        except Exception as e:
            logger.error("Failed to get collection info", collection=collection_name, error=str(e))
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' not found: {str(e)}",
                details={"collection": collection_name, "error": str(e)}
            )
    
    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            raise VectorStoreError(
                f"Failed to list collections: {str(e)}",
                details={"error": str(e)}
            )
    
    def _build_filter(self, filter_dict: Dict) -> qdrant_models.Filter:
        """
        Build a Qdrant filter from a dictionary.
        
        Args:
            filter_dict: Dictionary of field: value pairs
            
        Returns:
            Qdrant Filter object
        """
        conditions = []
        
        for field, value in filter_dict.items():
            if isinstance(value, str):
                conditions.append(
                    qdrant_models.FieldCondition(
                        key=field,
                        match=qdrant_models.MatchValue(value=value)
                    )
                )
            elif isinstance(value, list):
                conditions.append(
                    qdrant_models.FieldCondition(
                        key=field,
                        match=qdrant_models.MatchAny(any=value)
                    )
                )
            else:
                logger.warning(
                    "Unsupported filter value type",
                    field=field,
                    type=type(value)
                )
        
        if conditions:
            return qdrant_models.Filter(must=conditions)
        
        return None
    
    def close(self) -> None:
        """Close Qdrant client connection."""
        try:
            self.client.close()
            logger.info("Qdrant client closed")
        except Exception as e:
            logger.warning("Failed to close Qdrant client", error=str(e))

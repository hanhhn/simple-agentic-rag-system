"""
Tool interface and implementations for agent capabilities.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json

from src.core.logging import get_logger
from src.core.exceptions import AgentError


logger = get_logger(__name__)


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    RETRIEVAL = "retrieval"  # Document retrieval and search
    SEARCH = "search"  # External web search
    CALCULATION = "calculation"  # Mathematical operations
    ANALYSIS = "analysis"  # Data analysis and processing
    GENERATION = "generation"  # Content generation
    KNOWLEDGE = "knowledge"  # Knowledge base queries
    UTILITY = "utility"  # Helper functions


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM consumption."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }

    def to_string(self) -> str:
        """Convert to string for LLM prompt."""
        if self.success:
            return json.dumps({
                "status": "success",
                "result": self.data
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "error": self.error
            }, indent=2)


class Tool(ABC):
    """
    Base class for agent tools.
    
    Tools are callable functions that agents can use to perform actions.
    Each tool has a name, description, and callable implementation.
    
    Example:
        >>> class MyTool(Tool):
        ...     def execute(self, **kwargs):
        ...         return ToolResult(success=True, data="Hello!")
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.UTILITY,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a tool.
        
        Args:
            name: Unique tool name
            description: Description of what the tool does (for LLM)
            category: Tool category
            parameters: Schema of required parameters
        """
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters or {}
        
        logger.debug(
            "Tool initialized",
            name=name,
            category=category.value,
            parameters=list(self.parameters.keys())
        )
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    def validate_parameters(self, kwargs: Dict[str, Any]) -> bool:
        """
        Validate that required parameters are provided.
        
        Args:
            kwargs: Parameters to validate
            
        Returns:
            True if valid, raises AgentError if not
        """
        for param, schema in self.parameters.items():
            if schema.get("required", False) and param not in kwargs:
                raise AgentError(
                    f"Missing required parameter: {param}",
                    details={"tool": self.name, "missing_param": param}
                )
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for LLM context."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters
        }


class RetrievalTool(Tool):
    """Tool for retrieving documents from the knowledge base."""
    
    def __init__(self, vector_store, embedding_service):
        """
        Initialize retrieval tool.
        
        Args:
            vector_store: Vector store service
            embedding_service: Embedding service for query encoding
        """
        super().__init__(
            name="retrieve_documents",
            description="Retrieve relevant documents from the knowledge base using semantic search. Use this when you need information from uploaded documents.",
            category=ToolCategory.RETRIEVAL,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query text",
                    "required": True
                },
                "collection": {
                    "type": "string",
                    "description": "Collection name to search",
                    "required": True
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of documents to retrieve (default: 5)",
                    "required": False,
                    "default": 5
                },
                "score_threshold": {
                    "type": "float",
                    "description": "Minimum similarity score (default: 0.0)",
                    "required": False,
                    "default": 0.0
                }
            }
        )
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute document retrieval."""
        import time
        start_time = time.time()
        
        try:
            # Validate parameters
            self.validate_parameters(kwargs)
            
            # Extract parameters with defaults
            query = kwargs["query"]
            collection = kwargs["collection"]
            top_k = kwargs.get("top_k", 5)
            score_threshold = kwargs.get("score_threshold", 0.0)
            
            logger.info(
                "Executing retrieval tool",
                query=query[:100],
                collection=collection,
                top_k=top_k
            )
            
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search vector store
            results = self.vector_store.search(
                collection_name=collection,
                query_vector=query_embedding,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.get("payload", {}).get("text", ""),
                    "score": result.get("score", 0),
                    "metadata": result.get("payload", {})
                })
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Retrieval tool executed successfully",
                results_count=len(formatted_results),
                execution_time=f"{execution_time:.4f}s"
            )
            
            return ToolResult(
                success=True,
                data={
                    "documents": formatted_results,
                    "count": len(formatted_results)
                },
                metadata={
                    "execution_time": execution_time,
                    "top_k": top_k,
                    "collection": collection
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Retrieval tool failed", error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"execution_time": execution_time}
            )


class CalculatorTool(Tool):
    """Tool for mathematical calculations."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations. Supports basic arithmetic operations: +, -, *, /, **, %. Returns the result as a number.",
            category=ToolCategory.CALCULATION,
            parameters={
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')",
                    "required": True
                }
            }
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute calculation."""
        import time
        start_time = time.time()
        
        try:
            self.validate_parameters(kwargs)
            expression = kwargs["expression"]
            
            logger.info("Executing calculator tool", expression=expression)
            
            # Safe evaluation using eval with restricted globals
            allowed_names = {
                "__builtins__": {
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "round": round,
                    "pow": pow,
                    "sum": sum,
                }
            }
            
            result = eval(expression, allowed_names)
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Calculator tool executed successfully",
                result=result,
                execution_time=f"{execution_time:.4f}s"
            )
            
            return ToolResult(
                success=True,
                data={"result": result, "expression": expression},
                metadata={"execution_time": execution_time}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Calculator tool failed", expression=kwargs.get("expression"), error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to calculate: {str(e)}",
                metadata={"execution_time": execution_time}
            )


class WebSearchTool(Tool):
    """Tool for web search functionality."""
    
    def __init__(self, search_engine: Optional[Any] = None):
        """
        Initialize web search tool.
        
        Args:
            search_engine: Optional search engine instance (for future web API integration)
        """
        super().__init__(
            name="web_search",
            description="Search the web for information. Returns search results with titles, snippets, and URLs.",
            category=ToolCategory.SEARCH,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query text",
                    "required": True
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "required": False,
                    "default": 5
                }
            }
        )
        self.search_engine = search_engine
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute web search."""
        import time
        start_time = time.time()
        
        try:
            self.validate_parameters(kwargs)
            query = kwargs["query"]
            num_results = kwargs.get("num_results", 5)
            
            logger.info("Executing web search tool", query=query)
            
            # Note: This is a placeholder. In production, integrate with actual search APIs
            # like Google Custom Search, Bing Search, or Tavily API
            results = [
                {
                    "title": f"Search result for: {query}",
                    "snippet": f"This is a placeholder result. To enable real web search, integrate with a search API.",
                    "url": f"https://example.com/search?q={query}"
                }
            ] * num_results
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Web search tool executed",
                results_count=len(results),
                execution_time=f"{execution_time:.4f}s"
            )
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results)
                },
                metadata={"execution_time": execution_time}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Web search tool failed", error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"execution_time": execution_time}
            )


class SummaryTool(Tool):
    """Tool for summarizing text."""
    
    def __init__(self, llm_service):
        """
        Initialize summary tool.
        
        Args:
            llm_service: LLM service for generation
        """
        super().__init__(
            name="summarize",
            description="Summarize a piece of text. Extracts key points and creates a concise summary.",
            category=ToolCategory.GENERATION,
            parameters={
                "text": {
                    "type": "string",
                    "description": "Text to summarize",
                    "required": True
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of summary in words (default: 200)",
                    "required": False,
                    "default": 200
                }
            }
        )
        self.llm_service = llm_service
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute text summarization."""
        import time
        start_time = time.time()
        
        try:
            self.validate_parameters(kwargs)
            text = kwargs["text"]
            max_length = kwargs.get("max_length", 200)
            
            logger.info(
                "Executing summary tool",
                text_length=len(text),
                max_length=max_length
            )
            
            # Generate summary
            summary = self.llm_service.summarize(text, max_length=max_length)
            
            execution_time = time.time() - start_time
            
            logger.info(
                "Summary tool executed successfully",
                original_length=len(text),
                summary_length=len(summary),
                execution_time=f"{execution_time:.4f}s"
            )
            
            return ToolResult(
                success=True,
                data={
                    "summary": summary,
                    "original_length": len(text),
                    "summary_length": len(summary)
                },
                metadata={"execution_time": execution_time}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Summary tool failed", error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"execution_time": execution_time}
            )

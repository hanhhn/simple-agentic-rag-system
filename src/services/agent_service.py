"""
Agent service for managing intelligent RAG agents.
"""
from typing import Any, Dict, List, Optional
import time

from src.core.logging import get_logger
from src.core.exceptions import AgentError
from src.agents.base_agent import BaseAgent, AgentResponse
from src.agents.react_agent import ReActAgent
from src.agents.memory import ConversationMemory, VectorMemory
from src.agents.planner import QueryPlanner
from src.agents.tool import (
    Tool,
    RetrievalTool,
    CalculatorTool,
    SummaryTool,
    WebSearchTool
)
from src.services.llm_service import LLMService
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import VectorStore


logger = get_logger(__name__)


class AgentService:
    """
    Service for creating and managing agents.
    
    Provides high-level interface for using agentic RAG capabilities.
    
    Example:
        >>> service = AgentService(llm_service, vector_store, embedding_service)
        >>> agent = service.create_react_agent()
        >>> response = await agent.run("What is RAG?", collection="docs")
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        use_memory: bool = True,
        max_iterations: int = 10,
        verbose: bool = False
    ):
        """
        Initialize agent service.
        
        Args:
            llm_service: LLM service
            vector_store: Vector store
            embedding_service: Embedding service
            use_memory: Whether to use conversation memory
            max_iterations: Max agent reasoning iterations
            verbose: Verbose logging
        """
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.use_memory = use_memory
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Initialize memory
        self.memory = ConversationMemory() if use_memory else None
        
        logger.info(
            "Agent service initialized",
            tools_count=len(self.tools),
            use_memory=use_memory,
            max_iterations=max_iterations
        )
    
    def _initialize_tools(self) -> List[Tool]:
        """Initialize available tools."""
        tools = [
            RetrievalTool(self.vector_store, self.embedding_service),
            CalculatorTool(),
            SummaryTool(self.llm_service),
            # WebSearchTool()  # Uncomment if web search is needed
        ]
        
        logger.info(
            "Tools initialized",
            tool_names=[tool.name for tool in tools]
        )
        
        return tools
    
    def create_react_agent(
        self,
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        enable_reflection: bool = True,
        reflector: Optional[Any] = None
    ) -> ReActAgent:
        """
        Create a ReAct agent.
        
        Args:
            tools: Custom tools (uses default if None)
            temperature: LLM temperature
            enable_reflection: Whether to enable answer reflection
            reflector: Custom reflector (creates default if None)
            
        Returns:
            ReActAgent instance
        """
        tools_to_use = tools or self.tools
        
        agent = ReActAgent(
            tools=tools_to_use,
            llm_service=self.llm_service,
            memory=self.memory,
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            temperature=temperature,
            enable_reflection=enable_reflection,
            reflector=reflector
        )
        
        logger.info(
            "ReAct agent created",
            tools_count=len(tools_to_use),
            temperature=temperature,
            enable_reflection=enable_reflection
        )
        
        return agent
    
    def create_planner(self) -> QueryPlanner:
        """
        Create a query planner.
        
        Returns:
            QueryPlanner instance
        """
        planner = QueryPlanner(
            llm_service=self.llm_service,
            tools=self.tools
        )
        
        logger.info("Query planner created")
        
        return planner
    
    async def query(
        self,
        query: str,
        collection: str,
        agent_type: str = "react",
        enable_reflection: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an agentic query.
        
        Args:
            query: User query
            collection: Collection name
            agent_type: Type of agent to use ("react")
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with query results
        """
        start_time = time.time()
        
        logger.info(
            "Executing agentic query",
            query=query[:100],
            collection=collection,
            agent_type=agent_type
        )
        
        try:
            # Create agent
            if agent_type == "react":
                agent = self.create_react_agent(enable_reflection=enable_reflection)
            else:
                raise AgentError(
                    f"Unknown agent type: {agent_type}",
                    details={"agent_type": agent_type}
                )
            
            # Execute query
            response = await agent.run(
                query=query,
                collection=collection,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            # Format response
            result = {
                "success": True,
                "query": query,
                "answer": response.answer,
                "actions": [action.to_dict() for action in response.actions],
                "intermediate_steps": response.intermediate_steps,
                "confidence": response.confidence,
                "metadata": {
                    "agent_type": agent_type,
                    "iterations": response.metadata.get("iterations", 0),
                    "tools_used": response.metadata.get("tools_used", []),
                    "execution_time": execution_time
                }
            }
            
            logger.info(
                "Agentic query completed successfully",
                answer_length=len(response.answer),
                actions_count=len(response.actions),
                execution_time=f"{execution_time:.4f}s"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Agentic query failed",
                query=query[:100],
                error=str(e),
                error_type=type(e).__name__,
                execution_time=f"{execution_time:.4f}s"
            )
            
            return {
                "success": False,
                "query": query,
                "answer": None,
                "error": str(e),
                "metadata": {
                    "execution_time": execution_time
                }
            }
    
    async def plan_query(
        self,
        query: str,
        collection: str = None
    ) -> Dict[str, Any]:
        """
        Plan a query without executing it.
        
        Args:
            query: User query
            collection: Collection name
            
        Returns:
            Dictionary with execution plan
        """
        logger.info(
            "Planning query",
            query=query[:100],
            collection=collection
        )
        
        try:
            planner = self.create_planner()
            plan = await planner.plan(
                query=query,
                context={"collection": collection}
            )
            
            result = {
                "success": True,
                "query": query,
                "plan": plan.to_dict()
            }
            
            logger.info(
                "Query planned successfully",
                query_type=plan.query_type.value,
                sub_queries=len(plan.sub_queries)
            )
            
            return result
            
        except Exception as e:
            logger.error("Query planning failed", error=str(e))
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
    
    def add_tool(self, tool: Tool) -> None:
        """
        Add a custom tool to the service.
        
        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        logger.info("Tool added to service", tool_name=tool.name)
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the service.
        
        Args:
            tool_name: Name of tool to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, tool in enumerate(self.tools):
            if tool.name == tool_name:
                self.tools.pop(i)
                logger.info("Tool removed from service", tool_name=tool_name)
                return True
        return False
    
    def get_memory(self) -> Optional[ConversationMemory]:
        """Get conversation memory."""
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear conversation memory."""
        if self.memory:
            self.memory.clear()
            logger.info("Agent memory cleared")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools.
        
        Returns:
            List of tool descriptions
        """
        return [tool.to_dict() for tool in self.tools]

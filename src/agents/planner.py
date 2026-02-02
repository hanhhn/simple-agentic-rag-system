"""
Query planning and decomposition for complex queries.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from src.core.logging import get_logger
from src.core.exceptions import AgentError


logger = get_logger(__name__)


class QueryType(Enum):
    """Types of queries that agents can handle."""
    SIMPLE = "simple"  # Direct question
    RECURSIVE = "recursive"  # Requires multiple steps
    MULTI_PART = "multi_part"  # Has multiple sub-questions
    COMPARISON = "comparison"  # Compares multiple things
    AGGREGATION = "aggregation"  # Combines information
    REASONING = "reasoning"  # Requires logical reasoning
    CALCULATION = "calculation"  # Requires calculations
    UNKNOWN = "unknown"


@dataclass
class SubQuery:
    """A sub-query from query decomposition."""
    id: int
    text: str
    dependencies: List[int]  # IDs of queries this depends on
    tool_hint: Optional[str] = None  # Suggested tool
    priority: int = 0  # Higher = execute first
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "dependencies": self.dependencies,
            "tool_hint": self.tool_hint,
            "priority": self.priority
        }


@dataclass
class QueryPlan:
    """A plan for executing a complex query."""
    original_query: str
    query_type: QueryType
    sub_queries: List[SubQuery]
    execution_order: List[int]  # Order to execute sub-queries
    description: str = ""
    estimated_steps: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_query": self.original_query,
            "query_type": self.query_type.value,
            "sub_queries": [sq.to_dict() for sq in self.sub_queries],
            "execution_order": self.execution_order,
            "description": self.description,
            "estimated_steps": self.estimated_steps
        }


class Planner(ABC):
    """
    Base class for query planners.
    
    Planners analyze queries and create execution plans for complex tasks.
    """
    
    @abstractmethod
    async def plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Create an execution plan for a query.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            QueryPlan with execution strategy
        """
        pass
    
    @abstractmethod
    def classify_query(self, query: str) -> QueryType:
        """
        Classify the type of query.
        
        Args:
            query: User query
            
        Returns:
            QueryType classification
        """
        pass


class QueryPlanner(Planner):
    """
    LLM-powered query planner.
    
    Uses LLM to analyze queries and create detailed execution plans.
    """
    
    def __init__(self, llm_service: Any, tools: List[Any] = None):
        """
        Initialize query planner.
        
        Args:
            llm_service: LLM service for analysis
            tools: Available tools (for context)
        """
        self.llm_service = llm_service
        self.tools = tools or []
        
        logger.info(
            "Query planner initialized",
            tools_count=len(tools) if tools else 0
        )
    
    async def plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """
        Create an execution plan for a query.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            QueryPlan with execution strategy
        """
        start_time = time.time()
        
        logger.info(
            "Planning query",
            query=query[:100],
            context_keys=list(context.keys()) if context else []
        )
        
        # Classify query
        query_type = self.classify_query(query)
        
        # If simple, create single-step plan
        if query_type == QueryType.SIMPLE:
            plan = QueryPlan(
                original_query=query,
                query_type=query_type,
                sub_queries=[SubQuery(
                    id=0,
                    text=query,
                    dependencies=[],
                    tool_hint=None,
                    priority=0
                )],
                execution_order=[0],
                description="Direct query - no planning needed",
                estimated_steps=1
            )
            
            logger.info("Simple query - single step plan")
            return plan
        
        # For complex queries, use LLM to decompose
        plan = await self._decompose_query(query, query_type, context)
        
        plan.estimated_steps = len(plan.sub_queries)
        
        execution_time = time.time() - start_time
        
        logger.info(
            "Query plan created",
            query_type=query_type.value,
            sub_queries=len(plan.sub_queries),
            estimated_steps=plan.estimated_steps,
            planning_time=f"{execution_time:.4f}s"
        )
        
        return plan
    
    def classify_query(self, query: str) -> QueryType:
        """
        Classify the type of query.
        
        Args:
            query: User query
            
        Returns:
            QueryType classification
        """
        query_lower = query.lower()
        
        # Check for calculation indicators
        if any(word in query_lower for word in [
            "calculate", "sum", "add", "multiply", "divide", "subtract",
            "total", "average", "count", "how many", "how much"
        ]):
            return QueryType.CALCULATION
        
        # Check for comparison indicators
        if any(word in query_lower for word in [
            "compare", "difference", "better", "worse", "vs", "versus",
            "between", "among", "contrast"
        ]):
            return QueryType.COMPARISON
        
        # Check for multi-part indicators
        if any(word in query_lower for word in [
            "and also", "also", "additionally", "besides", "furthermore",
            "what about", "how about"
        ]):
            return QueryType.MULTI_PART
        
        # Check for recursive indicators
        if any(word in query_lower for word in [
            "find all", "list all", "every", "each", "then", "after that",
            "next", "subsequently"
        ]):
            return QueryType.RECURSIVE
        
        # Check for reasoning indicators
        if any(word in query_lower for word in [
            "why", "explain", "reason", "because", "cause", "effect",
            "relationship", "how does", "how do"
        ]):
            return QueryType.REASONING
        
        # Default to simple
        return QueryType.SIMPLE
    
    async def _decompose_query(
        self,
        query: str,
        query_type: QueryType,
        context: Optional[Dict[str, Any]]
    ) -> QueryPlan:
        """
        Decompose complex query into sub-queries.
        
        Args:
            query: Original query
            query_type: Type of query
            context: Additional context
            
        Returns:
            QueryPlan with sub-queries
        """
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        
        prompt = f"""You are a query planner. Your job is to break down complex queries into simpler sub-queries.

Original Query: {query}

Query Type: {query_type.value}

Available Tools:
{tools_desc}

Instructions:
1. Identify what information is needed to answer the query
2. Break the query into 2-5 sub-queries
3. Each sub-query should be answerable in one step
4. Indicate dependencies (e.g., sub-query 2 might depend on results from sub-query 1)
5. Suggest which tool would be best for each sub-query

Output format (JSON):
{{
    "description": "Brief description of the approach",
    "sub_queries": [
        {{
            "id": 1,
            "text": "Sub-query text",
            "dependencies": [],
            "tool_hint": "tool_name",
            "priority": 1
        }}
    ]
}}

Respond with only the JSON, no other text."""

        try:
            response = self.llm_service.generate(prompt, temperature=0.3)
            
            # Parse JSON response
            import json
            plan_data = json.loads(self._extract_json(response))
            
            # Create sub-queries
            sub_queries = []
            for sq_data in plan_data.get("sub_queries", []):
                sub_queries.append(SubQuery(
                    id=sq_data["id"],
                    text=sq_data["text"],
                    dependencies=sq_data.get("dependencies", []),
                    tool_hint=sq_data.get("tool_hint"),
                    priority=sq_data.get("priority", 0)
                ))
            
            # Determine execution order (topological sort based on dependencies)
            execution_order = self._determine_execution_order(sub_queries)
            
            return QueryPlan(
                original_query=query,
                query_type=query_type,
                sub_queries=sub_queries,
                execution_order=execution_order,
                description=plan_data.get("description", ""),
                estimated_steps=len(sub_queries)
            )
            
        except Exception as e:
            logger.error("Failed to decompose query", error=str(e))
            # Fallback to single query
            return QueryPlan(
                original_query=query,
                query_type=query_type,
                sub_queries=[SubQuery(
                    id=0,
                    text=query,
                    dependencies=[],
                    tool_hint=None,
                    priority=0
                )],
                execution_order=[0],
                description="Planning failed, treating as simple query",
                estimated_steps=1
            )
    
    def _determine_execution_order(self, sub_queries: List[SubQuery]) -> List[int]:
        """
        Determine execution order using topological sort.
        
        Args:
            sub_queries: List of sub-queries with dependencies
            
        Returns:
            Ordered list of sub-query IDs
        """
        # Build dependency graph
        graph = {sq.id: sq.dependencies for sq in sub_queries}
        
        # Topological sort (Kahn's algorithm)
        in_degree = {sq.id: 0 for sq in sub_queries}
        for sq_id, deps in graph.items():
            for dep_id in deps:
                in_degree[sq_id] += 1
        
        # Queue for nodes with no dependencies
        from collections import deque
        queue = deque([sq_id for sq_id, degree in in_degree.items() if degree == 0])
        order = []
        
        while queue:
            current = queue.popleft()
            order.append(current)
            
            # Update in-degrees
            for sq_id, deps in graph.items():
                if current in deps:
                    in_degree[sq_id] -= 1
                    if in_degree[sq_id] == 0:
                        queue.append(sq_id)
        
        # If not all nodes processed, there's a cycle - just return all IDs
        if len(order) != len(sub_queries):
            return [sq.id for sq in sub_queries]
        
        return order
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response."""
        import re
        
        # Find JSON between braces
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        
        return text


class SimplePlanner(Planner):
    """
    Simple rule-based planner.
    
    Uses keyword matching to classify and plan queries without LLM.
    """
    
    def classify_query(self, query: str) -> QueryType:
        """Classify query using keyword matching."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["calculate", "sum", "multiply"]):
            return QueryType.CALCULATION
        elif any(word in query_lower for word in ["compare", "difference", "vs"]):
            return QueryType.COMPARISON
        elif any(word in query_lower for word in ["and also", "besides", "additionally"]):
            return QueryType.MULTI_PART
        elif any(word in query_lower for word in ["why", "explain", "reason"]):
            return QueryType.REASONING
        else:
            return QueryType.SIMPLE
    
    async def plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryPlan:
        """Create simple plan."""
        query_type = self.classify_query(query)
        
        return QueryPlan(
            original_query=query,
            query_type=query_type,
            sub_queries=[SubQuery(
                id=0,
                text=query,
                dependencies=[],
                tool_hint=None,
                priority=0
            )],
            execution_order=[0],
            description="Simple plan",
            estimated_steps=1
        )

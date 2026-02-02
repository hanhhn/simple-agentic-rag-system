"""
Base agent class for agentic RAG system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time

from src.core.logging import get_logger
from src.core.exceptions import AgentError
from src.agents.tool import Tool, ToolResult, ToolCategory
from src.agents.memory import Memory


logger = get_logger(__name__)


@dataclass
class AgentAction:
    """Represents an action taken by an agent."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[ToolResult] = None
    thought: Optional[str] = None
    step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool_name,
            "input": self.tool_input,
            "output": self.tool_output.to_dict() if self.tool_output else None,
            "thought": self.thought,
            "step": self.step
        }


@dataclass
class AgentResponse:
    """Response from an agent execution."""
    answer: str
    actions: List[AgentAction] = field(default_factory=list)
    intermediate_steps: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "actions": [action.to_dict() for action in self.actions],
            "intermediate_steps": self.intermediate_steps,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "execution_time": self.execution_time
        }


class BaseAgent(ABC):
    """
    Base class for intelligent agents.
    
    Agents use tools to perform actions and reason about problems.
    This class provides the foundation for various agent patterns.
    
    Example:
        >>> agent = BaseAgent([retrieval_tool, calculator_tool])
        >>> response = agent.run("What is 2 + 2?", "my_collection")
    """
    
    def __init__(
        self,
        tools: List[Tool],
        llm_service: Any = None,
        memory: Optional[Memory] = None,
        max_iterations: int = 10,
        verbose: bool = False
    ):
        """
        Initialize base agent.
        
        Args:
            tools: List of available tools
            llm_service: LLM service for reasoning
            memory: Memory for conversation history
            max_iterations: Maximum reasoning iterations
            verbose: Whether to log detailed reasoning steps
        """
        self.tools = {tool.name: tool for tool in tools}
        self.llm_service = llm_service
        self.memory = memory or Memory()
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Group tools by category
        self.tools_by_category = {}
        for tool in tools:
            if tool.category not in self.tools_by_category:
                self.tools_by_category[tool.category] = []
            self.tools_by_category[tool.category].append(tool)
        
        logger.info(
            "Agent initialized",
            tools_count=len(tools),
            categories=[cat.value for cat in self.tools_by_category.keys()],
            max_iterations=max_iterations
        )
    
    @abstractmethod
    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AgentResponse:
        """
        Run the agent on a query.
        
        Args:
            query: User query or task
            context: Additional context for execution
            **kwargs: Additional parameters
            
        Returns:
            AgentResponse with answer and execution details
        """
        pass
    
    async def use_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to use
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with execution outcome
        """
        if tool_name not in self.tools:
            logger.error("Tool not found", tool_name=tool_name, available=list(self.tools.keys()))
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not found"
            )
        
        tool = self.tools[tool_name]
        
        logger.info(
            "Using tool",
            tool_name=tool_name,
            parameters=list(kwargs.keys())
        )
        
        try:
            result = await tool.execute(**kwargs)
            
            if self.verbose:
                logger.info(
                    "Tool executed",
                    tool_name=tool_name,
                    success=result.success,
                    execution_time=f"{result.execution_time:.4f}s"
                )
            
            return result
            
        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def get_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        Get available tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of available tools
        """
        if category:
            return self.tools_by_category.get(category, [])
        return list(self.tools.values())
    
    def get_tool_descriptions(self) -> str:
        """
        Get formatted descriptions of all tools for LLM prompts.
        
        Returns:
            Formatted string with tool descriptions
        """
        descriptions = []
        for tool in self.tools.values():
            desc = f"- {tool.name}: {tool.description}"
            if tool.parameters:
                params = ", ".join(
                    f"{name} ({schema.get('type', 'any')})"
                    for name, schema in tool.parameters.items()
                )
                desc += f"\n  Parameters: {params}"
            descriptions.append(desc)
        
        return "\n\n".join(descriptions)
    
    def add_tool(self, tool: Tool) -> None:
        """
        Add a tool to the agent.
        
        Args:
            tool: Tool to add
        """
        self.tools[tool.name] = tool
        
        if tool.category not in self.tools_by_category:
            self.tools_by_category[tool.category] = []
        self.tools_by_category[tool.category].append(tool)
        
        logger.info("Tool added to agent", tool_name=tool.name)
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the agent.
        
        Args:
            tool_name: Name of tool to remove
            
        Returns:
            True if removed, False if not found
        """
        if tool_name not in self.tools:
            return False
        
        tool = self.tools[tool_name]
        del self.tools[tool_name]
        self.tools_by_category[tool.category].remove(tool)
        
        logger.info("Tool removed from agent", tool_name=tool_name)
        return True
    
    async def think(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a thought/reasoning step.
        
        Args:
            query: Current query or task
            context: Context from previous steps
            
        Returns:
            Thought text
        """
        # This is a placeholder - subclasses should implement specific reasoning
        return f"Thinking about: {query}"
    
    def update_memory(
        self,
        query: str,
        response: AgentResponse
    ) -> None:
        """
        Update agent memory with interaction.
        
        Args:
            query: User query
            response: Agent response
        """
        self.memory.add(query, response)
        
        if self.verbose:
            logger.info(
                "Memory updated",
                query_length=len(query),
                response_length=len(response.answer),
                actions_count=len(response.actions)
            )
    
    def get_memory(self) -> Memory:
        """Get agent memory."""
        return self.memory
    
    def clear_memory(self) -> None:
        """Clear agent memory."""
        self.memory.clear()
        logger.info("Agent memory cleared")

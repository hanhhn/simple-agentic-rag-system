"""
ReAct (Reasoning + Acting) Agent implementation.
"""
from typing import Any, Dict, List, Optional
import time
import json

from src.core.logging import get_logger, LogTag
from src.core.exceptions import AgentError
from src.agents.base_agent import BaseAgent, AgentAction, AgentResponse
from src.agents.tool import Tool, ToolResult
from src.agents.reflector import Reflector, ReflectionResult
from src.llm.prompt_builder import PromptBuilder


logger = get_logger(__name__)


class ReActAgent(BaseAgent):
    """
    ReAct (Reasoning + Acting) Agent.
    
    This agent follows the ReAct pattern:
    1. Thought: Reason about what to do
    2. Action: Select and execute a tool
    3. Observation: Observe the tool result
    4. Repeat until answer is found
    
    This enables multi-step reasoning and tool usage for complex queries.
    
    Example:
        >>> agent = ReActAgent([retrieval_tool, calculator_tool], llm_service)
        >>> response = agent.run("What is the sum of values in document X?", "my_collection")
    """
    
    def __init__(
        self,
        tools: List[Tool],
        llm_service: Any,
        memory: Optional[Any] = None,
        max_iterations: int = 10,
        verbose: bool = False,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        enable_reflection: bool = True,
        reflector: Optional[Reflector] = None
    ):
        """
        Initialize ReAct agent.
        
        Args:
            tools: List of available tools
            llm_service: LLM service for reasoning
            memory: Memory for conversation history
            max_iterations: Maximum reasoning iterations
            verbose: Whether to log detailed reasoning steps
            temperature: LLM temperature
            stop_sequences: Stop sequences for LLM generation
            enable_reflection: Whether to enable answer reflection
            reflector: Custom reflector (creates default if None)
        """
        super().__init__(tools, llm_service, memory, max_iterations, verbose)
        
        self.temperature = temperature
        self.stop_sequences = stop_sequences or ["\nObservation:", "\n\nObservation:"]
        self.prompt_builder = PromptBuilder()
        self.enable_reflection = enable_reflection
        
        # Initialize reflector if not provided
        if reflector is None and enable_reflection:
            from src.agents.reflector import Reflector
            self.reflector = Reflector(llm_service=llm_service)
        else:
            self.reflector = reflector
        
        logger.bind(tag=LogTag.REACT.value).info(
            "ReAct agent initialized",
            tools_count=len(tools),
            max_iterations=max_iterations,
            temperature=temperature,
            enable_reflection=enable_reflection
        )
    
    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        collection: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        """
        Run the ReAct agent on a query.
        
        Args:
            query: User query or task
            context: Additional context (e.g., collection name)
            collection: Collection name for retrieval tools
            **kwargs: Additional parameters
            
        Returns:
            AgentResponse with answer and execution trace
        """
        start_time = time.time()
        
        logger.bind(tag=LogTag.REACT.value).info(
            "ReAct agent started",
            query=query[:100],
            query_length=len(query),
            collection=collection,
            max_iterations=self.max_iterations,
            temperature=self.temperature,
            enable_reflection=self.enable_reflection
        )
        
        # Prepare context
        execution_context = {
            "query": query,
            "collection": collection,
            "context": context or {},
            **kwargs
        }
        
        # Initialize response
        response = AgentResponse(answer="")
        
        # Build initial prompt
        prompt = self._build_react_prompt(query, execution_context)
        
        # ReAct loop: Thought -> Action -> Observation
        iteration = 0
        previous_actions = []
        
        while iteration < self.max_iterations:
            iteration += 1
            
            logger.bind(tag=LogTag.REACT.value).info(
                "ReAct iteration started",
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_actions_count=len(previous_actions)
            )
            
            # Step 1: Generate thought and action
            llm_start = time.time()
            llm_response = self.llm_service.generate(
                prompt,
                temperature=self.temperature
            )
            llm_time = time.time() - llm_start
            
            logger.bind(tag=LogTag.LLM.value).info(
                "LLM reasoning step",
                iteration=iteration,
                llm_response_length=len(llm_response),
                llm_time=f"{llm_time:.4f}s"
            )
            
            # Parse thought and action
            parse_start = time.time()
            thought, action = self._parse_react_response(llm_response)
            parse_time = time.time() - parse_start
            
            logger.bind(tag=LogTag.REACT.value).info(
                "ReAct step parsed",
                iteration=iteration,
                thought=thought[:200] if thought else "None",
                thought_length=len(thought) if thought else 0,
                action_tool=action.get('tool') if action else "None",
                action_args=action.get('args') if action else None,
                parse_time=f"{parse_time:.4f}s"
            )
            
            response.intermediate_steps.append(
                f"Thought {iteration}: {thought}"
            )
            
            # Check if agent wants to answer directly
            if action is None or action.get("tool") == "Answer":
                # Agent has final answer
                final_answer = action.get("args", {}).get("answer", llm_response)
                
                # Apply reflection if enabled
                if self.enable_reflection and self.reflector:
                    logger.bind(tag=LogTag.REFLECTION.value).info(
                        "Starting reflection on final answer",
                        answer_length=len(final_answer),
                        answer_preview=final_answer[:200]
                    )
                    
                    # Collect retrieved documents for reflection context
                    retrieved_docs = []
                    for agent_action in response.actions:
                        if agent_action.tool_output and agent_action.tool_output.success:
                            if hasattr(agent_action.tool_output, 'data'):
                                docs = agent_action.tool_output.data.get('documents', [])
                                retrieved_docs.extend(docs)
                    
                    logger.bind(tag=LogTag.REFLECTION.value).info(
                        "Reflection context prepared",
                        retrieved_docs_count=len(retrieved_docs),
                        actions_count=len(response.actions)
                    )
                    
                    # Reflect on answer
                    reflection_result = await self.reflector.reflect(
                        query=query,
                        answer=final_answer,
                        context=execution_context,
                        retrieved_docs=retrieved_docs
                    )
                    
                    # Store reflection in response metadata
                    response.metadata["reflection"] = reflection_result.to_dict()
                    
                    # If reflection suggests refinement and it's enabled
                    if reflection_result.should_refine:
                        logger.bind(tag=LogTag.REFLECTION.value).info(
                            "Answer needs refinement",
                            overall_score=reflection_result.overall_score,
                            issues=reflection_result.issues,
                            suggestions=reflection_result.suggestions
                        )
                        
                        # Use reflector's refinement
                        refined_answer, final_reflection = await self.reflector.reflect_and_refine(
                            query=query,
                            answer=final_answer,
                            context=execution_context,
                            retrieved_docs=retrieved_docs,
                            max_refinements=2
                        )
                        
                        logger.bind(tag=LogTag.REFLECTION.value).info(
                            "Answer refined",
                            original_length=len(final_answer),
                            refined_length=len(refined_answer),
                            final_score=final_reflection.overall_score
                        )
                        
                        response.answer = refined_answer
                        response.metadata["refinement"] = {
                            "original_answer": final_answer,
                            "refined_answer": refined_answer,
                            "final_reflection": final_reflection.to_dict()
                        }
                        response.confidence = final_reflection.overall_score
                    else:
                        # Answer is good enough
                        logger.bind(tag=LogTag.REFLECTION.value).info(
                            "Answer accepted without refinement",
                            overall_score=reflection_result.overall_score,
                            confidence=reflection_result.overall_score
                        )
                        response.answer = final_answer
                        response.confidence = reflection_result.overall_score
                else:
                    # No reflection, just use answer
                    response.answer = final_answer
                    response.confidence = 0.8  # Default confidence
                
                break
            
            # Step 2: Execute action
            tool_name = action.get("tool")
            tool_args = action.get("args", {})
            
            # Add collection to args if not provided
            if collection and "collection" not in tool_args and tool_name == "retrieve_documents":
                tool_args["collection"] = collection
            
            logger.bind(tag=LogTag.TOOL.value).info(
                "Executing tool",
                iteration=iteration,
                tool_name=tool_name,
                tool_args=tool_args
            )
            
            tool_start = time.time()
            tool_result = await self.use_tool(tool_name, **tool_args)
            tool_time = time.time() - tool_start
            
            # Record action
            agent_action = AgentAction(
                tool_name=tool_name,
                tool_input=tool_args,
                tool_output=tool_result,
                thought=thought,
                step=iteration
            )
            response.actions.append(agent_action)
            previous_actions.append(agent_action)
            
            # Step 3: Observe result
            observation = tool_result.to_string()
            
            # Log detailed tool results, especially for retrieval
            if tool_name == "retrieve_documents" and tool_result.success:
                docs = tool_result.data.get("documents", []) if hasattr(tool_result, 'data') else []
                logger.bind(tag=LogTag.TOOL.value).info(
                    "Tool execution completed (retrieval)",
                    iteration=iteration,
                    tool=tool_name,
                    success=tool_result.success,
                    documents_retrieved=len(docs),
                    tool_execution_time=f"{tool_time:.4f}s",
                    scores=[f"{doc.get('score', 0):.4f}" for doc in docs[:3]]
                )
            else:
                logger.bind(tag=LogTag.TOOL.value).info(
                    "Tool execution completed",
                    iteration=iteration,
                    tool=tool_name,
                    success=tool_result.success,
                    tool_execution_time=f"{tool_time:.4f}s",
                    error=tool_result.error if not tool_result.success else None
                )
            
            # Update prompt with observation
            prompt = self._update_react_prompt(
                prompt,
                thought,
                action,
                observation,
                iteration
            )
            
            response.intermediate_steps.append(
                f"Observation {iteration}: {observation[:200]}"
            )
            
            # Check if we should stop (e.g., tool failed or got good results)
            if not tool_result.success:
                # Tool failed, might need to adjust approach
                logger.bind(tag=LogTag.TOOL.value).warning(
                    "Tool execution failed",
                    tool=tool_name,
                    error=tool_result.error
                )
        
        # Calculate execution time
        response.execution_time = time.time() - start_time
        response.metadata = {
            "iterations": iteration,
            "tools_used": [action.tool_name for action in response.actions],
            "collection": collection,
            "query_length": len(query)
        }
        
        # Update memory
        self.update_memory(query, response)
        
        # Count tools used
        tools_used = {}
        for action in response.actions:
            tool_name = action.tool_name
            tools_used[tool_name] = tools_used.get(tool_name, 0) + 1
        
        # Count retrieved documents
        total_docs_retrieved = 0
        for action in response.actions:
            if action.tool_name == "retrieve_documents" and action.tool_output and action.tool_output.success:
                if hasattr(action.tool_output, 'data'):
                    docs = action.tool_output.data.get('documents', [])
                    total_docs_retrieved += len(docs)
        
        logger.bind(tag=LogTag.REACT.value).info(
            "ReAct agent completed",
            iterations=iteration,
            actions_count=len(response.actions),
            tools_used=tools_used,
            total_documents_retrieved=total_docs_retrieved,
            execution_time=f"{response.execution_time:.4f}s",
            answer_length=len(response.answer),
            confidence=response.confidence,
            has_reflection="reflection" in response.metadata,
            has_refinement="refinement" in response.metadata
        )
        
        return response
    
    def _build_react_prompt(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Build initial ReAct prompt."""
        tools_description = self.get_tool_descriptions()
        
        prompt = f"""You are an intelligent assistant that can use tools to answer questions. Follow this pattern:

Thought: [Reason about what to do]
Action: [tool_name](parameters)
Observation: [Result of the tool]

Available tools:
{tools_description}

Instructions:
1. Think step by step about what information you need
2. Choose the most appropriate tool for each step
3. Use tools with correct parameters
4. If you have enough information to answer, use: Action: Answer(answer="your answer")
5. Be concise and specific in your reasoning
6. If a tool fails, try a different approach

Question: {query}

Let's think step by step.

Thought:"""
        
        return prompt
    
    def _parse_react_response(
        self,
        response: str
    ) -> tuple[Optional[str], Optional[Dict]]:
        """
        Parse LLM response to extract thought and action.
        
        Args:
            response: LLM response text
            
        Returns:
            Tuple of (thought, action_dict)
        """
        import re
        
        # Extract thought (everything before "Action:")
        thought_match = re.search(r"Thought:?(.*?)Action:?", response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        else:
            thought = response.strip()
        
        # Extract action
        action_pattern = r"Action:\s*(\w+)(?:\((.*?)\))?"
        action_match = re.search(action_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if action_match:
            tool_name = action_match.group(1)
            args_str = action_match.group(2) or ""
            
            # Parse arguments
            args = {}
            if args_str:
                # Try to parse as dictionary
                try:
                    import json
                    args = json.loads(args_str)
                except:
                    # Parse as key=value pairs
                    arg_pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
                    for match in re.finditer(arg_pattern, args_str):
                        args[match.group(1)] = match.group(2)
            
            action = {
                "tool": tool_name,
                "args": args
            }
        else:
            action = None
        
        return thought, action
    
    def _update_react_prompt(
        self,
        prompt: str,
        thought: str,
        action: Dict,
        observation: str,
        iteration: int
    ) -> str:
        """Update ReAct prompt with new step."""
        # Append thought, action, and observation
        prompt += f" {thought}\n\n"
        
        if action:
            tool_name = action.get("tool")
            args = action.get("args", {})
            args_str = ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())
            prompt += f"Action: {tool_name}({args_str})\n\n"
        
        prompt += f"Observation: {observation}\n\nThought:"
        
        return prompt
    
    async def stream_run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Run agent with streaming output.
        
        Yields intermediate thoughts and actions in real-time.
        
        Args:
            query: User query
            context: Execution context
            **kwargs: Additional parameters
            
        Yields:
            Tuples of (step_type, content) where step_type is 'thought', 'action', or 'observation'
        """
        # This is a simplified version - in production, implement proper streaming
        yield ("start", f"Starting ReAct agent for: {query}")

        response = await self.run(query, context, **kwargs)

        for step in response.intermediate_steps:
            yield ("step", step)

        yield ("answer", response.answer)
        yield ("end", f"Completed in {len(response.actions)} steps")

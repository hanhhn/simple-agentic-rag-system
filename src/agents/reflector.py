"""
Reflection mechanism for answer quality evaluation.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time

from src.core.logging import get_logger
from src.core.exceptions import AgentError


logger = get_logger(__name__)


class ReflectionCriterion(Enum):
    """Criteria for evaluating agent answers."""
    RELEVANCE = "relevance"  # How well answer addresses query
    ACCURACY = "accuracy"  # Factual correctness
    COMPLETENESS = "completeness"  # How comprehensive the answer is
    CLARITY = "clarity"  # How clear and understandable
    EVIDENCE = "evidence"  # Whether answer is backed by retrieved information
    LOGIC = "logic"  # Logical consistency


@dataclass
class ReflectionResult:
    """Result of reflection evaluation."""
    overall_score: float  # 0.0 to 1.0
    criterion_scores: Dict[str, float]  # Individual criterion scores
    feedback: str  # Qualitative feedback
    issues: List[str]  # Identified issues
    suggestions: List[str]  # Suggestions for improvement
    should_refine: bool  # Whether answer needs refinement
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_score": self.overall_score,
            "criterion_scores": self.criterion_scores,
            "feedback": self.feedback,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "should_refine": self.should_refine
        }


class Reflector:
    """
    Reflector for evaluating agent answer quality.
    
    Uses LLM to evaluate answers against multiple criteria:
    - Relevance to original query
    - Factual accuracy
    - Completeness
    - Clarity
    - Evidence support
    - Logical consistency
    """
    
    def __init__(
        self,
        llm_service: Any,
        enable_self_correction: bool = True,
        min_acceptable_score: float = 0.7
    ):
        """
        Initialize reflector.
        
        Args:
            llm_service: LLM service for evaluation
            enable_self_correction: Whether to automatically refine answers
            min_acceptable_score: Minimum score to accept answer
        """
        self.llm_service = llm_service
        self.enable_self_correction = enable_self_correction
        self.min_acceptable_score = min_acceptable_score
        
        logger.info(
            "Reflector initialized",
            enable_self_correction=enable_self_correction,
            min_acceptable_score=min_acceptable_score
        )
    
    async def reflect(
        self,
        query: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        retrieved_docs: Optional[List[Dict]] = None,
        criteria: Optional[List[ReflectionCriterion]] = None
    ) -> ReflectionResult:
        """
        Reflect on and evaluate agent answer.
        
        Args:
            query: Original user query
            answer: Agent's answer
            context: Additional context
            retrieved_docs: Documents retrieved during reasoning
            criteria: Specific criteria to evaluate (default: all)
            
        Returns:
            ReflectionResult with evaluation
        """
        start_time = time.time()
        
        logger.info(
            "Starting reflection",
            query=query[:100],
            answer_length=len(answer),
            has_retrieved_docs=len(retrieved_docs) > 0 if retrieved_docs else False
        )
        
        # Build evaluation prompt
        criteria_to_use = criteria or [
            ReflectionCriterion.RELEVANCE,
            ReflectionCriterion.ACCURACY,
            ReflectionCriterion.COMPLETENESS,
            ReflectionCriterion.CLARITY,
            ReflectionCriterion.EVIDENCE,
            ReflectionCriterion.LOGIC
        ]
        
        prompt = self._build_reflection_prompt(
            query=query,
            answer=answer,
            retrieved_docs=retrieved_docs,
            criteria=criteria_to_use
        )
        
        # Get evaluation from LLM
        evaluation = await self._get_evaluation(prompt)
        
        # Parse evaluation
        result = self._parse_evaluation(evaluation)
        
        # Determine if refinement is needed
        result.should_refine = result.overall_score < self.min_acceptable_score
        
        execution_time = time.time() - start_time
        
        logger.info(
            "Reflection completed",
            overall_score=result.overall_score,
            should_refine=result.should_refine,
            execution_time=f"{execution_time:.4f}s"
        )
        
        return result
    
    async def reflect_and_refine(
        self,
        query: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        retrieved_docs: Optional[List[Dict]] = None,
        max_refinements: int = 2
    ) -> tuple[str, ReflectionResult]:
        """
        Reflect on answer and refine if needed.
        
        Args:
            query: Original user query
            answer: Initial agent answer
            context: Additional context
            retrieved_docs: Documents retrieved
            max_refinements: Maximum refinement iterations
            
        Returns:
            Tuple of (final_answer, final_reflection)
        """
        current_answer = answer
        refinement_count = 0
        
        while refinement_count < max_refinements:
            # Reflect on current answer
            reflection = await self.reflect(
                query=query,
                answer=current_answer,
                context=context,
                retrieved_docs=retrieved_docs
            )
            
            # If answer is good enough, return it
            if not reflection.should_refine:
                logger.info(
                    "Answer accepted",
                    refinement_count=refinement_count,
                    score=reflection.overall_score
                )
                return current_answer, reflection
            
            # Refine the answer
            logger.info(
                "Refining answer",
                iteration=refinement_count + 1,
                issues=reflection.issues
            )
            
            current_answer = await self._refine_answer(
                query=query,
                original_answer=answer,
                current_answer=current_answer,
                reflection=reflection,
                retrieved_docs=retrieved_docs
            )
            
            refinement_count += 1
        
        # Return last refinement even if not perfect
        final_reflection = await self.reflect(
            query=query,
            answer=current_answer,
            context=context,
            retrieved_docs=retrieved_docs
        )
        
        logger.warning(
            "Max refinements reached",
            final_score=final_reflection.overall_score,
            refinements=max_refinements
        )
        
        return current_answer, final_reflection
    
    def _build_reflection_prompt(
        self,
        query: str,
        answer: str,
        retrieved_docs: Optional[List[Dict]],
        criteria: List[ReflectionCriterion]
    ) -> str:
        """Build reflection evaluation prompt."""
        criteria_descriptions = "\n".join([
            f"- {crit.value}: {self._get_criterion_description(crit)}"
            for crit in criteria
        ])
        
        docs_context = ""
        if retrieved_docs:
            docs_context = "\n\n".join([
                f"Document {i+1}: {doc.get('text', '')[:300]}"
                for i, doc in enumerate(retrieved_docs[:3])
            ])
        
        prompt = f"""You are an answer quality evaluator. Evaluate the following answer based on the given criteria.

Original Query:
{query}

Agent Answer:
{answer}

{f'Retrieved Documents:
{docs_context}' if retrieved_docs else 'No documents retrieved.'}

Evaluation Criteria:
{criteria_descriptions}

Provide your evaluation in the following JSON format:
{{
    "overall_score": <float between 0.0 and 1.0>,
    "criterion_scores": {{
        "relevance": <float 0.0-1.0>,
        "accuracy": <float 0.0-1.0>,
        "completeness": <float 0.0-1.0>,
        "clarity": <float 0.0-1.0>,
        "evidence": <float 0.0-1.0>,
        "logic": <float 0.0-1.0>
    }},
    "feedback": "<overall qualitative feedback>",
    "issues": ["<issue 1>", "<issue 2>", ...],
    "suggestions": ["<suggestion 1>", "<suggestion 2>", ...]
}}

Be objective and specific in your evaluation. Respond with only the JSON, no additional text."""
        
        return prompt
    
    def _get_criterion_description(self, criterion: ReflectionCriterion) -> str:
        """Get description for a criterion."""
        descriptions = {
            ReflectionCriterion.RELEVANCE: "How well the answer addresses the original query",
            ReflectionCriterion.ACCURACY: "Factual correctness based on retrieved information",
            ReflectionCriterion.COMPLETENESS: "How comprehensive the answer is",
            ReflectionCriterion.CLARITY: "How clear and understandable the answer is",
            ReflectionCriterion.EVIDENCE: "Whether the answer is properly supported by evidence",
            ReflectionCriterion.LOGIC: "Logical consistency of the reasoning"
        }
        return descriptions.get(criterion, criterion.value)
    
    async def _get_evaluation(self, prompt: str) -> str:
        """Get evaluation from LLM."""
        try:
            evaluation = self.llm_service.generate(
                prompt,
                temperature=0.3  # Low temperature for objective evaluation
            )
            return evaluation
        except Exception as e:
            logger.error("Failed to get evaluation from LLM", error=str(e))
            raise AgentError(
                f"Reflection evaluation failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def _parse_evaluation(self, evaluation: str) -> ReflectionResult:
        """Parse LLM evaluation into ReflectionResult."""
        import json
        import re
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', evaluation, re.DOTALL)
            if json_match:
                eval_data = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in evaluation")
            
            return ReflectionResult(
                overall_score=eval_data.get("overall_score", 0.5),
                criterion_scores=eval_data.get("criterion_scores", {}),
                feedback=eval_data.get("feedback", ""),
                issues=eval_data.get("issues", []),
                suggestions=eval_data.get("suggestions", []),
                should_refine=False  # Will be calculated later
            )
            
        except Exception as e:
            logger.error("Failed to parse evaluation", error=str(e))
            # Return default moderate evaluation
            return ReflectionResult(
                overall_score=0.5,
                criterion_scores={},
                feedback="Could not evaluate answer automatically",
                issues=[],
                suggestions=[],
                should_refine=False
            )
    
    async def _refine_answer(
        self,
        query: str,
        original_answer: str,
        current_answer: str,
        reflection: ReflectionResult,
        retrieved_docs: Optional[List[Dict]]
    ) -> str:
        """Refine answer based on reflection feedback."""
        
        refinement_prompt = f"""Original Query:
{query}

Original Answer:
{original_answer}

Current Answer:
{current_answer}

Evaluation:
Overall Score: {reflection.overall_score}
Issues: {', '.join(reflection.issues)}
Suggestions: {', '.join(reflection.suggestions)}

Please improve the current answer based on the evaluation. Address the issues and incorporate the suggestions.
Provide the refined answer directly, without explanation."""
        
        try:
            refined = self.llm_service.generate(
                refinement_prompt,
                temperature=0.7
            )
            return refined
        except Exception as e:
            logger.error("Failed to refine answer", error=str(e))
            return current_answer


class SimpleReflector(Reflector):
    """
    Simple rule-based reflector.
    
    Uses basic heuristics instead of LLM evaluation.
    Faster but less sophisticated.
    """
    
    async def reflect(
        self,
        query: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        retrieved_docs: Optional[List[Dict]] = None,
        criteria: Optional[List[ReflectionCriterion]] = None
    ) -> ReflectionResult:
        """
        Simple reflection using heuristics.
        
        Evaluates based on:
        - Answer length vs query length
        - Presence of retrieved documents
        - Answer structure
        """
        logger.info("Using simple reflector")
        
        # Initialize scores
        scores = {
            "relevance": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "clarity": 0.0,
            "evidence": 0.0,
            "logic": 0.0
        }
        
        issues = []
        suggestions = []
        
        # Check relevance based on keywords
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words) / max(len(query_words), 1)
        scores["relevance"] = min(overlap + 0.3, 1.0)
        
        if overlap < 0.3:
            issues.append("Answer doesn't directly address the query")
            suggestions.append("Ensure answer directly responds to the question")
        
        # Check completeness based on length
        if len(answer) < len(query) * 2:
            issues.append("Answer seems too short")
            suggestions.append("Provide more detailed explanation")
            scores["completeness"] = 0.4
        else:
            scores["completeness"] = min(len(answer) / (len(query) * 10), 1.0)
        
        # Check evidence
        if retrieved_docs:
            scores["evidence"] = 0.8
        else:
            scores["evidence"] = 0.5
            issues.append("No documents were retrieved to support answer")
        
        # Check clarity (simple heuristic)
        sentences = answer.split('.')
        if len(sentences) < 2:
            issues.append("Answer is not well-structured")
            scores["clarity"] = 0.5
        else:
            scores["clarity"] = 0.8
        
        # Calculate overall score
        overall = sum(scores.values()) / len(scores)
        
        # Generate feedback
        if overall >= 0.8:
            feedback = "Good quality answer"
        elif overall >= 0.6:
            feedback = "Acceptable answer with minor issues"
        else:
            feedback = "Answer needs significant improvement"
        
        return ReflectionResult(
            overall_score=overall,
            criterion_scores=scores,
            feedback=feedback,
            issues=issues,
            suggestions=suggestions,
            should_refine=overall < self.min_acceptable_score
        )

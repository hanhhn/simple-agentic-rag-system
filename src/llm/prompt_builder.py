"""
Prompt builder for constructing LLM prompts.
"""
from pathlib import Path
from typing import Dict, List, Optional

from src.core.logging import get_logger
from src.core.exceptions import PromptError


logger = get_logger(__name__)


class PromptBuilder:
    """
    Builder for constructing LLM prompts with templates.
    
    This class provides methods to build prompts for various RAG scenarios,
    including question answering, summarization, and more.
    
    Example:
        >>> builder = PromptBuilder()
        >>> prompt = builder.build_rag_prompt(
        ...     question="What is RAG?",
        ...     context=["RAG stands for Retrieval-Augmented Generation"]
        ... )
        >>> print(prompt)
    """
    
    # Default templates
    DEFAULT_RAG_TEMPLATE = """Use the following pieces of context to answer the question at the end.

Context:
{context}

Question: {question}

Answer:"""

    DEFAULT_CHAT_TEMPLATE = """You are a helpful assistant. Respond to the user's question based on the provided context if available.

{context}

User: {question}

Assistant:"""

    def __init__(self, rag_template: Optional[str] = None, chat_template: Optional[str] = None) -> None:
        """
        Initialize prompt builder.
        
        Args:
            rag_template: Custom RAG template (uses default if None)
            chat_template: Custom chat template (uses default if None)
        """
        self.rag_template = rag_template or self.DEFAULT_RAG_TEMPLATE
        self.chat_template = chat_template or self.DEFAULT_CHAT_TEMPLATE
    
    def build_rag_prompt(
        self,
        question: str,
        contexts: List[str],
        max_context_length: int = 4000
    ) -> str:
        """
        Build a RAG prompt with context.
        
        Args:
            question: User's question
            contexts: List of context strings from retrieved documents
            max_context_length: Maximum characters for context
            
        Returns:
            Formatted RAG prompt
            
        Example:
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_rag_prompt(
            ...     question="What is RAG?",
            ...     contexts=["RAG is..."]
            ... )
        """
        # Combine contexts
        context_text = self._format_contexts(contexts, max_context_length)
        
        # Build prompt
        try:
            prompt = self.rag_template.format(
                context=context_text,
                question=question
            )
            
            logger.info(
                "Built RAG prompt",
                question=question[:100],
                context_length=len(context_text)
            )
            
            return prompt
            
        except KeyError as e:
            raise PromptError(
                f"Missing placeholder in template: {e}",
                details={"missing_key": str(e), "template": self.rag_template[:100]}
            )
    
    def build_chat_prompt(
        self,
        question: str,
        contexts: Optional[List[str]] = None,
        chat_history: Optional[List[Dict]] = None,
        max_context_length: int = 4000
    ) -> str:
        """
        Build a chat prompt with optional context and history.
        
        Args:
            question: Current user question
            contexts: Optional context strings from retrieved documents
            chat_history: Optional chat history (list of {role, content} dicts)
            max_context_length: Maximum characters for context
            
        Returns:
            Formatted chat prompt
        """
        # Build context section
        context_section = ""
        if contexts:
            context_text = self._format_contexts(contexts, max_context_length)
            context_section = f"Context:\n{context_text}\n\n"
        
        # Build history section
        history_section = ""
        if chat_history:
            history_lines = []
            for msg in chat_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_lines.append(f"{role.capitalize()}: {content}")
            history_section = "\n".join(history_lines) + "\n\n"
        
        # Build prompt
        try:
            prompt = self.chat_template.format(
                context=context_section,
                question=question,
                history=history_section
            )
            
            logger.info(
                "Built chat prompt",
                question=question[:100],
                has_context=bool(contexts),
                history_length=len(chat_history) if chat_history else 0
            )
            
            return prompt
            
        except KeyError as e:
            raise PromptError(
                f"Missing placeholder in template: {e}",
                details={"missing_key": str(e), "template": self.chat_template[:100]}
            )
    
    def build_summarization_prompt(self, text: str, max_length: int = 200) -> str:
        """
        Build a summarization prompt.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words
            
        Returns:
            Summarization prompt
        """
        prompt = f"""Summarize the following text in approximately {max_length} words.

Text:
{text}

Summary:"""
        
        logger.info(
            "Built summarization prompt",
            text_length=len(text),
            target_length=max_length
        )
        
        return prompt
    
    def build_qa_prompt(self, question: str) -> str:
        """
        Build a simple question-answering prompt.
        
        Args:
            question: Question to answer
            
        Returns:
            QA prompt
        """
        prompt = f"""Answer the following question clearly and concisely.

Question: {question}

Answer:"""
        
        return prompt
    
    def _format_contexts(self, contexts: List[str], max_length: int) -> str:
        """
        Format contexts into a single text block.
        
        Args:
            contexts: List of context strings
            max_length: Maximum total characters
            
        Returns:
            Formatted context text
        """
        # Add separators between contexts
        formatted_contexts = []
        total_length = 0
        
        for i, context in enumerate(contexts):
            # Check if adding this context would exceed limit
            if total_length + len(context) > max_length:
                break
            
            formatted_contexts.append(f"[Document {i+1}]\n{context.strip()}")
            total_length += len(context) + 20  # +20 for formatting
        
        return "\n\n".join(formatted_contexts)
    
    def load_template(self, filepath: str, template_type: str = "rag") -> None:
        """
        Load a custom template from a file.
        
        Args:
            filepath: Path to template file
            template_type: Type of template ("rag" or "chat")
            
        Example:
            >>> builder = PromptBuilder()
            >>> builder.load_template("custom_rag_template.txt", "rag")
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template = f.read()
            
            if template_type == "rag":
                self.rag_template = template
            elif template_type == "chat":
                self.chat_template = template
            else:
                raise PromptError(
                    f"Unknown template type: {template_type}",
                    details={"template_type": template_type}
                )
            
            logger.info("Loaded custom template", template_type=template_type, filepath=filepath)
            
        except Exception as e:
            raise PromptError(
                f"Failed to load template from {filepath}: {str(e)}",
                details={"filepath": filepath, "error": str(e)}
            )
    
    def get_template(self, template_type: str = "rag") -> str:
        """
        Get the current template.
        
        Args:
            template_type: Type of template ("rag" or "chat")
            
        Returns:
            Template string
        """
        if template_type == "rag":
            return self.rag_template
        elif template_type == "chat":
            return self.chat_template
        else:
            raise PromptError(
                f"Unknown template type: {template_type}",
                details={"template_type": template_type}
            )

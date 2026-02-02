"""
Memory management for agent conversations and context.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from src.core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class Message:
    """Represents a message in conversation history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Conversation:
    """Represents a conversation with multiple messages."""
    id: str
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: Message) -> None:
        """Add a message to conversation."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """Get recent messages."""
        return self.messages[-count:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class Memory(ABC):
    """
    Base class for agent memory.
    
    Memory allows agents to remember past interactions and maintain context.
    """
    
    @abstractmethod
    def add(
        self,
        query: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an interaction to memory."""
        pass
    
    @abstractmethod
    def get(
        self,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Any]:
        """Retrieve interactions from memory."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear memory."""
        pass
    
    @abstractmethod
    def to_string(self) -> str:
        """Convert memory to string for LLM context."""
        pass


class ConversationMemory(Memory):
    """
    Memory that stores full conversation history.
    
    Useful for multi-turn conversations where context is important.
    """
    
    def __init__(self, max_messages: int = 100):
        """
        Initialize conversation memory.
        
        Args:
            max_messages: Maximum number of messages to keep
        """
        self.max_messages = max_messages
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation_id: Optional[str] = None
        self.global_messages: List[Message] = []
        
        logger.info(
            "Conversation memory initialized",
            max_messages=max_messages
        )
    
    def add(
        self,
        query: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add interaction to memory.
        
        Args:
            query: User query
            response: Agent response
            metadata: Optional metadata
        """
        # Create user message
        user_message = Message(
            role="user",
            content=query,
            metadata=metadata or {}
        )
        
        # Create assistant message
        answer = getattr(response, 'answer', str(response))
        assistant_message = Message(
            role="assistant",
            content=answer,
            metadata={
                "actions_count": len(getattr(response, 'actions', [])),
                "execution_time": getattr(response, 'execution_time', 0),
                **(metadata or {})
            }
        )
        
        # Add to global messages
        self.global_messages.append(user_message)
        self.global_messages.append(assistant_message)
        
        # Add to current conversation if exists
        if self.current_conversation_id:
            conversation = self.conversations.get(self.current_conversation_id)
            if conversation:
                conversation.add_message(user_message)
                conversation.add_message(assistant_message)
        
        # Trim if needed
        self._trim_messages()
        
        logger.debug(
            "Memory updated",
            user_query_length=len(query),
            assistant_answer_length=len(answer),
            total_messages=len(self.global_messages)
        )
    
    def get(
        self,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Message]:
        """
        Get messages from memory.
        
        Args:
            query: Optional query for filtering (not used in this implementation)
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages
        """
        return self.global_messages[-limit:]
    
    def clear(self) -> None:
        """Clear all memory."""
        self.global_messages = []
        self.conversations = {}
        self.current_conversation_id = None
        logger.info("Conversation memory cleared")
    
    def to_string(self, max_messages: int = 10) -> str:
        """
        Convert recent conversation history to string.
        
        Args:
            max_messages: Maximum messages to include
            
        Returns:
            Formatted conversation string
        """
        messages = self.global_messages[-max_messages:]
        
        lines = []
        for msg in messages:
            role = msg.role.capitalize()
            content = msg.content[:500]  # Truncate long messages
            lines.append(f"{role}: {content}")
        
        return "\n\n".join(lines)
    
    def start_conversation(self, conversation_id: str) -> None:
        """
        Start a new conversation.
        
        Args:
            conversation_id: Unique conversation ID
        """
        self.current_conversation_id = conversation_id
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation(
                id=conversation_id,
                messages=[],
                metadata={"started_at": datetime.now().isoformat()}
            )
            logger.info("New conversation started", id=conversation_id)
    
    def end_conversation(self) -> None:
        """End current conversation."""
        if self.current_conversation_id:
            logger.info("Conversation ended", id=self.current_conversation_id)
            self.current_conversation_id = None
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a specific conversation."""
        return self.conversations.get(conversation_id)
    
    def list_conversations(self) -> List[Conversation]:
        """List all conversations."""
        return list(self.conversations.values())
    
    def _trim_messages(self) -> None:
        """Trim messages to max_messages."""
        if len(self.global_messages) > self.max_messages:
            self.global_messages = self.global_messages[-self.max_messages:]
            logger.debug("Memory trimmed to max_messages", count=len(self.global_messages))


class VectorMemory(Memory):
    """
    Memory that stores embeddings for semantic retrieval.
    
    Useful for finding relevant past interactions based on semantic similarity.
    """
    
    def __init__(
        self,
        vector_store: Any,
        embedding_service: Any,
        max_memories: int = 1000
    ):
        """
        Initialize vector memory.
        
        Args:
            vector_store: Vector store for embeddings
            embedding_service: Embedding service
            max_memories: Maximum number of memories to store
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.max_memories = max_memories
        self.memories: List[Dict[str, Any]] = []
        
        logger.info(
            "Vector memory initialized",
            max_memories=max_memories
        )
    
    def add(
        self,
        query: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add interaction to vector memory.
        
        Args:
            query: User query
            response: Agent response
            metadata: Optional metadata
        """
        import time
        
        memory_item = {
            "query": query,
            "answer": getattr(response, 'answer', str(response)),
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Generate embedding for query
        embedding = self.embedding_service.generate_embedding(query)
        
        # Store in vector store (if collection exists)
        # Note: In production, you'd want a dedicated collection for memory
        try:
            self.vector_store.insert_vectors(
                collection_name="agent_memory",
                vectors=[embedding],
                payloads=[{
                    "query": query,
                    "answer": memory_item["answer"],
                    "timestamp": memory_item["timestamp"],
                    **memory_item["metadata"]
                }]
            )
        except Exception as e:
            logger.warning("Failed to insert into vector memory", error=str(e))
        
        self.memories.append(memory_item)
        
        # Trim if needed
        if len(self.memories) > self.max_memories:
            self.memories = self.memories[-self.max_memories:]
    
    def get(
        self,
        query: Optional[str] = None,
        limit: int = 5
    ) -> List[Any]:
        """
        Retrieve relevant memories.
        
        Args:
            query: Query to search for (returns all if None)
            limit: Maximum number of results
            
        Returns:
            List of relevant memories
        """
        if query is None:
            return self.memories[-limit:]
        
        # Search vector store for similar queries
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            results = self.vector_store.search(
                collection_name="agent_memory",
                query_vector=query_embedding,
                top_k=limit
            )
            
            memories = []
            for result in results:
                payload = result.get("payload", {})
                memories.append({
                    "query": payload.get("query", ""),
                    "answer": payload.get("answer", ""),
                    "score": result.get("score", 0),
                    "metadata": payload
                })
            
            return memories
            
        except Exception as e:
            logger.warning("Vector search failed, returning recent memories", error=str(e))
            return self.memories[-limit:]
    
    def clear(self) -> None:
        """Clear vector memory."""
        self.memories = []
        try:
            if self.vector_store.collection_exists("agent_memory"):
                self.vector_store.delete_collection("agent_memory")
        except Exception as e:
            logger.warning("Failed to clear vector collection", error=str(e))
        logger.info("Vector memory cleared")
    
    def to_string(self, max_items: int = 5) -> str:
        """
        Convert recent memories to string.
        
        Args:
            max_items: Maximum items to include
            
        Returns:
            Formatted memory string
        """
        memories = self.memories[-max_items:]
        
        lines = []
        for memory in memories:
            lines.append(f"Q: {memory['query'][:200]}")
            lines.append(f"A: {memory['answer'][:200]}")
            lines.append("")
        
        return "\n".join(lines)

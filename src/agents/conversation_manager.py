"""
Advanced conversation manager with session management and persistence.
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import uuid

from src.core.logging import get_logger
from src.agents.memory import Message, Conversation


logger = get_logger(__name__)


class ConversationStatus(Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ConversationPriority(Enum):
    """Priority level for conversations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ConversationMetadata:
    """Extended metadata for conversations."""
    title: str = ""
    tags: List[str] = field(default_factory=list)
    status: str = ConversationStatus.ACTIVE.value
    priority: str = ConversationPriority.MEDIUM.value
    collection: str = ""
    user_id: str = "default"
    session_id: str = ""
    message_count: int = 0
    total_tokens: int = 0
    avg_confidence: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    archived_at: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.archived_at:
            data["archived_at"] = self.archived_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMetadata":
        """Create from dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if "archived_at" in data and isinstance(data["archived_at"], str):
            data["archived_at"] = datetime.fromisoformat(data["archived_at"])
        return cls(**data)


@dataclass
class Session:
    """Represents a user session."""
    id: str
    user_id: str = "default"
    conversation_ids: List[str] = field(default_factory=list)
    current_conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "conversation_ids": self.conversation_ids,
            "current_conversation_id": self.current_conversation_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data and isinstance(data["last_activity"], str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)


@dataclass
class ConversationStats:
    """Statistics for a conversation."""
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    total_tokens: int = 0
    avg_tokens_per_message: float = 0.0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    tool_usage_count: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    reflection_count: int = 0
    refinement_count: int = 0
    error_count: int = 0
    success_rate: float = 1.0
    first_message_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.first_message_time:
            data["first_message_time"] = self.first_message_time.isoformat()
        if self.last_message_time:
            data["last_message_time"] = self.last_message_time.isoformat()
        return data


class ConversationManager:
    """
    Advanced conversation manager with session management and persistence.
    
    Features:
    - Multi-conversation support
    - Session management
    - Conversation metadata and tagging
    - Search and filtering
    - Analytics and statistics
    - Export/import functionality
    - Archiving and deletion
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_conversations: int = 100,
        max_messages_per_conversation: int = 1000,
        auto_archive_days: int = 30
    ):
        """
        Initialize conversation manager.
        
        Args:
            storage_path: Path for persistent storage
            max_conversations: Maximum conversations to keep
            max_messages_per_conversation: Max messages per conversation
            auto_archive_days: Days before auto-archiving inactive conversations
        """
        self.storage_path = storage_path
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation
        self.auto_archive_days = auto_archive_days
        
        self.conversations: Dict[str, Conversation] = {}
        self.conversation_metadata: Dict[str, ConversationMetadata] = {}
        self.sessions: Dict[str, Session] = {}
        self.current_session_id: Optional[str] = None
        
        # Load from storage if available
        if storage_path:
            self._load_from_storage()
        
        logger.info(
            "Conversation manager initialized",
            storage_path=storage_path,
            max_conversations=max_conversations,
            auto_archive_days=auto_archive_days
        )
    
    def create_conversation(
        self,
        title: str = "",
        collection: str = "",
        tags: List[str] = None,
        user_id: str = "default",
        priority: str = ConversationPriority.MEDIUM.value
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            title: Conversation title
            collection: Collection name
            tags: Tags for categorization
            user_id: User ID
            priority: Priority level
            
        Returns:
            Conversation ID
        """
        conv_id = str(uuid.uuid4())
        
        # Generate title from first message if not provided
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Create conversation
        conversation = Conversation(
            id=conv_id,
            messages=[],
            metadata={"user_id": user_id, "collection": collection}
        )
        
        # Create metadata
        metadata = ConversationMetadata(
            title=title,
            tags=tags or [],
            collection=collection,
            user_id=user_id,
            session_id=self.current_session_id or "",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.conversations[conv_id] = conversation
        self.conversation_metadata[conv_id] = metadata
        
        # Add to current session
        if self.current_session_id:
            self._add_conversation_to_session(self.current_session_id, conv_id)
        
        logger.info(
            "Conversation created",
            conversation_id=conv_id,
            title=title,
            user_id=user_id
        )
        
        self._save_to_storage()
        return conv_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(conversation_id)
    
    def get_conversation_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        """Get conversation metadata."""
        return self.conversation_metadata.get(conversation_id)
    
    def add_message(
        self,
        conversation_id: str,
        message: Message,
        update_title: bool = True
    ) -> None:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            message: Message to add
            update_title: Whether to update title based on first message
        """
        conversation = self.conversations.get(conversation_id)
        metadata = self.conversation_metadata.get(conversation_id)
        
        if not conversation or not metadata:
            logger.warning("Conversation not found", conversation_id=conversation_id)
            return
        
        conversation.add_message(message)
        metadata.updated_at = datetime.now()
        metadata.message_count = len(conversation.messages)
        metadata.last_activity = datetime.now()
        
        # Update title from first user message if needed
        if update_title and len(conversation.messages) == 1 and message.role == "user":
            title = message.content[:50] + ("..." if len(message.content) > 50 else "")
            metadata.title = title
        
        # Update session activity
        if metadata.session_id and metadata.session_id in self.sessions:
            self.sessions[metadata.session_id].last_activity = datetime.now()
        
        logger.debug(
            "Message added to conversation",
            conversation_id=conversation_id,
            role=message.role,
            message_count=len(conversation.messages)
        )
        
        self._save_to_storage()
    
    def update_conversation_metadata(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation ID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated, False if not found
        """
        metadata = self.conversation_metadata.get(conversation_id)
        
        if not metadata:
            return False
        
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        metadata.updated_at = datetime.now()
        
        logger.info(
            "Conversation metadata updated",
            conversation_id=conversation_id,
            updates=list(updates.keys())
        )
        
        self._save_to_storage()
        return True
    
    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        metadata = self.conversation_metadata.get(conversation_id)
        
        if not metadata:
            return False
        
        metadata.status = ConversationStatus.ARCHIVED.value
        metadata.archived_at = datetime.now()
        metadata.updated_at = datetime.now()
        
        logger.info("Conversation archived", conversation_id=conversation_id)
        self._save_to_storage()
        return True
    
    def delete_conversation(self, conversation_id: str, permanent: bool = False) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
            permanent: If True, permanently delete; otherwise just mark as deleted
            
        Returns:
            True if deleted
        """
        if permanent:
            self.conversations.pop(conversation_id, None)
            self.conversation_metadata.pop(conversation_id, None)
        else:
            metadata = self.conversation_metadata.get(conversation_id)
            if metadata:
                metadata.status = ConversationStatus.DELETED.value
                metadata.updated_at = datetime.now()
        
        logger.info(
            "Conversation deleted",
            conversation_id=conversation_id,
            permanent=permanent
        )
        
        self._save_to_storage()
        return True
    
    def list_conversations(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        collection: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List conversations with filtering.
        
        Args:
            user_id: Filter by user ID
            status: Filter by status
            tags: Filter by tags (must have all specified tags)
            collection: Filter by collection
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of conversation summaries
        """
        results = []
        
        for conv_id, metadata in self.conversation_metadata.items():
            # Apply filters
            if user_id and metadata.user_id != user_id:
                continue
            if status and metadata.status != status:
                continue
            if tags and not all(tag in metadata.tags for tag in tags):
                continue
            if collection and metadata.collection != collection:
                continue
            
            results.append({
                "id": conv_id,
                "metadata": metadata.to_dict(),
                "message_count": metadata.message_count
            })
        
        # Sort by updated_at (newest first)
        results.sort(key=lambda x: x["metadata"]["updated_at"], reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]
    
    def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by content.
        
        Args:
            query: Search query
            user_id: Filter by user ID
            limit: Maximum results
            
        Returns:
            List of matching conversations with snippets
        """
        query_lower = query.lower()
        results = []
        
        for conv_id, conversation in self.conversations.items():
            metadata = self.conversation_metadata.get(conv_id)
            
            # Filter by user
            if user_id and metadata and metadata.user_id != user_id:
                continue
            
            # Search in messages
            for msg in conversation.messages:
                if query_lower in msg.content.lower():
                    results.append({
                        "id": conv_id,
                        "metadata": metadata.to_dict() if metadata else {},
                        "snippet": msg.content[:200],
                        "match_message": msg.to_dict()
                    })
                    break
        
        return results[:limit]
    
    def get_conversation_stats(self, conversation_id: str) -> Optional[ConversationStats]:
        """
        Calculate statistics for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationStats object
        """
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return None
        
        stats = ConversationStats()
        stats.total_messages = len(conversation.messages)
        
        tool_usage = {}
        total_confidence = 0.0
        confidence_count = 0
        total_exec_time = 0.0
        
        for msg in conversation.messages:
            # Count messages by role
            if msg.role == "user":
                stats.user_messages += 1
            elif msg.role == "assistant":
                stats.assistant_messages += 1
            
            # Token counts
            stats.total_tokens += len(msg.content.split())
            
            # Track first/last message
            if not stats.first_message_time:
                stats.first_message_time = msg.timestamp
            stats.last_message_time = msg.timestamp
            
            # Extract metrics from metadata
            msg_metrics = msg.metadata
            
            # Execution time
            if "execution_time" in msg_metrics:
                total_exec_time += msg_metrics["execution_time"]
                stats.total_execution_time += msg_metrics["execution_time"]
            
            # Confidence scores
            if "confidence" in msg_metrics:
                total_confidence += msg_metrics["confidence"]
                confidence_count += 1
            
            # Tool usage
            if "tools_used" in msg_metrics:
                for tool in msg_metrics["tools_used"]:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            # Reflection and refinement counts
            if "reflection" in msg_metrics:
                stats.reflection_count += 1
            if "refinement" in msg_metrics:
                stats.refinement_count += 1
            
            # Error count (from failed tools)
            if msg_metrics.get("has_error", False):
                stats.error_count += 1
        
        # Calculate averages
        if stats.total_messages > 0:
            stats.avg_tokens_per_message = stats.total_tokens / stats.total_messages
            stats.avg_execution_time = total_exec_time / stats.total_messages
            stats.success_rate = 1.0 - (stats.error_count / stats.total_messages)
        
        if confidence_count > 0:
            stats.avg_confidence = total_confidence / confidence_count
        
        stats.tool_usage_count = tool_usage
        
        # Calculate duration
        if stats.first_message_time and stats.last_message_time:
            stats.duration_seconds = (stats.last_message_time - stats.first_message_time).total_seconds()
        
        return stats
    
    def create_session(self, user_id: str = "default") -> str:
        """
        Create a new session.
        
        Args:
            user_id: User ID
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        session = Session(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            is_active=True
        )
        
        self.sessions[session_id] = session
        self.current_session_id = session_id
        
        logger.info("Session created", session_id=session_id, user_id=user_id)
        
        self._save_to_storage()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def set_current_session(self, session_id: str) -> bool:
        """Set the current session."""
        if session_id not in self.sessions:
            return False
        
        self.current_session_id = session_id
        logger.info("Current session set", session_id=session_id)
        return True
    
    def _add_conversation_to_session(self, session_id: str, conversation_id: str) -> None:
        """Add conversation to session."""
        session = self.sessions.get(session_id)
        if session:
            if conversation_id not in session.conversation_ids:
                session.conversation_ids.append(conversation_id)
            session.current_conversation_id = conversation_id
            session.last_activity = datetime.now()
    
    def export_conversation(
        self,
        conversation_id: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> str:
        """
        Export a conversation.
        
        Args:
            conversation_id: Conversation ID
            format: Export format (json, txt, markdown)
            include_metadata: Whether to include metadata
            
        Returns:
            Exported data as string
        """
        conversation = self.conversations.get(conversation_id)
        metadata = self.conversation_metadata.get(conversation_id)
        
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        if format == "json":
            export_data = {
                "conversation": conversation.to_dict(),
                "metadata": metadata.to_dict() if metadata and include_metadata else None
            }
            return json.dumps(export_data, indent=2)
        
        elif format == "txt":
            lines = [f"Conversation: {metadata.title if metadata else conversation_id}"]
            lines.append(f"ID: {conversation_id}")
            if metadata and include_metadata:
                lines.append(f"Created: {metadata.created_at}")
                lines.append(f"Messages: {len(conversation.messages)}")
            lines.append("\n" + "="*50 + "\n")
            
            for msg in conversation.messages:
                lines.append(f"[{msg.timestamp}] {msg.role.upper()}")
                lines.append(msg.content)
                lines.append("")
            
            return "\n".join(lines)
        
        elif format == "markdown":
            lines = [f"# {metadata.title if metadata else 'Conversation'}"]
            lines.append(f"**ID:** `{conversation_id}`")
            if metadata and include_metadata:
                lines.append(f"**Created:** {metadata.created_at}")
                if metadata.tags:
                    lines.append(f"**Tags:** {', '.join(metadata.tags)}")
            lines.append("\n" + "---\n")
            
            for msg in conversation.messages:
                role_emoji = "👤" if msg.role == "user" else "🤖"
                lines.append(f"### {role_emoji} {msg.role.capitalize()}")
                lines.append(f"*{msg.timestamp}*")
                lines.append("")
                lines.append(msg.content)
                lines.append("")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_conversation(
        self,
        data: str,
        format: str = "json",
        user_id: str = "default"
    ) -> str:
        """
        Import a conversation.
        
        Args:
            data: Conversation data
            format: Data format (json, txt, markdown)
            user_id: User ID to associate with
            
        Returns:
            New conversation ID
        """
        if format == "json":
            import_data = json.loads(data)
            conv_dict = import_data.get("conversation", {})
            metadata_dict = import_data.get("metadata", {})
            
            # Create new conversation
            conv_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conv_id,
                messages=[Message.from_dict(m) for m in conv_dict.get("messages", [])],
                metadata=conv_dict.get("metadata", {})
            )
            
            # Create metadata
            metadata = ConversationMetadata(
                title=metadata_dict.get("title", "Imported Conversation"),
                tags=metadata_dict.get("tags", []),
                collection=metadata_dict.get("collection", ""),
                user_id=user_id,
                message_count=len(conversation.messages),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.conversations[conv_id] = conversation
            self.conversation_metadata[conv_id] = metadata
            
            logger.info("Conversation imported", conversation_id=conv_id)
            
            self._save_to_storage()
            return conv_id
        
        else:
            raise ValueError(f"Import format not supported: {format}")
    
    def cleanup_old_conversations(self, days: Optional[int] = None) -> int:
        """
        Archive or delete old conversations.
        
        Args:
            days: Number of days before archiving (uses auto_archive_days if None)
            
        Returns:
            Number of conversations archived
        """
        cutoff_days = days or self.auto_archive_days
        cutoff_date = datetime.now() - timedelta(days=cutoff_days)
        archived_count = 0
        
        for conv_id, metadata in self.conversation_metadata.items():
            if metadata.status == ConversationStatus.ACTIVE.value:
                if metadata.last_activity < cutoff_date:
                    if self.archive_conversation(conv_id):
                        archived_count += 1
        
        logger.info(
            "Old conversations archived",
            count=archived_count,
            days=cutoff_days
        )
        
        return archived_count
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags across conversations."""
        tags = set()
        for metadata in self.conversation_metadata.values():
            tags.update(metadata.tags)
        return sorted(list(tags))
    
    def _save_to_storage(self) -> None:
        """Save to persistent storage."""
        if not self.storage_path:
            return
        
        try:
            import os
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            data = {
                "conversations": {
                    conv_id: conv.to_dict()
                    for conv_id, conv in self.conversations.items()
                },
                "conversation_metadata": {
                    conv_id: meta.to_dict()
                    for conv_id, meta in self.conversation_metadata.items()
                },
                "sessions": {
                    session_id: session.to_dict()
                    for session_id, session in self.sessions.items()
                },
                "current_session_id": self.current_session_id
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            logger.error("Failed to save to storage", error=str(e))
    
    def _load_from_storage(self) -> None:
        """Load from persistent storage."""
        if not self.storage_path:
            return
        
        try:
            import os
            if not os.path.exists(self.storage_path):
                logger.info("No existing storage file found, starting fresh")
                return
            
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Load conversations
            for conv_id, conv_dict in data.get("conversations", {}).items():
                self.conversations[conv_id] = Conversation(
                    id=conv_id,
                    messages=[Message.from_dict(m) for m in conv_dict.get("messages", [])],
                    metadata=conv_dict.get("metadata", {})
                )
            
            # Load metadata
            for conv_id, meta_dict in data.get("conversation_metadata", {}).items():
                self.conversation_metadata[conv_id] = ConversationMetadata.from_dict(meta_dict)
            
            # Load sessions
            for session_id, session_dict in data.get("sessions", {}).items():
                self.sessions[session_id] = Session.from_dict(session_dict)
            
            self.current_session_id = data.get("current_session_id")
            
            logger.info(
                "Loaded from storage",
                conversations=len(self.conversations),
                sessions=len(self.sessions)
            )
            
        except Exception as e:
            logger.error("Failed to load from storage", error=str(e))

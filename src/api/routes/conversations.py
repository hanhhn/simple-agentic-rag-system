"""
Conversation management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from src.core.logging import get_logger, LogTag
from src.core.exceptions import ValidationError
from src.api.models.common import SuccessResponse, ErrorResponse
from src.api.dependencies import get_llm_service, get_vector_store, get_embedding_service
from src.agents.conversation_manager import (
    ConversationManager,
    ConversationMetadata,
    ConversationStats
)
from src.services.analytics_service import (
    AnalyticsService,
    AnalyticsReport,
    MetricType,
    TimeGranularity
)


logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

# Global instances (in production, use dependency injection)
_conversation_manager: Optional[ConversationManager] = None
_analytics_service: Optional[AnalyticsService] = None


def get_conversation_manager() -> ConversationManager:
    """Get or create conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(
            storage_path="data/conversations.json"
        )
    return _conversation_manager


def get_analytics_service() -> AnalyticsService:
    """Get or create analytics service."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService(
            conversation_manager=get_conversation_manager()
        )
    return _analytics_service


# Conversation Endpoints

@router.post("/", response_model=SuccessResponse, status_code=201)
async def create_conversation(
    title: str = Query(..., description="Conversation title"),
    collection: str = Query("", description="Collection name"),
    tags: Optional[List[str]] = Query(None, description="Tags for categorization"),
    user_id: str = Query("default", description="User ID"),
    priority: str = Query("medium", description="Priority level"),
    manager = Depends(get_conversation_manager)
):
    """
    Create a new conversation.
    
    Args:
        title: Conversation title
        collection: Collection name
        tags: Tags for categorization
        user_id: User ID
        priority: Priority level (low, medium, high, urgent)
        
    Returns:
        Success response with conversation ID
    """
    try:
        conv_id = manager.create_conversation(
            title=title,
            collection=collection,
            tags=tags or [],
            user_id=user_id,
            priority=priority
        )
        
        return SuccessResponse(
            success=True,
            data={
                "conversation_id": conv_id,
                "message": "Conversation created successfully"
            }
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to create conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/", response_model=SuccessResponse)
async def list_conversations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    collection: Optional[str] = Query(None, description="Filter by collection"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    manager = Depends(get_conversation_manager)
):
    """
    List conversations with filtering and pagination.
    
    Args:
        user_id: Filter by user ID
        status: Filter by status (active, paused, archived, deleted)
        tags: Filter by tags (must have all specified tags)
        collection: Filter by collection
        limit: Maximum results (1-200)
        offset: Offset for pagination
        
    Returns:
        Success response with list of conversations
    """
    try:
        conversations = manager.list_conversations(
            user_id=user_id,
            status=status,
            tags=tags or [],
            collection=collection,
            limit=limit,
            offset=offset
        )
        
        return SuccessResponse(
            success=True,
            data={
                "conversations": conversations,
                "count": len(conversations)
            }
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to list conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/{conversation_id}", response_model=SuccessResponse)
async def get_conversation(
    conversation_id: str,
    manager = Depends(get_conversation_manager)
):
    """
    Get a conversation by ID.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Success response with conversation details
    """
    try:
        conversation = manager.get_conversation(conversation_id)
        metadata = manager.get_conversation_metadata(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "Conversation not found"}
            )
        
        return SuccessResponse(
            success=True,
            data={
                "conversation": conversation.to_dict(),
                "metadata": metadata.to_dict() if metadata else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.put("/{conversation_id}", response_model=SuccessResponse)
async def update_conversation(
    conversation_id: str,
    updates: dict,
    manager = Depends(get_conversation_manager)
):
    """
    Update conversation metadata.
    
    Args:
        conversation_id: Conversation ID
        updates: Fields to update (title, tags, status, priority, etc.)
        
    Returns:
        Success response
    """
    try:
        success = manager.update_conversation_metadata(conversation_id, updates)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "Conversation not found"}
            )
        
        return SuccessResponse(
            success=True,
            data={"message": "Conversation updated successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to update conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.post("/{conversation_id}/archive", response_model=SuccessResponse)
async def archive_conversation(
    conversation_id: str,
    manager = Depends(get_conversation_manager)
):
    """
    Archive a conversation.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Success response
    """
    try:
        success = manager.archive_conversation(conversation_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "Conversation not found"}
            )
        
        return SuccessResponse(
            success=True,
            data={"message": "Conversation archived successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to archive conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.delete("/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: str,
    permanent: bool = Query(False, description="Permanently delete vs mark as deleted"),
    manager = Depends(get_conversation_manager)
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        permanent: If True, permanently delete; otherwise mark as deleted
        
    Returns:
        Success response
    """
    try:
        success = manager.delete_conversation(conversation_id, permanent=permanent)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "Conversation not found"}
            )
        
        return SuccessResponse(
            success=True,
            data={"message": "Conversation deleted successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to delete conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Search Endpoints

@router.get("/search", response_model=SuccessResponse)
async def search_conversations(
    query: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    manager = Depends(get_conversation_manager)
):
    """
    Search conversations by content.
    
    Args:
        query: Search query
        user_id: Filter by user ID
        limit: Maximum results (1-100)
        
    Returns:
        Success response with search results
    """
    try:
        results = manager.search_conversations(
            query=query,
            user_id=user_id,
            limit=limit
        )
        
        return SuccessResponse(
            success=True,
            data={
                "results": results,
                "count": len(results)
            }
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to search conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Statistics Endpoints

@router.get("/{conversation_id}/stats", response_model=SuccessResponse)
async def get_conversation_statistics(
    conversation_id: str,
    manager = Depends(get_conversation_manager)
):
    """
    Get statistics for a conversation.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Success response with conversation statistics
    """
    try:
        stats = manager.get_conversation_stats(conversation_id)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "Conversation not found"}
            )
        
        return SuccessResponse(
            success=True,
            data=stats.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get conversation stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Export/Import Endpoints

@router.get("/{conversation_id}/export", response_model=SuccessResponse)
async def export_conversation(
    conversation_id: str,
    format: str = Query("json", description="Export format (json, txt, markdown)"),
    include_metadata: bool = Query(True, description="Include metadata"),
    manager = Depends(get_conversation_manager)
):
    """
    Export a conversation.
    
    Args:
        conversation_id: Conversation ID
        format: Export format (json, txt, markdown)
        include_metadata: Whether to include metadata
        
    Returns:
        Success response with exported data
    """
    try:
        exported_data = manager.export_conversation(
            conversation_id=conversation_id,
            format=format,
            include_metadata=include_metadata
        )
        
        return SuccessResponse(
            success=True,
            data={
                "conversation_id": conversation_id,
                "format": format,
                "data": exported_data
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to export conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.post("/import", response_model=SuccessResponse, status_code=201)
async def import_conversation(
    data: str,
    format: str = Query("json", description="Import format"),
    user_id: str = Query("default", description="User ID to associate with"),
    manager = Depends(get_conversation_manager)
):
    """
    Import a conversation.
    
    Args:
        data: Conversation data
        format: Data format (json)
        user_id: User ID to associate with
        
    Returns:
        Success response with new conversation ID
    """
    try:
        conv_id = manager.import_conversation(
            data=data,
            format=format,
            user_id=user_id
        )
        
        return SuccessResponse(
            success=True,
            data={
                "conversation_id": conv_id,
                "message": "Conversation imported successfully"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": str(e)}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to import conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Tags Endpoints

@router.get("/tags", response_model=SuccessResponse)
async def get_all_tags(
    manager = Depends(get_conversation_manager)
):
    """
    Get all unique tags across conversations.
    
    Returns:
        Success response with list of tags
    """
    try:
        tags = manager.get_all_tags()
        
        return SuccessResponse(
            success=True,
            data={"tags": tags}
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get tags", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Maintenance Endpoints

@router.post("/cleanup", response_model=SuccessResponse)
async def cleanup_old_conversations(
    days: int = Query(30, ge=1, le=365, description="Days threshold"),
    manager = Depends(get_conversation_manager)
):
    """
    Archive or delete old conversations.
    
    Args:
        days: Number of days before archiving
        
    Returns:
        Success response with count of archived conversations
    """
    try:
        count = manager.cleanup_old_conversations(days=days)
        
        return SuccessResponse(
            success=True,
            data={
                "message": f"Archived {count} conversations",
                "archived_count": count
            }
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to cleanup conversations", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


# Analytics Endpoints

@router.get("/analytics/report", response_model=SuccessResponse)
async def get_analytics_report(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    include_conversations: int = Query(10, ge=1, le=50, description="Number of top conversations"),
    analytics_service = Depends(get_analytics_service)
):
    """
    Generate a comprehensive analytics report.
    
    Args:
        start_time: Start of report period (ISO format)
        end_time: End of report period (ISO format)
        include_conversations: Number of top conversations to include
        
    Returns:
        Success response with analytics report
    """
    try:
        # Parse time strings if provided
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        report = analytics_service.generate_report(
            start_time=start_dt,
            end_time=end_dt,
            include_conversations=include_conversations
        )
        
        return SuccessResponse(
            success=True,
            data=report.to_dict()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": f"Invalid time format: {str(e)}"}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to generate analytics report", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/analytics/insights", response_model=SuccessResponse)
async def get_analytics_insights(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    analytics_service = Depends(get_analytics_service)
):
    """
    Get analytics insights.
    
    Args:
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        
    Returns:
        Success response with list of insights
    """
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        insights = analytics_service.generate_insights(
            time_range=(start_dt, end_dt) if start_dt or end_dt else None
        )
        
        return SuccessResponse(
            success=True,
            data={
                "insights": [i.to_dict() for i in insights],
                "count": len(insights)
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": f"Invalid time format: {str(e)}"}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get analytics insights", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/analytics/metrics/{metric_type}", response_model=SuccessResponse)
async def get_metric_summary(
    metric_type: str,
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    analytics_service = Depends(get_analytics_service)
):
    """
    Get summary statistics for a specific metric.
    
    Args:
        metric_type: Type of metric (query_count, response_time, etc.)
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        
    Returns:
        Success response with metric summary
    """
    try:
        # Validate metric type
        try:
            metric_enum = MetricType(metric_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": f"Invalid metric type: {metric_type}"}
            )
        
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        summary = analytics_service.get_metric_summary(
            metric_type=metric_enum,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if not summary:
            return SuccessResponse(
                success=True,
                data={"message": "No data available for this metric"}
            )
        
        return SuccessResponse(
            success=True,
            data=summary.to_dict()
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": f"Invalid time format: {str(e)}"}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get metric summary", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/analytics/trends/{metric_type}", response_model=SuccessResponse)
async def get_metric_trend(
    metric_type: str,
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    granularity: str = Query("daily", description="Time granularity (hourly, daily, weekly, monthly)"),
    analytics_service = Depends(get_analytics_service)
):
    """
    Analyze trend of a metric over time.
    
    Args:
        metric_type: Type of metric
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        granularity: Time granularity
        
    Returns:
        Success response with trend analysis
    """
    try:
        # Validate metric type
        try:
            metric_enum = MetricType(metric_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": f"Invalid metric type: {metric_type}"}
            )
        
        # Validate granularity
        try:
            granularity_enum = TimeGranularity(granularity)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": f"Invalid granularity: {granularity}"}
            )
        
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        trend = analytics_service.analyze_trend(
            metric_type=metric_enum,
            start_time=start_dt,
            end_time=end_dt,
            granularity=granularity_enum
        )
        
        if not trend:
            return SuccessResponse(
                success=True,
                data={"message": "Insufficient data for trend analysis"}
            )
        
        return SuccessResponse(
            success=True,
            data=trend.to_dict()
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": f"Invalid time format: {str(e)}"}
        )
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to analyze metric trend", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )


@router.get("/analytics/realtime", response_model=SuccessResponse)
async def get_realtime_metrics(
    last_minutes: int = Query(60, ge=1, le=1440, description="Minutes of data to retrieve"),
    analytics_service = Depends(get_analytics_service)
):
    """
    Get recent metrics for real-time monitoring.
    
    Args:
        last_minutes: How many minutes of data to retrieve (1-1440)
        
    Returns:
        Success response with real-time metrics
    """
    try:
        metrics = analytics_service.get_realtime_metrics(last_minutes=last_minutes)
        
        # Convert to dict
        metrics_dict = {
            k: [dp.to_dict() for dp in v]
            for k, v in metrics.items()
        }
        
        return SuccessResponse(
            success=True,
            data=metrics_dict
        )
        
    except Exception as e:
        logger.bind(tag=LogTag.API.value).error("Failed to get realtime metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": str(e)}
        )

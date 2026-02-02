"""
Prometheus metrics for agentic RAG system.

This module defines custom Prometheus metrics for monitoring the agentic RAG system,
including query latency, embedding cache performance, task failures, and vector operations.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import CollectorRegistry
from typing import Optional

# Global registry
REGISTRY = CollectorRegistry()

# RAG Query Metrics
rag_query_latency = Histogram(
    'rag_query_latency_seconds',
    'RAG query processing latency in seconds',
    ['phase', 'collection'],  # phases: validation, embedding, search, llm, total
    registry=REGISTRY
)

rag_query_total = Counter(
    'rag_query_total',
    'Total RAG queries processed',
    ['collection', 'mode'],  # mode: rag, retrieval_only
    registry=REGISTRY
)

rag_query_errors = Counter(
    'rag_query_errors_total',
    'Total RAG query errors',
    ['collection', 'error_type'],
    registry=REGISTRY
)

# Embedding Metrics
embedding_cache_hits = Counter(
    'embedding_cache_hits_total',
    'Total embedding cache hits',
    ['model'],
    registry=REGISTRY
)

embedding_cache_misses = Counter(
    'embedding_cache_misses_total',
    'Total embedding cache misses',
    ['model'],
    registry=REGISTRY
)

embedding_generation_total = Counter(
    'embedding_generation_total',
    'Total embeddings generated',
    ['model', 'batch_size'],
    registry=REGISTRY
)

embedding_generation_errors = Counter(
    'embedding_generation_errors_total',
    'Total embedding generation errors',
    ['model', 'error_type'],
    registry=REGISTRY
)

embedding_batch_size = Histogram(
    'embedding_batch_size',
    'Embedding batch sizes',
    ['model'],
    buckets=(1, 8, 16, 32, 64, 128),
    registry=REGISTRY
)

# Vector Store Metrics
vector_insert_total = Counter(
    'vector_insert_total',
    'Total vectors inserted',
    ['collection'],
    registry=REGISTRY
)

vector_insert_errors = Counter(
    'vector_insert_errors_total',
    'Total vector insertion errors',
    ['collection', 'error_type'],
    registry=REGISTRY
)

vector_search_total = Counter(
    'vector_search_total',
    'Total vector searches',
    ['collection', 'top_k_range'],
    registry=REGISTRY
)

vector_search_errors = Counter(
    'vector_search_errors_total',
    'Total vector search errors',
    ['collection', 'error_type'],
    registry=REGISTRY
)

vector_search_latency = Histogram(
    'vector_search_latency_seconds',
    'Vector search latency in seconds',
    ['collection'],
    registry=REGISTRY
)

# Task Queue Metrics
task_queued = Counter(
    'task_queued_total',
    'Total tasks queued',
    ['queue', 'task_type'],  # queue: documents, embeddings; task_type: process_document, generate_embeddings
    registry=REGISTRY
)

task_started = Counter(
    'task_started_total',
    'Total tasks started',
    ['queue', 'task_type'],
    registry=REGISTRY
)

task_completed = Counter(
    'task_completed_total',
    'Total tasks completed',
    ['queue', 'task_type', 'status'],  # status: success, failure
    registry=REGISTRY
)

task_retries = Counter(
    'task_retries_total',
    'Total task retries',
    ['queue', 'task_type'],
    registry=REGISTRY
)

task_failures = Counter(
    'task_failures_total',
    'Total task failures',
    ['queue', 'task_type', 'error_type'],
    registry=REGISTRY
)

task_pending = Gauge(
    'task_pending',
    'Number of pending tasks',
    ['queue'],
    registry=REGISTRY
)

# LLM Metrics
llm_generation_total = Counter(
    'llm_generation_total',
    'Total LLM generations',
    ['model', 'type'],  # type: rag, summary, direct
    registry=REGISTRY
)

llm_generation_errors = Counter(
    'llm_generation_errors_total',
    'Total LLM generation errors',
    ['model', 'error_type'],
    registry=REGISTRY
)

llm_generation_latency = Histogram(
    'llm_generation_latency_seconds',
    'LLM generation latency in seconds',
    ['model', 'type'],
    registry=REGISTRY
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens processed',
    ['model', 'direction'],  # direction: input, output
    registry=REGISTRY
)

# Document Processing Metrics
document_upload_total = Counter(
    'document_upload_total',
    'Total documents uploaded',
    ['collection', 'format'],  # format: pdf, docx, txt, md
    registry=REGISTRY
)

document_processed_total = Counter(
    'document_processed_total',
    'Total documents processed',
    ['collection', 'format', 'status'],
    registry=REGISTRY
)

document_chunks_total = Counter(
    'document_chunks_total',
    'Total document chunks created',
    ['collection'],
    registry=REGISTRY
)

document_processing_errors = Counter(
    'document_processing_errors_total',
    'Total document processing errors',
    ['collection', 'format', 'error_type'],
    registry=REGISTRY
)

# Collection Metrics
collection_info = Info(
    'collection_info',
    'Collection information',
    ['name', 'dimension', 'vector_count'],
    registry=REGISTRY
)

collection_operations = Counter(
    'collection_operations_total',
    'Total collection operations',
    ['operation', 'collection'],  # operation: create, delete, list
    registry=REGISTRY
)

# Agent Metrics
agent_query_total = Counter(
    'agent_query_total',
    'Total agent queries processed',
    ['agent_type', 'collection'],
    registry=REGISTRY
)

agent_query_errors = Counter(
    'agent_query_errors_total',
    'Total agent query errors',
    ['agent_type', 'error_type'],
    registry=REGISTRY
)

agent_execution_steps = Histogram(
    'agent_execution_steps',
    'Number of steps taken by agent',
    ['agent_type'],
    buckets=(1, 2, 3, 5, 10, 15, 20),
    registry=REGISTRY
)

agent_execution_time = Histogram(
    'agent_execution_time_seconds',
    'Agent execution time in seconds',
    ['agent_type'],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
    registry=REGISTRY
)

agent_tool_usage = Counter(
    'agent_tool_usage_total',
    'Total tool invocations by agents',
    ['agent_type', 'tool_name'],
    registry=REGISTRY
)

agent_tool_errors = Counter(
    'agent_tool_errors_total',
    'Total tool execution errors',
    ['agent_type', 'tool_name', 'error_type'],
    registry=REGISTRY
)

agent_iterations_total = Counter(
    'agent_iterations_total',
    'Total reasoning iterations by agents',
    ['agent_type'],
    registry=REGISTRY
)

agent_memory_operations = Counter(
    'agent_memory_operations_total',
    'Total memory operations',
    ['operation'],  # operation: add, retrieve, clear
    registry=REGISTRY
)

agent_planning_time = Histogram(
    'agent_planning_time_seconds',
    'Time spent planning queries',
    ['query_type'],
    buckets=(0.1, 0.5, 1, 2, 5, 10),
    registry=REGISTRY
)


def get_registry() -> CollectorRegistry:
    """
    Get the Prometheus metrics registry.

    Returns:
        The global metrics registry
    """
    return REGISTRY


def reset_metrics() -> None:
    """
    Reset all metrics (useful for testing).

    This clears all metric values while keeping the metrics themselves.
    """
    REGISTRY.clear()


class QueryTimer:
    """
    Context manager for timing RAG query phases.

    This helper class provides a convenient way to time different
    phases of RAG query processing.

    Example:
        >>> with QueryTimer('validation', collection='my_collection'):
        ...     validate_query(query)
        >>> with QueryTimer('embedding', collection='my_collection'):
        ...     generate_embedding(query)
    """

    def __init__(self, phase: str, **labels: str) -> None:
        """
        Initialize query timer.

        Args:
            phase: The query phase being timed (validation, embedding, search, llm)
            **labels: Additional labels for the metric
        """
        self.phase = phase
        self.labels = labels

    def __enter__(self):
        """Start timing."""
        self.start_time = __import__('time').time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metric."""
        if hasattr(self, 'start_time'):
            elapsed = __import__('time').time() - self.start_time
            rag_query_latency.labels(phase=self.phase, **self.labels).observe(elapsed)

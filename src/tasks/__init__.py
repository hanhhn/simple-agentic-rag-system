"""
Background task processing module.

This module contains Celery tasks for asynchronous processing
of documents, embeddings, and other long-running operations.
"""
from src.tasks.celery_app import celery_app

# Import task modules to register them
from src.tasks import document_tasks, embedding_tasks

__all__ = ["celery_app", "document_tasks", "embedding_tasks"]

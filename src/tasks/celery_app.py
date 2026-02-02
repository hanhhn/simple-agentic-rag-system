"""
Celery application configuration.

This module sets up the Celery application for background task processing.
"""
from celery import Celery
from celery.signals import setup_logging, worker_process_init

from src.core.config import get_config
from src.core.logging import configure_logging, get_logger


# Configure logging before creating Celery app
configure_logging()
logger = get_logger(__name__)

# Get configuration
config = get_config()

# Create Celery app
celery_app = Celery(
    "rag_system",
    broker=config.celery.broker_url,
    backend=config.celery.result_backend,
)

# Disable Celery's default logging setup to use our structured logging
@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers."""
    configure_logging()
    logger.info("Celery logging configured")


@worker_process_init.connect
def init_worker_process(*args, **kwargs):
    """
    Initialize worker process after fork.
    
    This signal is sent after a worker process has been forked.
    For prefork pools, this is where we can safely initialize
    resources that don't work well with fork (like PyTorch models).
    
    Note: For thread/solo pools, this may not be called or may
    be called differently, so we use lazy loading in services.
    """
    logger.info(
        "Worker process initialized",
        worker_pool=config.celery.worker_pool
    )
    
    # Clear any cached models to force reload after fork
    # This helps avoid issues with models loaded before fork
    try:
        from src.embedding.model_loader import ModelLoader
        # The ModelLoader uses a class-level cache, but each worker
        # process will have its own memory space, so this is safe
        logger.info("Worker process ready for model loading")
    except Exception as e:
        logger.warning(
            "Error during worker process initialization",
            error=str(e)
        )


logger.info(
    "Celery app initialized",
    broker=config.celery.broker_url,
    backend=config.celery.result_backend,
    worker_pool=config.celery.worker_pool,
)

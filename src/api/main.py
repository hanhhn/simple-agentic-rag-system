"""
FastAPI application entry point.
"""
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.logging import configure_logging, get_logger, LogTag
from src.core.config import get_config
from src.api.routes import health, documents, query, collections, tasks, models, agents, conversations
from src.api.middleware import logging as logging_middleware
from src.api.middleware import rate_limit as rate_limit_middleware
from src.api.middleware import tracing as tracing_middleware

# Configure logging
configure_logging()
logger = get_logger(__name__)
config = get_config()

# Initialize Prometheus instrumentator before creating the app
instrumentator = Instrumentator()


# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check and readiness endpoints for monitoring system status.",
    },
    {
        "name": "Collections",
        "description": "Manage vector collections. Collections are containers for document embeddings.",
    },
    {
        "name": "Documents",
        "description": "Upload, list, download, and delete documents. Documents are processed and chunked for embedding.",
    },
    {
        "name": "Query",
        "description": "Query the RAG system. Search documents and generate answers using retrieval-augmented generation.",
    },
    {
        "name": "Tasks",
        "description": "Monitor and manage background tasks (e.g., document processing tasks).",
    },
    {
        "name": "Models",
        "description": "Manage LLM and embedding models (list, switch, view info, clear cache).",
    },
    {
        "name": "Agents",
        "description": "Intelligent agents with tool capabilities for complex queries. Uses ReAct pattern for reasoning and acting.",
    },
    {
        "name": "Root",
        "description": "Root endpoint and API information.",
    },
]

#
# Create FastAPI application
app = FastAPI(
    title=config.app.app_name,
    version=config.app.api_version,
    description="""
    An Agentic RAG (Retrieval-Augmented Generation) system with intelligent agents.
    
    ## Features
    
    * **Collection Management**: Create and manage vector collections
    * **Document Processing**: Upload documents (PDF, TXT, MD, DOCX) with automatic chunking and embedding
    * **RAG Queries**: Query documents using semantic search with LLM-powered answer generation
    * **Agentic Queries**: Use intelligent agents with tool capabilities for complex queries
    * **Multi-step Reasoning**: Agents can reason, plan, and execute multi-step tasks
    * **Task Management**: Monitor background document processing tasks
    * **Health Monitoring**: Check system and service health status
    
    ## Getting Started
    
    1. Create a collection using the Collections API
    2. Upload documents to the collection
    3. Use the Agent API for intelligent query processing with tools
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "RAG System API",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {
            "url": f"http://{config.app.app_host}:{config.app.app_port}",
            "description": "Development server",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local server",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tracing middleware (must be first to set trace_id in context)
tracing_middleware.add_tracing_middleware(app)

# Add logging middleware
logging_middleware.add_logging_middleware(app)

# Add rate limiting middleware (if enabled)
if config.security.rate_limit_enabled:
    rate_limit_middleware.add_rate_limit_middleware(app)
    logger.bind(tag=LogTag.MIDDLEWARE.value).info("Rate limiting middleware enabled")
else:
    logger.bind(tag=LogTag.MIDDLEWARE.value).info("Rate limiting middleware disabled")

# Include routers
app.include_router(health.router)
app.include_router(documents.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(collections.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")

# Instrument the app with Prometheus (must be done before startup)
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Mount static files for frontend (if frontend/dist exists)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount assets directory
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Serve vite.svg if it exists
    vite_svg = frontend_dist / "vite.svg"
    if vite_svg.exists():
        @app.get("/vite.svg")
        async def serve_vite_svg():
            return FileResponse(str(vite_svg))


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.bind(tag=LogTag.STARTUP.value).info("Application starting up", app_name=config.app.app_name, version=config.app.api_version)
    logger.bind(tag=LogTag.SYSTEM.value).info("Prometheus metrics enabled at /metrics")
    
    # Initialize necessary services
    # Services are lazily loaded via dependencies, so no explicit init needed


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.bind(tag=LogTag.SHUTDOWN.value).info("Application shutting down")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: Incoming request
        exc: Exception that occurred
        
    Returns:
        JSON response with error details
    """
    logger.bind(tag=LogTag.ERROR.value).error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        exception_type=type(exc).__name__,
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {
                "exception": type(exc).__name__,
                "message": str(exc)
            }
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - serves frontend if available, otherwise returns API info.
    
    Returns:
        Frontend index.html or API metadata
    """
    # Try to serve frontend index.html if it exists
    frontend_index = Path(__file__).parent.parent.parent / "frontend" / "dist" / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    
    # Fallback to API info if frontend not available
    return {
        "name": config.app.app_name,
        "version": config.app.api_version,
        "description": "RAG System API",
        "docs": "/docs",
        "health": "/health"
    }

# Catch-all route for SPA routing (must be last)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    """
    Catch-all route for SPA routing.
    Serves index.html for non-API routes.
    """
    # Don't interfere with API routes
    if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    # Serve frontend index.html for SPA routing
    frontend_index = Path(__file__).parent.parent.parent / "frontend" / "dist" / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    
    return JSONResponse(status_code=404, content={"detail": "Not found"})


if __name__ == "__main__":
    import uvicorn
    
    logger.bind(tag=LogTag.STARTUP.value).info(
        "Starting server",
        host=config.app.app_host,
        port=config.app.app_port,
        debug=config.app.app_debug
    )
    
    uvicorn.run(
        "src.api.main:app",
        host=config.app.app_host,
        port=config.app.app_port,
        reload=config.app.app_debug,
        timeout_keep_alive=config.app.timeout_keep_alive,
        log_level="info" if not config.app.app_debug else "debug"
    )

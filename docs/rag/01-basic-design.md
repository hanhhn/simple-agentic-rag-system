# Basic Design - RAG System

## System Overview

The Retrieval-Augmented Generation (RAG) System is an intelligent document querying platform that combines large language models with vector-based information retrieval. The system enables users to upload documents, process them into embeddings, and ask natural language questions that are answered based on the document content.

### Purpose

To provide a scalable, efficient, and user-friendly interface for document-based question answering that leverages local LLM models for privacy and cost-effectiveness.

### Key Features

- Document ingestion and processing (PDF, TXT, MD, DOCX)
- Automated chunking and embedding generation
- Vector similarity search using Qdrant
- Context-aware response generation using local LLMs
- RESTful API for integration
- Support for multiple document collections

## Core Components and Responsibilities

### 1. API Layer

**Responsibilities:**
- Expose REST endpoints for client applications
- Handle authentication and authorization
- Validate incoming requests
- Return responses in standardized format
- Rate limiting and request throttling

**Key Endpoints:**

Document Management:
- `POST /api/v1/documents/upload` - Upload document (async, returns task ID)
- `GET /api/v1/documents/list/{collection}` - List documents in collection
- `GET /api/v1/documents/download/{collection}/{filename}` - Download document
- `DELETE /api/v1/documents/{collection}/{filename}` - Delete document

Task Management:
- `GET /api/v1/tasks/{task_id}` - Get task status and result
- `POST /api/v1/tasks/{task_id}/revoke` - Cancel/revoke task
- `GET /api/v1/tasks/` - List active tasks

Query Operations:
- `POST /api/v1/query` - Query the RAG system
- `GET /api/v1/query/history` - Get query history

Collection Management:
- `GET /api/v1/collections` - List collections
- `POST /api/v1/collections` - Create collection
- `GET /api/v1/collections/{name}` - Get collection details
- `DELETE /api/v1/collections/{name}` - Delete collection

Model Management:
- `POST /api/v1/models/load` - Load a model
- `PUT /api/v1/models/switch` - Switch active model
- `GET /api/v1/models` - List available models

Batch Operations:
- `GET /api/v1/batches/{id}` - Get batch processing status

### 2. Document Processor Service

**Responsibilities:**
- Parse various document formats
- Extract text content
- Clean and normalize text
- Split documents into chunks
- Manage chunk metadata

**Supported Formats:**
- PDF files
- Plain text (.txt)
- Markdown (.md)
- Word documents (.docx)
- HTML content

### 3. Embedding Service

**Responsibilities:**
- Generate vector embeddings for text chunks
- Manage embedding model selection
- Handle batch processing for efficiency
- Cache embeddings to avoid recomputation
- Implement cache locking to prevent race conditions
- Support multiple embedding models

**Cache Concurrency Control:**
- Uses atomic operations for cache check and update
- Implements distributed locks for multi-instance deployments
- Cache-aside pattern with lock to prevent duplicate embedding generation
- When multiple requests process identical text, only one generates embeddings

**Default Model:** `all-MiniLM-L6-v2` or similar lightweight local model

### 4. Vector Store Service (Qdrant)

**Responsibilities:**
- Store and index document embeddings
- Perform similarity search
- Manage collections and indexes
- Handle CRUD operations for vectors
- Optimize query performance

**Configuration:**
- In-memory or persistent storage
- Configurable distance metrics (Cosine, Euclidean, Dot)
- Sharding for scalability
- Replication for high availability

### 5. Task Queue Service (Celery + Redis) - IMPLEMENTED

**Responsibilities:**
- Process document uploads asynchronously
- Generate embeddings in background
- Manage task queues (documents, embeddings)
- Track task status and results
- Retry failed tasks automatically
- Scale workers independently

**Technology:**
- **Celery 5.3.4**: Distributed task queue
- **Redis 7**: Message broker and result backend
- **Queues**: Separate queues for documents (I/O) and embeddings (CPU/GPU)

**Task Types:**
- `process_document_task`: Parse and chunk documents
- `generate_embeddings_task`: Generate and store embeddings
- `delete_document_task`: Delete documents and vectors

**Benefits:**
- Non-blocking API responses
- Horizontal scalability
- Automatic retry on failures
- Task status tracking

**Implementation:**
- Location: `src/tasks/`
- Configuration: `src/tasks/celery_app.py`
- Tasks: `src/tasks/document_tasks.py`, `src/tasks/embedding_tasks.py`
- API: `src/api/routes/tasks.py` for status tracking

### 6. LLMService

**Responsibilities:**
- Manage local LLM models via Ollama
- Generate context-aware responses
- Handle prompt engineering and templates
- Manage model loading and unloading
- Support streaming responses

**Default Model:** `llama2` or `mistral` via Ollama

### 7. QueryProcessor

**Responsibilities:**
- Parse user queries
- Generate query embeddings
- Retrieve relevant documents from vector store
- Construct context for LLM
- Format and return final response
- Handle edge cases and errors

**RAG Pipeline:**
1. Receive user query
2. Generate query embedding
3. Perform similarity search in Qdrant
4. Retrieve top-k relevant chunks
5. Construct prompt with context
6. Generate response using LLM
7. Return formatted answer

### 8. Storage Manager

**Responsibilities:**
- Store original documents
- Manage document metadata
- Track processing status
- Handle file lifecycle
- Implement cleanup policies

## Technology Stack

### Backend

- **Language:** Python 3.11+
- **Framework:** FastAPI or Flask
- **Async Support:** asyncio
- **Type Checking:** mypy

### Vector Database

- **Vector Store:** Qdrant
- **Deployment:** Docker or local installation
- **Client:** qdrant-client Python SDK

### LLM Integration

- **LLM Runtime:** Ollama
- **Models:** Llama 2, Mistral, or other open-source models
- **API:** Ollama HTTP API

### Embedding Models

- **Model:** sentence-transformers
- **Backend:** PyTorch
- **Inference:** CPU/GPU accelerated

### Document Processing

- **PDF:** PyPDF2 or pdfplumber
- **Word:** python-docx
- **Text:** Built-in Python libraries
- **Chunking:** LangChain or custom implementation

### Task Queue

- **Task Queue:** Celery 5.3.4
- **Message Broker:** Redis 7
- **Result Backend:** Redis 7
- **Worker Management:** Docker Compose or manual scripts

### Utilities

- **Environment:** python-dotenv
- **Logging:** structlog
- **Validation:** pydantic
- **Testing:** pytest
- **HTTP Client:** httpx

## Design Principles

### 1. Separation of Concerns

Each component has a single, well-defined responsibility. The system is divided into distinct layers (API, Service, Data) with clear boundaries.

### 2. Scalability

- Horizontal scaling via containerization
- Efficient vector storage and retrieval
- Asynchronous processing for I/O operations
- Connection pooling for database operations

### 3. Privacy and Data Security

- All processing runs locally (no external API calls for LLM)
- Optional encryption for stored documents
- Secure authentication and authorization
- Audit logging for sensitive operations

### 4. Performance

- Embedding caching to avoid recomputation
- Batch processing for efficiency
- Vector similarity search with sub-second latency
- Optimized chunk sizes for balance of context and performance

### 5. Extensibility

- Plugin architecture for embedding models
- Support for multiple LLM providers (if needed)
- Configurable chunking strategies
- Modular component design

### 6. Error Resilience

- Graceful degradation on failures
- Retry mechanisms for transient errors
- Comprehensive error logging
- User-friendly error messages

## Assumptions

### System Requirements

- Python 3.11 or higher installed
- Sufficient RAM for local LLM inference (minimum 8GB, recommended 16GB+)
- Disk space for document storage and vector database
- Network access for initial model downloads (Ollama)

### Performance Expectations

- Document ingestion: ~1-5 MB/second depending on model and hardware
- Query response: < 3 seconds for typical queries
- Embedding generation: ~1000 chunks/minute on CPU

### Usage Patterns

- Typical document size: 1-50 MB per file
- Query frequency: 1-100 queries per minute
- Concurrent users: 1-50 (depends on hardware)
- Total documents: 1-10,000 documents (scales with Qdrant)

### Limitations

- Single-tenant deployment (designed for self-hosting)
- No built-in multi-user access control (can be added)
- Limited to text-based content (images not processed)
- Processing speed depends on local hardware

## System Scope

### In Scope

- Document upload and processing
- Vector-based similarity search
- RAG-based question answering
- REST API for integration
- Support for common document formats
- Collection management
- Query history (optional)

### Out of Scope

- Real-time document updates (documents are re-indexed)
- Multi-user access control (can be added later)
- Distributed deployment (single-node design)
- Web UI (API-only implementation)
- Image and video processing
- Multi-modal retrieval
- Advanced NLP features (NER, entity extraction, etc.)
- Chat history and conversation memory (can be added)

## Module Organization

```
simple-rag-system/
├── src/
│   ├── api/                    # Presentation Layer
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── routes/              # API route definitions
│   │   │   ├── documents.py
│   │   │   ├── query.py
│   │   │   ├── collections.py
│   │   │   ├── tasks.py         # Task status tracking endpoints
│   │   │   └── health.py
│   │   └── models/              # Pydantic models
│   │       ├── document.py
│   │       ├── query.py
│   │       ├── collection.py
│   │       ├── task.py          # Task status models
│   │       └── common.py
│   ├── services/               # Service Layer (Business Logic)
│   │   ├── __init__.py
│   │   ├── document_processor.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── llm_service.py
│   │   ├── query_processor.py
│   │   └── storage_manager.py
│   ├── tasks/                  # Background Task Processing (IMPLEMENTED)
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery application configuration
│   │   ├── document_tasks.py   # Document processing Celery tasks
│   │   └── embedding_tasks.py  # Embedding generation Celery tasks
│   ├── core/                   # Core utilities (Infrastructure Layer)
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── logging.py           # Logging setup
│   │   └── monitoring.py        # Metrics and monitoring
│   └── utils/                  # Utility functions (Infrastructure Layer)
│       ├── __init__.py
│       ├── text_chunker.py
│       ├── validators.py
│       └── cache.py            # Cache utilities
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── 01-basic-design.md       # This document
│   ├── 02-c4-model.md
│   ├── 03-high-level-design.md
│   ├── 04-data-flow.md
│   └── 05-sequence-diagrams.md
├── requirements.txt
├── .env.example
└── README.md
```

## Next Steps

For detailed architectural diagrams and design specifications, refer to:

- **[C4 Model](02-c4-model.md)** - System architecture with Context, Container, and Component diagrams
- **[High-Level Design](03-high-level-design.md)** - Architectural patterns and deployment strategy
- **[Data Flow](04-data-flow.md)** - Detailed data flow diagrams
- **[Sequence Diagrams](05-sequence-diagrams.md)** - Interaction sequences between components

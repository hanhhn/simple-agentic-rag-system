# C4 Model - RAG System Architecture

## Overview

This document provides a comprehensive C4 model for the RAG system, documenting the architecture from high-level context to detailed component design. The C4 model consists of four levels:

1. **Context Diagram** - System boundaries and external actors
2. **Container Diagram** - Major containers and their interactions
3. **Component Diagram** - Internal components of each container
4. **Code Diagram** - Key classes and their relationships

## 1. Context Diagram

The Context Diagram shows the RAG System in the center and the external actors that interact with it.

```mermaid
flowchart TB
    User[User] -->|Upload documents, Query documents| RAGSystem[RAG System]

    subgraph RAGSystem[ ]
        RAGSystemNode[RAG System]
    end

    Developer[Developer] -->|Configure, Monitor| RAGSystem

    Admin[Administrator] -->|Deploy, Maintain| RAGSystem

    RAGSystem -->|Store embeddings| Qdrant[Qdrant Vector Database]

    RAGSystem -->|Generate responses| Ollama[Ollama LLM Runtime]

    style RAGSystem fill:#e1f5ff
    style User fill:#f0f0f0
    style Developer fill:#f0f0f0
    style Admin fill:#f0f0f0
    style Qdrant fill:#fff4e1
    style Ollama fill:#fff4e1
```

### Actors and Descriptions

| Actor | Type | Description |
|-------|------|-------------|
| **User** | Person | End users who upload documents and query the system via API or UI |
| **Developer** | Person | Developers who configure and monitor the system |
| **Administrator** | Person | DevOps engineers who deploy and maintain the system |
| **Qdrant** | System | Vector database that stores document embeddings |
| **Ollama** | System | Local LLM runtime for generating responses |

### Interactions

- **User → RAG System**: Upload documents, query documents, retrieve responses
- **Developer → RAG System**: Configuration, monitoring, debugging
- **Administrator → RAG System**: Deployment, maintenance, scaling
- **RAG System → Qdrant**: Store and retrieve vector embeddings
- **RAG System → Ollama**: Generate responses using local LLM models

## 2. Container Diagram

The Container Diagram shows the major containers (applications, data stores, etc.) within the RAG System and how they interact.

```mermaid
flowchart TB
    subgraph RAGSystem["RAG System"]
        direction TB

        APIServer[API Server<br/>FastAPI Application]

        RedisBroker[Redis<br/>Message Broker & Result Backend]

        CeleryWorker[Celery Worker<br/>Background Task Processor]

        DocumentProcessor[Document Processor<br/>Document Ingestion Service]

        EmbeddingService[Embedding Service<br/>Vector Generation]

        VectorStoreService[Vector Store Service<br/>Qdrant Client]

        LLMService[LLM Service<br/>Ollama Integration]

        QueryProcessor[QueryProcessor<br/>RAG Orchestration]

        StorageManager[Storage Manager<br/>Document Lifecycle]
    end

    User[User Client] -->|HTTP Requests| APIServer

    APIServer -->|Enqueue Tasks| RedisBroker
    APIServer -->|Query Task Status| RedisBroker

    RedisBroker -->|Poll Tasks| CeleryWorker

    CeleryWorker -->|Process Documents| DocumentProcessor

    DocumentProcessor -->|Store Files| StorageManager

    DocumentProcessor -->|Enqueue Embedding Tasks| RedisBroker

    CeleryWorker -->|Generate Embeddings| EmbeddingService

    EmbeddingService -->|Store Vectors| VectorStoreService

    APIServer -->|Handle Queries| QueryProcessor

    QueryProcessor -->|Retrieve Similar Vectors| VectorStoreService

    QueryProcessor -->|Generate Response| LLMService

    StorageManager -->|Store Documents| LocalFS[Local File System]

    VectorStoreService -->|Persist Vectors| QdrantDB[(Qdrant Database)]

    LLMService -->|Inference| OllamaRuntime[Ollama Runtime]

    style APIServer fill:#e1f5ff
    style RedisBroker fill:#fff3e0
    style CeleryWorker fill:#fff3e0
    style DocumentProcessor fill:#e8f5e9
    style EmbeddingService fill:#e8f5e9
    style VectorStoreService fill:#e8f5e9
    style LLMService fill:#e8f5e9
    style QueryProcessor fill:#e8f5e9
    style StorageManager fill:#fff3e0
    style User fill:#f0f0f0
    style QdrantDB fill:#fff4e1
    style OllamaRuntime fill:#fff4e1
    style LocalFS fill:#fff4e1
```

### Containers and Descriptions

| Container | Technology | Responsibilities |
|-----------|------------|------------------|
| **API Server** | FastAPI, Python | REST API endpoints, request validation, authentication, response formatting, task enqueueing |
| **Redis** | Redis 7 | Message broker for task queues, result backend for task status and results |
| **Celery Worker** | Celery 5.3.4 | Background task processor, listens to queues and executes tasks asynchronously |
| **Document Processor** | Python | Parse documents, extract text, chunking, metadata extraction |
| **Embedding Service** | sentence-transformers | Generate vector embeddings for text chunks |
| **Vector Store Service** | qdrant-client | Manage Qdrant operations (CRUD, search, collections) |
| **LLM Service** | Ollama API | Manage local LLM models, generate responses, handle streaming |
| **QueryProcessor** | Python | Orchestrate RAG pipeline: query embedding, retrieval, context construction, response generation |
| **Storage Manager** | Python | Store original documents, manage metadata, track processing status, handle file lifecycle and cleanup |

### Container Interactions

1. **Document Ingestion Flow (with Task Queue):**
   - User uploads document → API Server
   - API Server validates and saves file → Storage Manager
   - API Server enqueues `process_document_task` → Redis (queue: "documents")
   - API Server returns task ID immediately (non-blocking)
   - Celery Worker polls Redis queue → Picks up task
   - Celery Worker executes task → Document Processor
   - Document Processor parses and chunks document
   - Document Processor enqueues `generate_embeddings_task` → Redis (queue: "embeddings")
   - Celery Worker (or another worker) picks up embedding task
   - Celery Worker generates embeddings → Embedding Service
   - Embedding Service stores vectors → Vector Store Service → Qdrant Database
   - Task results and status saved to Redis result backend
   - User can query task status via API → Redis result backend

2. **Query Flow:**
   - User sends query → API Server → QueryProcessor
   - QueryProcessor generates query embedding → Vector Store Service
   - Vector Store Service retrieves similar vectors → QueryProcessor
   - QueryProcessor constructs context → LLM Service
   - LLM Service generates response → QueryProcessor → API Server → User

3. **Document Deletion Flow:**
   - User requests deletion → API Server
   - API Server enqueues deletion task → Task Queue
   - Task Queue deletes file → Storage Manager → Local File System
   - Task Queue deletes vectors → Vector Store Service → Qdrant Database
   - Storage Manager removes metadata

## 3. Component Diagram

### 3.1 API Server Components

```mermaid
flowchart TB
    subgraph APIServerContainer["API Server (FastAPI)"]
        direction TB

        FastAPIApp[FastAPI Application]

        AuthMiddleware[Authentication<br/>Middleware]

        RateLimiter[Rate Limiter]

        DocumentRoutes[Document Routes]

        QueryRoutes[Query Routes]

        CollectionRoutes[Collection Routes]

        RequestValidator[Request Validator]

        ResponseFormatter[Response Formatter]

        ErrorHandler[Error Handler]

        APILogger[API Logger]

        FastAPIApp --> AuthMiddleware
        FastAPIApp --> RateLimiter
        FastAPIApp --> DocumentRoutes
        FastAPIApp --> QueryRoutes
        FastAPIApp --> CollectionRoutes

        DocumentRoutes --> RequestValidator
        DocumentRoutes --> ResponseFormatter
        QueryRoutes --> RequestValidator
        QueryRoutes --> ResponseFormatter
        CollectionRoutes --> RequestValidator
        CollectionRoutes --> ResponseFormatter

        FastAPIApp --> ErrorHandler
        FastAPIApp --> APILogger

        style FastAPIApp fill:#e1f5ff
        style DocumentRoutes fill:#e8f5e9
        style QueryRoutes fill:#e8f5e9
        style CollectionRoutes fill:#e8f5e9
    end
```

**API Server Components:**

- **FastAPI Application**: Main application entry point
- **Authentication Middleware**: JWT token validation
- **Rate Limiter**: Prevent API abuse
- **Document Routes**: Endpoints for document management
- **Query Routes**: Endpoints for querying the system
- **Collection Routes**: Endpoints for collection management
- **Request Validator**: Pydantic-based validation
- **Response Formatter**: Standardize API responses
- **Error Handler**: Centralized error handling
- **API Logger**: Request/response logging

### 3.2 Document Processor Components

```mermaid
flowchart TB
    subgraph DocumentProcessorContainer["Document Processor"]
        direction TB

        DocumentHandler[Document Handler]

        TextExtractor[Text Extractor]

        PDFParser[PDF Parser]

        WordParser[Word Parser]

        TextParser[Text Parser]

        TextCleaner[Text Cleaner]

        TextChunker[Text Chunker]

        MetadataExtractor[Metadata Extractor]

        ChunkManager[Chunk Manager]

        DocumentHandler --> TextExtractor

        TextExtractor --> PDFParser
        TextExtractor --> WordParser
        TextExtractor --> TextParser

        TextExtractor --> TextCleaner

        TextCleaner --> TextChunker

        TextChunker --> MetadataExtractor

        TextChunker --> ChunkManager

        MetadataExtractor --> ChunkManager

        style DocumentHandler fill:#e1f5ff
        style TextExtractor fill:#e8f5e9
        style TextChunker fill:#e8f5e9
    end
```

**Document Processor Components:**

- **Document Handler**: Main orchestrator for document processing
- **Text Extractor**: Detects file type and delegates to appropriate parser
- **PDF Parser**: Extracts text from PDF files
- **Word Parser**: Extracts text from DOCX files
- **Text Parser**: Reads plain text and markdown files
- **Text Cleaner**: Normalizes text, removes special characters
- **Text Chunker**: Splits text into manageable chunks
- **Metadata Extractor**: Extracts metadata (title, author, date)
- **Chunk Manager**: Manages chunk lifecycle and storage

### 3.3 Embedding Service Components

```mermaid
flowchart TB
    subgraph EmbeddingServiceContainer["Embedding Service"]
        direction TB

        EmbeddingManager[Embedding Manager]

        ModelLoader[Model Loader]

        EmbeddingCache[Embedding Cache]

        BatchProcessor[Batch Processor]

        VectorNormalizer[Vector Normalizer]

        ModelRegistry[Model Registry]

        EmbeddingManager --> ModelLoader
        EmbeddingManager --> EmbeddingCache
        EmbeddingManager --> BatchProcessor

        ModelLoader --> ModelRegistry

        BatchProcessor --> VectorNormalizer

        style EmbeddingManager fill:#e1f5ff
        style EmbeddingCache fill:#fff3e0
        style BatchProcessor fill:#e8f5e9
    end
```

**Embedding Service Components:**

- **Embedding Manager**: Main orchestrator for embedding generation
- **Model Loader**: Loads and manages embedding models
- **Embedding Cache**: Caches embeddings to avoid recomputation
- **Batch Processor**: Processes multiple chunks in batches for efficiency
- **Vector Normalizer**: Normalizes vectors for consistent similarity calculations
- **Model Registry**: Manages available embedding models

### 3.4 Vector Store Service Components

```mermaid
flowchart TB
    subgraph VectorStoreServiceContainer["Vector Store Service"]
        direction TB

        QdrantClient[Qdrant Client]

        CollectionManager[Collection Manager]

        VectorIndexer[Vector Indexer]

        SearchEngine[Search Engine]

        ConnectionPool[Connection Pool]

        QueryOptimizer[Query Optimizer]

        QdrantClient --> CollectionManager
        QdrantClient --> VectorIndexer
        QdrantClient --> SearchEngine
        QdrantClient --> ConnectionPool
        QdrantClient --> QueryOptimizer

        style QdrantClient fill:#e1f5ff
        style CollectionManager fill:#e8f5e9
        style SearchEngine fill:#e8f5e9
    end
```

**Vector Store Service Components:**

- **Qdrant Client**: Main interface to Qdrant database
- **Collection Manager**: Creates, deletes, and manages collections (handles all collection-related operations)
- **Vector Indexer**: Indexes vectors for efficient search
- **Search Engine**: Performs similarity searches
- **Connection Pool**: Manages connections to Qdrant
- **Query Optimizer**: Optimizes queries for performance

**Note**: Collection management operations (create, delete, list collections) are handled by the Vector Store Service through the Collection Manager component, not by a separate service.

### 3.5 LLM Service Components

```mermaid
flowchart TB
    subgraph LLMServiceContainer["LLM Service"]
        direction TB

        OllamaClient[Ollama Client]

        ModelManager[Model Manager]

        PromptBuilder[Prompt Builder]

        ResponseGenerator[Response Generator]

        StreamHandler[Stream Handler]

        ModelCache[Model Cache]

        TemplateEngine[Template Engine]

        OllamaClient --> ModelManager
        OllamaClient --> ResponseGenerator

        ModelManager --> ModelCache

        ResponseGenerator --> PromptBuilder
        ResponseGenerator --> StreamHandler

        PromptBuilder --> TemplateEngine

        style OllamaClient fill:#e1f5ff
        style ModelManager fill:#e8f5e9
        style PromptBuilder fill:#e8f5e9
    end
```

**LLM Service Components:**

- **Ollama Client**: Main interface to Ollama runtime
- **Model Manager**: Manages LLM model loading and unloading
- **Prompt Builder**: Constructs prompts with context and templates
- **Response Generator**: Generates responses using LLM
- **Stream Handler**: Handles streaming responses
- **Model Cache**: Caches loaded models
- **Template Engine**: Manages prompt templates

### 3.6 Query Processor Components

```mermaid
flowchart TB
    subgraph QueryProcessorContainer["Query Processor"]
        direction TB

        QueryOrchestrator[Query Orchestrator]

        QueryEmbedder[Query Embedder]

        ContextBuilder[Context Builder]

        ResponseRefiner[Response Refiner]

        RelevanceScorer[Relevance Scorer]

        QuerySanitizer[Query Sanitizer]

        ResultFormatter[Result Formatter]

        QueryOrchestrator --> QuerySanitizer
        QueryOrchestrator --> QueryEmbedder
        QueryOrchestrator --> ContextBuilder
        QueryOrchestrator --> ResponseRefiner
        QueryOrchestrator --> ResultFormatter

        ContextBuilder --> RelevanceScorer

        style QueryOrchestrator fill:#e1f5ff
        style QueryEmbedder fill:#e8f5e9
        style ContextBuilder fill:#e8f5e9
        style ResponseRefiner fill:#e8f5e9
    end
```

**Query Processor Components:**

- **Query Orchestrator**: Main orchestrator for RAG pipeline
- **Query Embedder**: Generates embeddings for user queries
- **Query Sanitizer**: Cleans and validates user queries
- **Context Builder**: Constructs context from retrieved documents
- **Relevance Scorer**: Scores and ranks retrieved chunks
- **Response Refiner**: Post-processes and refines LLM responses
- **Result Formatter**: Formats final response for API

### 3.7 Storage Manager Components

```mermaid
flowchart TB
    subgraph StorageManagerContainer["Storage Manager"]
        direction TB

        FileManager[File Manager]

        MetadataManager[Metadata Manager]

        LifecycleManager[Lifecycle Manager]

        CleanupManager[Cleanup Manager]

        StorageTracker[Storage Tracker]

        ValidationManager[Validation Manager]

        FileManager --> MetadataManager
        FileManager --> StorageTracker
        FileManager --> ValidationManager

        MetadataManager --> LifecycleManager
        LifecycleManager --> CleanupManager

        style FileManager fill:#e1f5ff
        style MetadataManager fill:#e8f5e9
        style LifecycleManager fill:#e8f5e9
        style CleanupManager fill:#e8f5e9
    end
```

**Storage Manager Components:**

- **File Manager**: Handles file operations (upload, delete, retrieve)
- **Metadata Manager**: Manages document metadata and processing status
- **Lifecycle Manager**: Tracks document lifecycle stages
- **Cleanup Manager**: Implements cleanup policies and scheduled deletions
- **Storage Tracker**: Monitors storage usage and capacity
- **Validation Manager**: Validates file types, sizes, and integrity

### 3.8 Monitoring and Logging Components

```mermaid
flowchart TB
    subgraph MonitoringLoggingContainer["Monitoring and Logging"]
        direction TB

        MetricsCollector[Metrics Collector]

        Logger[Structured Logger]

        PerformanceTracker[Performance Tracker]

        ErrorHandler[Error Handler]

        AlertManager[Alert Manager]

        Dashboard[Dashboard]

        MetricsCollector --> PerformanceTracker
        MetricsCollector --> AlertManager

        Logger --> ErrorHandler
        ErrorHandler --> AlertManager

        PerformanceTracker --> Dashboard
        AlertManager --> Dashboard

        style MetricsCollector fill:#e1f5ff
        style Logger fill:#e8f5e9
        style PerformanceTracker fill:#e8f5e9
        style ErrorHandler fill:#e8f5e9
        style AlertManager fill:#fff3e0
    end
```

**Monitoring and Logging Components:**

- **Metrics Collector**: Collects application and system metrics
- **Structured Logger**: Centralized logging with structured output
- **Performance Tracker**: Tracks performance metrics (latency, throughput)
- **Error Handler**: Centralized error handling and reporting
- **Alert Manager**: Manages alert rules and notifications
- **Dashboard**: Metrics visualization dashboard (Grafana integration)

## 4. Code Diagram

### 4.1 Core Classes

```mermaid
classDiagram
    class DocumentService {
        +upload_document(file) Document
        +get_document(id) Document
        +delete_document(id) bool
        +list_documents() List~Document~
        -parse_document(file) dict
        -extract_metadata(content) dict
    }

    class EmbeddingService {
        +generate_embedding(text) List~float~
        +generate_batch_embeddings(texts) List~List~float~~
        +load_model(model_name) Model
        -normalize_vector(vector) List~float~
    }

    class VectorStoreService {
        +create_collection(name, config) bool
        +delete_collection(name) bool
        +insert_vectors(collection, vectors) bool
        +search(collection, query_vector, limit) SearchResult
        -get_client() QdrantClient
    }

    class LLMService {
        +generate_response(prompt) str
        +generate_stream(prompt) Iterator~str~
        +load_model(model_name) bool
        -build_prompt(context, query) str
    }

    class QueryProcessor {
        +process_query(query) QueryResult
        +retrieve_relevant_chunks(query) List~Chunk~
        -construct_context(chunks) str
        -format_response(answer, sources) dict
    }

    class StorageManager {
        +store_document(file, metadata) Document
        +get_document(id) Document
        +delete_document(id) bool
        +get_document_metadata(id) dict
        +cleanup_old_documents() int
        -validate_file(file) bool
        -update_lifecycle_status(id, status) void
    }

    class Document {
        +id: str
        +filename: str
        +content: str
        +metadata: dict
        +chunks: List~Chunk~
    }

    class Chunk {
        +id: str
        +document_id: str
        +content: str
        +embedding: List~float~
        +metadata: dict
    }

    class QueryResult {
        +answer: str
        +sources: List~dict~
        +confidence: float
    }

    DocumentService --> EmbeddingService : uses
    DocumentService --> Document : manages
    DocumentService --> Chunk : creates
    DocumentService --> StorageManager : stores files
    EmbeddingService --> Chunk : updates
    VectorStoreService --> Chunk : stores
    QueryProcessor --> EmbeddingService : uses
    QueryProcessor --> VectorStoreService : uses
    QueryProcessor --> LLMService : uses
    QueryProcessor --> QueryResult : returns
    Document --> Chunk : contains
    StorageManager --> Document : manages
```

### 4.2 API Route Classes

```mermaid
classDiagram
    class BaseRouter {
        +router: APIRouter
        +setup_routes() None
    }

    class DocumentRouter {
        +router: APIRouter
        +POST /documents upload_document()
        +GET /documents list_documents()
        +GET /documents/{id} get_document()
        +DELETE /documents/{id} delete_document()
    }

    class QueryRouter {
        +router: APIRouter
        +POST /query query_documents()
        +GET /query/history get_query_history()
    }

    class CollectionRouter {
        +router: APIRouter
        +POST /collections create_collection()
        +GET /collections list_collections()
        +DELETE /collections/{name} delete_collection()
    }

    class RequestModel {
        +validate() bool
    }

    class ResponseModel {
        +to_dict() dict
    }

    BaseRouter <|-- DocumentRouter
    BaseRouter <|-- QueryRouter
    BaseRouter <|-- CollectionRouter
    DocumentRouter --> RequestModel : validates
    DocumentRouter --> ResponseModel : returns
    QueryRouter --> RequestModel : validates
    QueryRouter --> ResponseModel : returns
    CollectionRouter --> RequestModel : validates
    CollectionRouter --> ResponseModel : returns
```

### 4.3 Configuration Classes

```mermaid
classDiagram
    class Config {
        +load() Config
        +get(section, key) Any
        +validate() bool
    }

    class APIConfig {
        +host: str
        +port: int
        +debug: bool
        +cors_origins: List~str~
    }

    class QdrantConfig {
        +url: str
        +api_key: str
        +timeout: int
        +collection_name: str
    }

    class OllamaConfig {
        +host: str
        +port: int
        +model: str
        +timeout: int
    }

    class EmbeddingConfig {
        +model_name: str
        +batch_size: int
        +cache_enabled: bool
        +dimension: int
    }

    class DocumentConfig {
        +max_file_size: int
        +chunk_size: int
        +chunk_overlap: int
        +supported_formats: List~str~
    }

    Config --> APIConfig : contains
    Config --> QdrantConfig : contains
    Config --> OllamaConfig : contains
    Config --> EmbeddingConfig : contains
    Config --> DocumentConfig : contains
```

### 4.4 Exception Classes

```mermaid
classDiagram
    class RAGException {
        +message: str
        +status_code: int
        +to_dict() dict
    }

    class DocumentException {
        +document_id: str
    }

    class EmbeddingException {
        +model_name: str
        +text: str
    }

    class VectorStoreException {
        +collection_name: str
        +operation: str
    }

    class LLMException {
        +model_name: str
        +prompt: str
    }

    class QueryException {
        +query: str
        +context: str
    }

    class ValidationException {
        +field: str
        +value: Any
        +constraint: str
    }

    RAGException <|-- DocumentException
    RAGException <|-- EmbeddingException
    RAGException <|-- VectorStoreException
    RAGException <|-- LLMException
    RAGException <|-- QueryException
    RAGException <|-- ValidationException
```

## Component Relationships

### Key Dependencies

1. **API Server** depends on:
   - Document Processor for document management
   - Query Processor for query handling
   - Configuration for settings

2. **Document Processor** depends on:
   - Embedding Service for vector generation
   - File Storage for document storage

3. **Query Processor** depends on:
   - Embedding Service for query embeddings
   - Vector Store Service for retrieval
   - LLM Service for response generation

4. **Embedding Service** depends on:
   - Model Registry for model management
   - Configuration for model settings

5. **Vector Store Service** depends on:
   - Qdrant client library
   - Configuration for connection settings

6. **LLM Service** depends on:
   - Ollama runtime
   - Configuration for model settings

### Data Flow Between Components

```mermaid
flowchart LR
    subgraph IngestionFlow["Document Ingestion Flow"]
        API[API Server] --> DP[Document Processor]
        DP --> ES[Embedding Service]
        ES --> VSS[Vector Store Service]
        DP --> FS[File Storage]
    end

    subgraph QueryFlow["Query Flow"]
        API --> QP[Query Processor]
        QP --> ES
        QP --> VSS
        QP --> LS[LLM Service]
    end

    style API fill:#e1f5ff
    style DP fill:#e8f5e9
    style ES fill:#e8f5e9
    style VSS fill:#e8f5e9
    style QP fill:#e8f5e9
    style LS fill:#e8f5e9
```

## Summary

The C4 model provides a comprehensive view of the RAG system architecture:

- **Context Level**: Shows external actors and their interactions with the system
- **Container Level**: Breaks down the system into major functional containers
- **Component Level**: Details the internal components of each container
- **Code Level**: Defines the key classes and their relationships

This layered approach enables understanding at different levels of abstraction, from high-level system boundaries to detailed implementation structures.

## Related Documents

- **[Basic Design](01-basic-design.md)** - System overview and components
- **[High-Level Design](03-high-level-design.md)** - Architectural patterns and deployment
- **[Data Flow](04-data-flow.md)** - Detailed data flow diagrams
- **[Sequence Diagrams](05-sequence-diagrams.md)** - Interaction sequences

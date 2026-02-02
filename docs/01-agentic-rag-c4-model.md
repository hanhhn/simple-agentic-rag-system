# C4 Model – Agentic RAG System

## Overview

This document extends the base RAG C4 model to cover the **agentic orchestration** used in this project.  
Instead of a single monolithic RAG pipeline, the system is decomposed into cooperating **agents** (specialised services and workers) that coordinate via APIs and task queues.

Agentic in this context means:

- Individual services have **clear goals** (ingest, embed, retrieve, answer, manage models)
- They run **autonomously** once triggered and make **local decisions** (caching, retries, validation)
- They communicate through **well‑defined contracts** (REST APIs, Celery tasks, vector store operations)

Related base documents:

- `rag/01-basic-design.md` – core RAG components
- `rag/02-c4-model.md` – non‑agentic C4 view
- `rag/03-high-level-design.md` – general high‑level architecture

## 1. Context Diagram – Agentic View

From a context point of view, the system is still “one RAG System”, but the **behaviour** is now expressed as agents collaborating to fulfil user intents.

```mermaid
flowchart TB
    User[User / Frontend] -->|Queries, Document actions| AgenticRAG[Agentic RAG API]

    subgraph AgenticRAG[ Agentic RAG System ]
        Orchestrator[Query Orchestrator Agent<br/>(QueryProcessor + LLMService)]
        IngestionAgent[Ingestion Agent<br/>(API + DocumentProcessor + Celery)]
        EmbeddingAgent[Embedding Agent<br/>(EmbeddingService + Celery)]
        RetrievalAgent[Retrieval Agent<br/>(VectorStore)]
        ModelAgent[Model Management Agent<br/>(LLMService / EmbeddingService)]
        MonitoringAgent[Monitoring & Logging Agent]
    end

    AgenticRAG -->|Store & search vectors| Qdrant[Qdrant Vector DB]
    AgenticRAG -->|LLM inference| Ollama[Ollama Runtime]
    AgenticRAG -->|Store documents| FileStore[File Storage]
    AgenticRAG -->|Metrics & logs| Obsv[Prometheus / Loki / Grafana]

    style AgenticRAG fill:#e1f5ff
    style User fill:#f0f0f0
    style Qdrant fill:#fff4e1
    style Ollama fill:#fff4e1
    style FileStore fill:#fff4e1
    style Obsv fill:#fff4e1
```

### External Actors

| Actor | Type | Description |
|-------|------|-------------|
| **User / Frontend** | Person / System | Uses the REST API (and React UI) to upload documents, manage collections, and issue queries |
| **Administrator** | Person | Manages deployment, models, configuration, and monitoring |
| **Qdrant** | System | Vector database storing document embeddings and metadata |
| **Ollama** | System | Local LLM runtime for generation and summarisation |
| **File Storage** | System | Local filesystem or mounted volume for raw documents |
| **Observability Stack** | System | Prometheus, Loki, Grafana for metrics and logs |

## 2. Container Diagram – Agentic Containers

The underlying containers are the same as in the base C4 model, but we now explicitly group them into **agents** with goals and responsibilities.

```mermaid
flowchart TB
    subgraph AgenticRAG["Agentic RAG System"]
        direction TB

        subgraph APIContainer["API & Orchestration"]
            APIServer[FastAPI API Server<br/>`src/api`]
            QueryOrchestrator[Query Orchestrator Agent<br/>`QueryProcessor`]
        end

        subgraph TaskQueue["Task Queue Layer"]
            RedisBroker[Redis Broker/Backend]
            CeleryWorkers[Celery Workers<br/>Documents & Embeddings]
        end

        subgraph Ingestion["Ingestion Agent"]
            DocumentProcessor[Document Processor<br/>`DocumentProcessor`]
            StorageManager[Storage Manager<br/>`StorageManager`]
        end

        subgraph Embeddings["Embedding Agent"]
            EmbeddingService[Embedding Service<br/>`EmbeddingService`]
        end

        subgraph Retrieval["Retrieval Agent"]
            VectorStoreService[Vector Store Service<br/>`VectorStore`]
        end

        subgraph LLM["Answer / Model Agent"]
            LLMService[LLM Service<br/>`LLMService` + `PromptBuilder`]
        end

        subgraph Observability["Monitoring & Logging Agent"]
            Logging[Structured Logging<br/>`src/core/logging.py`]
            Metrics[Metrics Exporters / Middleware]
        end
    end

    User[User / Frontend] -->|HTTP| APIServer

    APIServer --> QueryOrchestrator
    APIServer --> RedisBroker
    RedisBroker --> CeleryWorkers

    CeleryWorkers --> DocumentProcessor
    DocumentProcessor --> StorageManager
    CeleryWorkers --> EmbeddingService

    QueryOrchestrator --> EmbeddingService
    QueryOrchestrator --> VectorStoreService
    QueryOrchestrator --> LLMService

    StorageManager --> FileStore[(File Storage)]
    VectorStoreService --> Qdrant[(Qdrant DB)]
    LLMService --> OllamaRuntime[Ollama Runtime]

    APIServer --> Logging
    CeleryWorkers --> Logging
    Logging --> Metrics

    style APIServer fill:#e1f5ff
    style QueryOrchestrator fill:#e8f5e9
    style DocumentProcessor fill:#e8f5e9
    style EmbeddingService fill:#e8f5e9
    style VectorStoreService fill:#e8f5e9
    style LLMService fill:#e8f5e9
    style RedisBroker fill:#fff3e0
    style CeleryWorkers fill:#fff3e0
    style FileStore fill:#fff4e1
    style Qdrant fill:#fff4e1
    style OllamaRuntime fill:#fff4e1
```

### Agentic Containers and Responsibilities

| Agent / Container | Backing Code | Responsibilities |
|-------------------|-------------|------------------|
| **API & Orchestration** | `src/api`, `QueryProcessor` | Accepts user intents (upload, query), validates them, and delegates work to specialised agents |
| **Ingestion Agent** | `DocumentProcessor`, `StorageManager`, `document_tasks` | Parses, cleans, chunks, and persists documents; emits embedding jobs |
| **Embedding Agent** | `EmbeddingService`, `embedding_tasks` | Generates and caches embeddings, manages embedding model configuration, ensures collection dimensions match |
| **Retrieval Agent** | `VectorStore` | Manages collections, executes similarity searches, filters by metadata and score |
| **Answer / Model Agent** | `LLMService`, `PromptBuilder`, `OllamaClient` | Builds prompts, calls LLM, streams responses, manages model listing and switching |
| **Task Queue Layer** | `Celery`, `Redis` | Schedules and executes long‑running tasks, handles retries and backoff |
| **Monitoring & Logging Agent** | `src/core/logging.py`, Loki/Prometheus/Grafana | Structured logs, metrics, dashboards, alerting hooks |

## 3. Component Diagram – Orchestrator and Agents

### 3.1 Query Orchestrator Agent

```mermaid
flowchart TB
    subgraph QueryOrchestratorAgent["Query Orchestrator Agent (`QueryProcessor`)"]
        direction TB

        QueryAPI[Query API Route<br/>`src/api/routes/query.py`]
        Validator[QueryValidator<br/>`src/utils/validators.py`]
        Orchestrator[QueryProcessor<br/>`process_query` / `process_query_stream`]
        Retriever[VectorStore Client<br/>`VectorStore.search`]
        Embedder[Embedding Client<br/>`EmbeddingService.generate_embedding`]
        RAGLLM[LLM RAG Wrapper<br/>`LLMService.generate_rag(_stream)`]

        QueryAPI --> Validator
        QueryAPI --> Orchestrator
        Orchestrator --> Embedder
        Orchestrator --> Retriever
        Orchestrator --> RAGLLM
    end

    style QueryAPI fill:#e1f5ff
    style Orchestrator fill:#e8f5e9
```

**Responsibilities:**

- Validate search parameters and query text
- Decide when to:
  - run pure vector search (set `use_rag=False`)
  - perform full RAG (embedding → retrieval → LLM)
- Coordinate streaming vs non‑streaming responses
- Enforce score thresholds and `top_k` limits

### 3.2 Ingestion & Embedding Agents

```mermaid
flowchart TB
    subgraph IngestionAgent["Ingestion Agent (`process_document_task`)"]
        APIUpload[Document Upload Route]
        CeleryDocTask[`process_document_task`]
        DocProcessor[DocumentProcessor]
        ChunkBuilder[Chunk Builder]
        ChunkMetadata[Chunk Metadata Enricher]
    end

    subgraph EmbeddingAgent["Embedding Agent (`generate_embeddings_task`)"]
        CeleryEmbTask[`generate_embeddings_task`]
        EmbService[EmbeddingService]
        Cache[EmbeddingCache]
        VStore[VectorStore]
    end

    APIUpload --> CeleryDocTask
    CeleryDocTask --> DocProcessor
    DocProcessor --> ChunkBuilder
    ChunkBuilder --> ChunkMetadata
    ChunkMetadata --> CeleryEmbTask

    CeleryEmbTask --> EmbService
    EmbService --> Cache
    EmbService --> VStore

    style APIUpload fill:#e1f5ff
    style CeleryDocTask fill:#fff3e0
    style CeleryEmbTask fill:#fff3e0
    style DocProcessor fill:#e8f5e9
    style EmbService fill:#e8f5e9
```

These agents collaborate asynchronously:

- **Ingestion Agent**: turns raw files into structured, metadata‑rich chunks.
- **Embedding Agent**: ensures those chunks become vectors stored in Qdrant with consistent payloads.

### 3.3 Answer / Model Agent

```mermaid
flowchart TB
    subgraph AnswerAgent["Answer / Model Agent (`LLMService` + `PromptBuilder`)"]
        PromptBuilder[PromptBuilder<br/>RAG & summarisation templates]
        LLMClient[OllamaClient<br/>HTTP integration]
        RAGWrapper[LLMService.generate_rag / _stream]
        Summarizer[LLMService.summarize]
        ModelManager[Model listing & switching]
    end

    style PromptBuilder fill:#e8f5e9
    style RAGWrapper fill:#e8f5e9
    style Summarizer fill:#e8f5e9
    style ModelManager fill:#e8f5e9
```

**Responsibilities:**

- Build prompts from question + contexts using project‑specific templates
- Provide both blocking and streaming generation
- Offer generic summarisation capabilities
- Expose model discovery and switching so admins can “steer” the answering behaviour

## 4. Code Diagram – Mapping Agents to Modules

At the code level the agentic behaviour is composed from existing services and tasks.

```mermaid
classDiagram
    class QueryProcessor {
        +process_query(query, collection, top_k, score_threshold, use_rag) Dict
        +process_query_stream(query, collection, top_k, score_threshold) Dict
        +create_collection(name, dimension)
    }

    class EmbeddingService {
        +generate_embedding(text) List~float~
        +generate_embeddings(texts, batch_size) List~List~float~~
        +get_dimension() int
    }

    class VectorStore {
        +search(collection, query_vector, top_k, score_threshold) List~Dict~
        +insert_vectors(collection, vectors, payloads) None
        +create_collection(name, dimension) None
        +collection_exists(name) bool
    }

    class LLMService {
        +generate(prompt) str
        +generate_rag(question, contexts) str
        +generate_stream(prompt) List~str~
        +generate_rag_stream(question, contexts) List~str~
        +summarize(text, max_length) str
    }

    class DocumentProcessor {
        +process_document(filepath, metadata) Dict
    }

    class StorageManager {
        +save_file(...)
        +delete_file(...)
    }

    class ProcessDocumentTask {
        +process_document_task(...)
    }

    class GenerateEmbeddingsTask {
        +generate_embeddings_task(...)
    }

    QueryProcessor --> EmbeddingService : uses
    QueryProcessor --> VectorStore : uses
    QueryProcessor --> LLMService : uses
    ProcessDocumentTask --> DocumentProcessor : uses
    ProcessDocumentTask --> StorageManager : uses
    ProcessDocumentTask --> GenerateEmbeddingsTask : schedules
    GenerateEmbeddingsTask --> EmbeddingService : uses
    GenerateEmbeddingsTask --> VectorStore : uses
```

### Agent Mapping Summary

- **Query Orchestrator Agent** → `QueryProcessor` + `LLMService` + `VectorStore` + `EmbeddingService`
- **Ingestion Agent** → `DocumentProcessor` + `StorageManager` + `process_document_task`
- **Embedding Agent** → `EmbeddingService` + `generate_embeddings_task`
- **Retrieval Agent** → `VectorStore` (used by both ingestion and query flows)
- **Answer / Model Agent** → `LLMService`, `PromptBuilder`, `OllamaClient`

## 5. Relationship to Base C4 Model

- The **containers and components** are the same as the base RAG system; the **agentic view** is primarily about:
  - clearer **intent‑centric** boundaries (ingest, embed, retrieve, answer, manage)
  - explicit use of **Celery workers as autonomous agents**
  - emphasising **local decision‑making** (caching, retries, validation) as agent responsibilities.
- This document should be read **after** `rag/02-c4-model.md` to understand how the same codebase supports both a traditional RAG pipeline view and an agent‑oriented view of the system.


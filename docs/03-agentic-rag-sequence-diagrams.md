# Sequence Diagrams – Agentic RAG System

## Overview

This document provides **agent‑centric sequence diagrams** for the main flows of the agentic RAG system:

- Document ingestion and preparation
- Embedding generation and storage
- Query and RAG answer generation (non‑streaming and streaming)
- Document deletion and cleanup
- Model management

It builds on the generic sequence diagrams in `rag/05-sequence-diagrams.md`.

---

## 1. Document Ingestion – Agent View

### 1.1 Description

This sequence focuses on how the **Ingestion Agent** turns an uploaded file into structured chunks and triggers the **Embedding Agent**.

### 1.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Frontend
    participant API as API Server<br/>(Documents Route)
    participant IngestA as Ingestion Agent<br/>(Celery doc task)
    participant Store as StorageManager
    participant DocProc as DocumentProcessor
    participant EmbedA as Embedding Agent<br/>(Celery embed task)

    User->>API: POST /api/v1/documents/upload<br/>(file, collection, metadata)
    API->>API: Validate file type, size, collection
    API->>Store: save_file(file, collection)
    Store-->>API: file_path, document_id

    API->>IngestA: enqueue process_document_task<br/>(storage_path, collection, filename, metadata)
    API-->>User: 202 Accepted<br/>(task_id)

    note over IngestA: Asynchronous execution on documents queue

    IngestA->>DocProc: process_document(filepath, metadata)
    DocProc->>DocProc: detect type, extract text
    DocProc->>DocProc: clean, normalise
    DocProc->>DocProc: chunk text into segments
    DocProc-->>IngestA: chunks + enriched metadata

    IngestA->>IngestA: build chunks_data[]<br/>{text, metadata, chunk_index, document_id, filename, collection}
    IngestA->>EmbedA: enqueue generate_embeddings_task(chunks_data, collection, document_id, filename)

    IngestA-->>API: update task state (via Celery backend)
    API-->>User: task status on poll
```

### 1.3 Key Agent Behaviours

- **Ingestion Agent** owns parsing, cleaning, chunking and metadata enrichment.
- The ingestion flow is intentionally **decoupled** from embedding via a separate Celery task.

---

## 2. Embedding Generation – Agent View

### 2.1 Description

This sequence highlights the **Embedding Agent** responsibilities: validating chunks, generating embeddings, using cache, and inserting vectors into Qdrant.

### 2.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant IngestA as Ingestion Agent
    participant EmbedA as Embedding Agent<br/>(Celery embed task)
    participant EmbSvc as EmbeddingService
    participant Cache as EmbeddingCache
    participant VStore as VectorStore

    IngestA->>EmbedA: enqueue generate_embeddings_task<br/>(chunks_data, collection, document_id, filename)

    note over EmbedA: Worker picks task from embeddings queue

    EmbedA->>EmbedA: validate chunk list and text fields
    EmbedA->>EmbSvc: init EmbeddingService(model_name)
    EmbedA->>VStore: init VectorStore

    EmbedA->>EmbedA: extract chunk_texts[]

    alt caching enabled
        EmbedA->>Cache: get_batch(chunk_texts)
        Cache-->>EmbedA: cached_embeddings[]
        EmbedA->>EmbSvc: encode texts without cache hits
        EmbSvc-->>EmbedA: new_embeddings[]
        EmbedA->>Cache: set_batch(texts_to_encode, new_embeddings)
        EmbedA->>EmbedA: merge cached + new embeddings
    else no caching
        EmbedA->>EmbSvc: generate_embeddings(chunk_texts, batch_size)
        EmbSvc-->>EmbedA: embeddings[]
    end

    EmbedA->>VStore: collection_exists(collection)
    alt collection missing
        EmbedA->>EmbSvc: get_dimension()
        EmbedA->>VStore: create_collection(collection, dimension)
    end

    EmbedA->>EmbedA: build payloads[]<br/>{document_id, filename, chunk_index, chunk_text, collection, metadata...}
    EmbedA->>VStore: insert_vectors(collection, embeddings, payloads)
    VStore-->>EmbedA: success

    EmbedA-->>IngestA: embedding summary<br/>(vectors_inserted, chunk_count)
```

### 2.3 Key Agent Behaviours

- **Embedding Agent** ensures:
  - Embedding generation is efficient (batching + caching).
  - Qdrant collections are created with the correct dimension.
  - Metadata payloads are consistent and rich enough for later retrieval and attribution.

---

## 3. Agentic RAG Query – Non‑Streaming

### 3.1 Description

This sequence covers the standard **RAG path** from query to final answer, focusing on the **Query Orchestrator Agent** and **Answer Agent**.

### 3.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Frontend
    participant API as API Server<br/>(Query Route)
    participant QAgent as Query Orchestrator Agent<br/>(QueryProcessor)
    participant EmbSvc as EmbeddingService
    participant VStore as VectorStore
    participant AnswerA as Answer / Model Agent<br/>(LLMService + PromptBuilder)

    User->>API: POST /api/v1/query<br/>(query, collection, top_k, score_threshold, use_rag)
    API->>QAgent: process_query(...)

    QAgent->>QAgent: validate search params
    QAgent->>EmbSvc: generate_embedding(query)
    EmbSvc-->>QAgent: query_embedding

    QAgent->>VStore: search(collection, query_embedding, top_k, score_threshold)
    VStore-->>QAgent: search_results[]

    alt use_rag=false
        QAgent-->>API: retrieval-only result
        API-->>User: 200 OK (hits, metadata)
    else use_rag=true
        alt no search_results
            QAgent-->>API: empty context
            API-->>User: 200 OK (no results)
        else results found
            QAgent->>QAgent: build contexts[] from payload.text
            QAgent->>AnswerA: generate_rag(question, contexts)
            AnswerA->>AnswerA: build_rag_prompt(question, contexts)
            AnswerA->>AnswerA: call LLM via Ollama
            AnswerA-->>QAgent: answer
            QAgent-->>API: answer + retrieval metadata
            API-->>User: 200 OK (answer, hits, timings)
        end
    end
```

### 3.3 Key Agent Behaviours

- **Query Orchestrator Agent**:
  - Centrally decides when to perform RAG vs. retrieval‑only.
  - Logs and measures each step (validation, embedding, search, LLM).
- **Answer Agent**:
  - Encapsulates RAG prompt construction and model interaction.

---

## 4. Agentic RAG Query – Streaming

### 4.1 Description

This sequence shows how the same agents support **streaming answers**, returning answer chunks as soon as they are produced by the LLM.

### 4.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Frontend
    participant API as API Server<br/>(Streaming Query Route)
    participant QAgent as Query Orchestrator Agent
    participant EmbSvc as EmbeddingService
    participant VStore as VectorStore
    participant AnswerA as Answer Agent<br/>(LLMService)

    User->>API: POST /api/v1/query/stream<br/>(query, collection, params)
    API->>QAgent: process_query_stream(...)

    QAgent->>QAgent: validate params
    QAgent->>EmbSvc: generate_embedding(query)
    EmbSvc-->>QAgent: query_embedding

    QAgent->>VStore: search(collection, query_embedding, top_k, score_threshold)
    VStore-->>QAgent: search_results[]

    alt no search_results
        QAgent-->>API: empty answer_chunks[]
        API-->>User: 200 OK (no results)
    else results found
        QAgent->>QAgent: build contexts[] from payload.text
        QAgent->>AnswerA: generate_rag_stream(question, contexts)
        AnswerA->>AnswerA: build_rag_prompt(question, contexts)
        AnswerA->>AnswerA: generate_stream(prompt)

        loop for each token/chunk
            AnswerA-->>QAgent: chunk
            QAgent-->>API: chunk
            API-->>User: stream chunk (e.g. SSE)
        end

        AnswerA-->>QAgent: all chunks complete
        QAgent-->>API: final aggregated answer
        API-->>User: stream end / completion event
    end
```

### 4.3 Key Agent Behaviours

- Reuses the same retrieval logic but:
  - Wraps LLM calls in a **streaming** interface.
  - Allows frontends to start rendering the answer while generation continues.

---

## 5. Document Deletion – Agent View

### 5.1 Description

This sequence shows how document deletion is handled asynchronously by agents to clean up both file storage and vector store entries.

### 5.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as User / Admin
    participant API as API Server<br/>(Documents Route)
    participant DelA as Deletion Agent<br/>(delete_document_task)
    participant Store as StorageManager
    participant VecDelA as Vector Deletion Agent<br/>(delete_vectors_task)
    participant VStore as VectorStore

    User->>API: DELETE /api/v1/documents/{filename}<br/>(collection)
    API->>DelA: enqueue delete_document_task(collection, filename)
    API-->>User: 202 Accepted (task_id)

    note over DelA: Worker picks delete_document_task

    DelA->>Store: delete_file(filename, collection)
    Store-->>DelA: success or failure

    alt file deletion success
        DelA-->>API: document deleted (file only)
    else file deletion failure
        DelA->>DelA: log inconsistency
        DelA-->>API: error / retry
    end

    note over User,VecDelA: Optional follow-up to delete vectors

    User->>API: DELETE /api/v1/vectors<br/>(collection, filter_criteria)
    API->>VecDelA: enqueue delete_vectors_task(collection, filter_criteria)
    VecDelA->>VStore: delete_vectors(collection, payload_filter)
    VStore-->>VecDelA: deletion summary
    VecDelA-->>API: success
    API-->>User: 204 No Content
```

### 5.3 Key Agent Behaviours

- Separates **file deletion** from **vector deletion** to avoid tight coupling and allow different retry strategies.
- Both deletion operations are fully asynchronous, keeping the user‑facing deletion endpoint responsive.

---

## 6. Model Management – Agent View

### 6.1 Description

This sequence focuses on the **Model & LLM Agent**, illustrating how models are listed and switched.

### 6.2 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Admin / Operator
    participant API as API Server<br/>(Models Route)
    participant ModelA as Model & LLM Agent<br/>(LLMService)

    note over Admin,ModelA: List available models

    Admin->>API: GET /api/v1/models
    API->>ModelA: list_models()
    ModelA->>ModelA: ask OllamaClient for models
    ModelA-->>API: [model names]
    API-->>Admin: 200 OK (models)

    note over Admin,ModelA: Switch active model

    Admin->>API: PUT /api/v1/models/switch<br/>(new_model)
    API->>ModelA: set_model(new_model)
    ModelA->>ModelA: instantiate new OllamaClient(model=new_model)
    ModelA-->>API: success
    API-->>Admin: 200 OK
```

### 6.3 Key Agent Behaviours

- Encapsulates model management behind `LLMService`, keeping the rest of the system agnostic to specific model details.
- Allows operators to **steer** system behaviour (quality, latency, cost) without changing application code.

---

## 7. Summary

- The sequence diagrams in this document emphasise **agents** rather than just classes or services.
- Each flow (ingestion, embedding, query, deletion, model management) is handled by a **dedicated agent** or a small set of collaborating agents.
- This agentic structure makes the system:
  - Easier to reason about for operations and debugging
  - Straightforward to scale and observe
  - Ready for future extension with additional higher‑level agents (planning, evaluation, routing) built on the same foundations.


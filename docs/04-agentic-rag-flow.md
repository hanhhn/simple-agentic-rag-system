# Agentic RAG Flow

## Overview

This document describes the **end‑to‑end flow** of the agentic RAG system:

- How user intents become **agent tasks**
- How agents collaborate through APIs, queues, and shared stores
- How control and data move across the system in the most common scenarios

It complements the more diagram‑heavy documents:

- `01-agentic-rag-c4-model.md`
- `02-agentic-rag-high-level-design.md`
- `03-agentic-rag-sequence-diagrams.md`

## 1. Main Agentic Flows

At a high level there are three primary flows:

1. **Document ingestion and preparation**
2. **Embedding generation and storage**
3. **Query → retrieval → answer (RAG)**

Each flow is implemented as a **collaboration between agents** that specialise in part of the pipeline.

## 2. Flow 1 – Document Ingestion and Preparation

### 2.1 Intent

A user uploads a new document (e.g. PDF, DOCX, MD, TXT) and wants it to be available for future queries in a specific collection.

### 2.2 Agents Involved

- **Ingestion Agent**
  - `src/tasks/document_tasks.py::process_document_task`
  - `src/services/document_processor.py` (`DocumentProcessor`)
  - `src/services/storage_manager.py` (`StorageManager`)
- **Embedding Agent**
  - `src/tasks/embedding_tasks.py::generate_embeddings_task`

### 2.3 Detailed Flow

1. **Upload and initial validation**
   - The user calls `POST /api/v1/documents/upload`.
   - The API validates:
     - File type and size
     - Required metadata (e.g. collection)
   - A **document id** and **storage path** are generated.

2. **Persist raw document**
   - `StorageManager` saves the file into the collection’s directory.
   - Metadata is recorded (filename, collection, size, timestamps, optional tags).

3. **Enqueue ingestion task**
   - The API does **not** process the document synchronously.
   - A Celery task `process_document_task` is enqueued onto the `documents` queue with:
     - `storage_path`
     - `collection`
     - `filename`
     - chunking parameters (size, overlap, strategy)
     - initial metadata (e.g. `document_id`)
   - The API returns a **task id** so the client can track progress.

4. **Ingestion Agent processing**
   - A worker picks up `process_document_task`.
   - `DocumentProcessor`:
     - Detects document type
     - Extracts raw text
     - Cleans and normalises text
     - Chunks text into manageable pieces
     - Attaches metadata (chunk index, document id, filename, collection, etc.)
   - The result is a list of **chunk descriptors**: `{ text, metadata, chunk_index, document_id, filename, collection }`.

5. **Emit embedding job**
   - The Ingestion Agent prepares `chunks_data` and enqueues `generate_embeddings_task` on the `embeddings` queue.
   - The ingestion task completes and returns:
     - `chunk_count`
     - `embedding_task_id`
     - document metadata

6. **Client tracking**
   - The client polls `GET /api/v1/tasks/{task_id}` or richer task APIs to monitor ingestion and embedding progress.

### 2.4 Outcomes

- Raw document is safely stored.
- Chunks are ready and queued for embedding.
- No blocking happens on the user request path; ingestion is fully **agentic and asynchronous**.

## 3. Flow 2 – Embedding Generation and Storage

### 3.1 Intent

Chunks produced by the Ingestion Agent need to be converted into vectors and inserted into Qdrant for future retrieval.

### 3.2 Agents Involved

- **Embedding Agent**
  - `src/tasks/embedding_tasks.py::generate_embeddings_task`
  - `src/services/embedding_service.py` (`EmbeddingService`)
  - `src/services/vector_store.py` (`VectorStore`)
  - `src/embedding/cache.py` (`EmbeddingCache`)

### 3.3 Detailed Flow

1. **Embedding task start**
   - A Celery worker takes `generate_embeddings_task(chunks_data, collection, document_id, filename, ...)`.
   - Basic validation is applied:
     - `chunks_data` must be a list of dicts.
     - Each chunk must contain non‑empty `text`.

2. **Service initialisation**
   - `EmbeddingService` is instantiated (lazy model loading).
   - `VectorStore` is instantiated (Qdrant connection).

3. **Text extraction**
   - The Embedding Agent builds a list `chunk_texts = [chunk["text"] …]`.
   - If no valid text exists, the task fails early with `EmbeddingError`.

4. **Generate embeddings**
   - `EmbeddingService.generate_embeddings(chunk_texts, batch_size)` is called.
   - Internally this:
     - Looks up any available **cache hits**.
     - Uses the Granite embedding model to generate embeddings for cache misses in batches.
     - Stores new embeddings back into `EmbeddingCache`.

5. **Ensure collection exists**
   - The Embedding Agent checks `VectorStore.collection_exists(collection)`.
   - If missing:
     - It creates the collection with the embedding dimension from `EmbeddingService.get_dimension()`.

6. **Prepare payloads**
   - For each `chunk_data`, a payload dict is created that includes:
     - `document_id`
     - `filename`
     - `chunk_index`
     - `chunk_text`
     - `collection`
     - any additional metadata supplied during ingestion

7. **Insert vectors**
   - `VectorStore.insert_vectors(collection, embeddings, payloads)` is called in a single batch.
   - Qdrant stores the vectors and metadata for retrieval.

8. **Task result**
   - The task returns:
     - `chunk_count`
     - `vectors_inserted`
     - `document_id`, `filename`
   - Logs include task ID, collection, counts, and any errors.

### 3.4 Outcomes

- Each chunk has a corresponding vector in Qdrant with rich metadata.
- `EmbeddingCache` is warmed for future re‑use.
- The collection is consistent with embedding dimensions and ready for queries.

## 4. Flow 3 – Agentic RAG Query

### 4.1 Intent

A user asks a question against one or more collections and expects an answer **grounded in the ingested documents**, optionally via streaming.

### 4.2 Agents Involved

- **Query Orchestrator Agent**
  - `src/services/query_processor.py` (`QueryProcessor`)
  - `src/utils/validators.py` (`QueryValidator`)
- **Embedding Agent** (as a service client)
  - `src/services/embedding_service.py` (`EmbeddingService`)
- **Retrieval Agent**
  - `src/services/vector_store.py` (`VectorStore`)
- **Answer / Model Agent**
  - `src/services/llm_service.py` (`LLMService`)
  - `src/llm/prompt_builder.py` (`PromptBuilder`)

### 4.3 Non‑Streaming Flow (`process_query`)

1. **API receives query**
   - The user calls `POST /api/v1/query` with:
     - `query`
     - `collection_name`
     - Optional: `top_k`, `score_threshold`, `use_rag`.

2. **Validation**
   - `QueryValidator.validate_search_params` checks:
     - Query length
     - `top_k` bounds
     - `score_threshold` validity

3. **Query embedding**
   - `EmbeddingService.generate_embedding(query)` is invoked.
   - Cache is consulted (if enabled) to avoid recomputing popular queries.

4. **Vector search**
   - `VectorStore.search(collection_name, query_vector, top_k, score_threshold)` is called.
   - The result is a ranked list of documents/chunks with scores and payloads.

5. **Decision: RAG or retrieval‑only**
   - If `use_rag is False`:
     - `QueryProcessor` returns only the search results (no LLM call).
   - If `use_rag is True`:
     - And **no results** meet the threshold:
       - Returns “no results” / empty answer with retrieval metadata.
     - And **results exist**:
       - Continues to RAG generation.

6. **RAG context construction**
   - The Query Orchestrator collects the `text` from each hit’s payload.
   - It logs `context_count` and `total_context_length`.

7. **LLM generation**
   - `LLMService.generate_rag(question, contexts)` is called.
   - Internally:
     - `PromptBuilder.build_rag_prompt(question, contexts)` constructs a prompt with instructions and citations.
     - `OllamaClient.generate` runs the model.

8. **Response**
   - The final result includes:
     - `answer`
     - `retrieved_documents`
     - counts and timing metadata

### 4.4 Streaming Flow (`process_query_stream`)

The streaming flow mirrors the non‑streaming flow up to retrieval, then:

1. **Context construction** is the same.
2. **Streaming generation**:
   - `LLMService.generate_rag_stream(question, contexts)` builds the same prompt but calls:
     - `LLMService.generate_stream(prompt)` under the hood.
   - The LLM client yields chunks (tokens or partial sentences) incrementally.
3. **Aggregation and return**:
   - The orchestrator aggregates chunks into `answer` and exposes both:
     - `answer_chunks`
     - `answer` (concatenated string)
   - The API can map `answer_chunks` to Server‑Sent Events (SSE) or similar streaming protocols.

### 4.5 Outcomes

- User receives a grounded answer with detailed retrieval metadata.
- Logs record per‑phase timing, enabling iterative optimisation and monitoring.
- The same agentic structure supports both synchronous and streaming experiences.

## 5. Supporting Flows

### 5.1 Collection Management Flow

High‑level steps (details in `rag/05-sequence-diagrams.md` and `embedding_tasks`):

1. User requests creation of a collection (via API).
2. The system validates the name and configuration.
3. Vector Store creates the collection (dimension usually taken from the active embedding model).
4. Collection metadata can be exposed with stats (document count, vector count, size, etc.).

### 5.2 Document Deletion Flow

1. User calls `DELETE /api/v1/documents/{id or filename}`.
2. A Celery task `delete_document_task`:
   - Deletes the raw file via `StorageManager`.
3. Optionally another task `delete_vectors_task`:
   - Deletes vectors in Qdrant with a filter on `filename` / `document_id`.

This keeps cleanup **asynchronous** and resilient to temporary issues.

### 5.3 Model Management Flow

Through `LLMService` and `OllamaClient`:

1. Admin lists available models (`LLMService.list_models()`).
2. Admin switches the active model (`LLMService.set_model(model)`).
3. Queries automatically use the newly selected model via the same agentic flow.

## 6. Agentic Properties of the Flows

Across all flows:

- **Autonomy**:
  - Each agent can continue functioning as long as its local dependencies are healthy (e.g. Embedding Agent can process pending jobs even if queries temporarily stop).
- **Loose Coupling**:
  - Interactions are via clear contracts (HTTP, Celery, Qdrant payload schemas).
  - Failures are contained and surfaced via typed errors and status endpoints.
- **Observability**:
  - Structured logs and metrics allow each agent’s performance and reliability to be tracked.
- **Extensibility**:
  - New flows (e.g. summarisation‑only, evaluation pipelines) can plug into the same services and agents without re‑architecting the system.

These properties make the RAG system **agentic** in practice while keeping the implementation clean, maintainable, and aligned with the existing Python service architecture.


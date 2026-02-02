## C4 Architecture Model – Agentic RAG System

This document describes the system using the C4 model: **System Context**, **Containers**, **Components**, and a brief view of the code-level structure where useful.

---

## 1. System Context (C1)

**Purpose**: A user-facing Agentic RAG system that lets users upload documents, build semantic collections, and query them using intelligent agents backed by local LLMs and a vector database.

**Primary users**
- **Knowledge Worker / End User**
  - Uploads documents.
  - Creates and manages collections.
  - Asks questions and receives agentic RAG answers.
- **Operator / DevOps**
  - Deploys and monitors the stack (API, workers, Qdrant, Redis, Ollama, monitoring).

**External systems**
- **Qdrant** – Vector database for embeddings and similarity search.
- **Ollama** – Local LLM runtime for:
  - Agent reasoning (ReAct).
  - RAG generation (answering with retrieved context).
- **Redis** – Message broker and result backend for Celery.
- **Prometheus / Grafana / Loki** – Metrics, dashboards, and log aggregation.

**System boundaries**
- **Frontend Web App** (`frontend/`): SPA UI for interacting with the RAG system.
- **Backend API Service** (`src/api/`): FastAPI application exposing REST endpoints.
- **Async Worker Service** (`src/tasks/`): Celery workers for document ingestion and embedding.

---

## 2. Container Diagram (C2)

**Containers inside the system**

- **Web Browser**
  - Runs the SPA built from `frontend/` (Vite + React + TypeScript).
  - Communicates with the backend via HTTPS/HTTP JSON APIs.

- **Frontend Web App (SPA)**
  - Pages:
    - `AgentPage.tsx` – Agentic RAG interface (agent queries, planning, tools, memory).
    - `QueryPage.tsx` – Traditional RAG querying.
    - `DocumentsPage.tsx`, `CollectionsPage.tsx`, `TasksPage.tsx`, `AnalyticsPage.tsx` – Management and monitoring.
  - Uses:
    - `lib/api.ts` to call backend REST endpoints.
    - UI components in `components/` and `components/ui/`.

- **Backend API (FastAPI)**
  - Entrypoint: `src/api/main.py`.
  - Exposes:
    - RAG endpoints: `src/api/routes/query.py`.
    - Agent endpoints: `src/api/routes/agents.py`.
    - Document & collection endpoints: `src/api/routes/documents.py`, `collections.py`.
    - Health and analytics endpoints: `health.py`, `tasks.py`, etc.
  - Depends on:
    - **Services** (`src/services/`):
      - `QueryProcessor` for standard RAG.
      - `AgentService` for agentic RAG.
      - `EmbeddingService`, `VectorStore`, `LLMService`, `DocumentProcessor`, `StorageManager`, `AnalyticsService`.
    - **Core** (`src/core/`): `config.py`, `logging.py`, `metrics.py`, `exceptions.py`, `security.py`.
    - **Agents** (`src/agents/`): `ReActAgent`, `QueryPlanner`, `Reflector`, `ConversationMemory`, tools.
    - **Embedding / LLM** layers:
      - `src/embedding/` – Granite embedding model, cache, model loader.
      - `src/llm/` – Base LLM client, Ollama client, prompt builder, streaming handler.

- **Async Worker (Celery)**
  - Configuration: `src/tasks/celery_app.py`.
  - Task modules: `document_tasks.py`, `embedding_tasks.py`.
  - Consumes from Redis queues, performs:
    - Document parsing and chunking.
    - Embedding generation via `EmbeddingService`.
    - Vector insertion via `VectorStore`.

- **Qdrant (Vector DB)**
  - Stores:
    - Embedding vectors for document chunks.
    - Payloads containing text, metadata, and collection information.
  - Accessed via `src/services/vector_store.py`.

- **Ollama (LLM Runtime)**
  - Provides LLM endpoints for:
    - `LLMService` (RAG answers).
    - `ReActAgent` reasoning and reflection.

- **Redis**
  - Celery broker and result backend.
  - Supports background processing for ingestion and embedding.

---

## 3. Component Diagram (C3) – Backend Focus

### 3.1 API Layer (`src/api/`)

- **`main.py`**
  - Initializes FastAPI app, includes routers, middleware, metrics endpoints.

- **Routers (`src/api/routes/`)**
  - `agents.py` – Agentic RAG:
    - `POST /agents/query` → `AgentService.query()`.
    - `POST /agents/plan` → `AgentService.plan_query()`.
    - `GET /agents/tools` → tool registry in `AgentService`.
    - `DELETE /agents/memory` → clear conversation memory.
  - `query.py` – Traditional RAG:
    - Uses `QueryProcessor` to embed, search, and answer.
  - `documents.py`, `collections.py` – Ingestion and collection management.
  - `tasks.py` – Task status and progress.
  - `health.py`, `models.py`, `conversations.py` – Health, model info, conversations.

- **Middleware (`src/api/middleware/`)**
  - `logging.py` – Request/response logging.
  - `rate_limit.py` – Basic rate limiting (protects API).

### 3.2 Services Layer (`src/services/`)

- **`AgentService`**
  - Wires **tools**, **memory**, and **ReActAgent** to the API.
  - Provides high-level methods:
    - `create_react_agent()`
    - `query()` – full agentic query execution.
    - `plan_query()` – planning without execution.
  - Uses:
    - `LLMService` for agent reasoning.
    - `VectorStore` + `EmbeddingService` via `RetrievalTool`.
    - `SummaryTool`, `CalculatorTool`, optional `WebSearchTool`.

- **`QueryProcessor`**
  - Implements the traditional RAG pipeline:
    - Validate input.
    - Generate embedding via `EmbeddingService`.
    - Search Qdrant via `VectorStore.search()`.
    - Build context and call `LLMService.generate_rag()`.
  - Responsible for metrics around each phase (validation/embedding/search/llm/total).

- **Other services**
  - `DocumentProcessor` – Parses and chunks documents via `parsers` + `text_chunker`.
  - `EmbeddingService` – Manages Granite embedding model and cache.
  - `VectorStore` – Qdrant abstraction (create collections, insert/search/delete vectors).
  - `LLMService` – Wraps Ollama for:
    - Generic `generate`.
    - RAG-specific `generate_rag` and streaming.
  - `StorageManager` – Handles file system I/O for uploaded documents.
  - `AnalyticsService` – Aggregates metrics and analytics across queries/tasks.

### 3.3 Agents Layer (`src/agents/`)

- **`BaseAgent`** – Common scaffolding for agents.
- **`ReActAgent`**
  - ReAct loop:
    - Build ReAct prompt.
    - LLM → Thought + Action.
    - Execute tool via `use_tool`.
    - Append Observation to prompt.
    - Repeat until `Action: Answer(...)`.
  - Integrates with:
    - `Tool` and `ToolResult` classes.
    - `Reflector` for answer evaluation and refinement.
    - `ConversationMemory` for multi-turn context.

- **`QueryPlanner`**
  - Classifies query type (simple/recursive/multi-part/comparison/aggregation/calculation/reasoning).
  - Produces a plan with sub-queries and tool steps.

- **`Reflector`**
  - Reflects on final answers using the LLM.
  - Can refine and improve answers based on retrieved documents and context.

- **`ConversationManager` / `memory.py`**
  - Encapsulates conversation state, sessions, metadata, and statistics.
  - Stores messages for use in prompts and analytics.

- **Tools (`tool.py`)**
  - `RetrievalTool` – Wraps `EmbeddingService` + `VectorStore.search`.
  - `CalculatorTool` – Safe mathematical evaluation.
  - `SummaryTool` – Short summaries via LLM.
  - `WebSearchTool` – Optional external search integration.

### 3.4 Embedding / LLM / Parsers / Utils

- **Embedding (`src/embedding/`)**
  - `GraniteEmbeddingModel` – Model wrapper.
  - `EmbeddingCache` – Disk-backed embedding cache.
  - `model_loader.py` / `model_manager.py` – Loading and management.

- **LLM (`src/llm/`)**
  - `base.py` – Base LLM interface.
  - `ollama_client.py` – HTTP client for Ollama.
  - `prompt_builder.py` – Shared prompt templates (chat vs RAG).
  - `templates/` – Text prompt templates for chat and RAG.
  - `stream_handler.py` – Streaming responses.

- **Parsers (`src/parsers/`)**
  - `pdf_parser.py`, `docx_parser.py`, `md_parser.py`, `txt_parser.py`.

- **Utils (`src/utils/`)**
  - `text_chunker.py`, `text_cleaner.py`, `validators.py`, `helpers.py`.

---

## 4. Code-Level Pointers (C4 – Partial)

Instead of a full class diagram, this section highlights the main entry points in code:

- **Agentic RAG Request Path**
  - `AgentPage.tsx` → `lib/api.ts` → `POST /api/v1/agents/query`
  - `src/api/routes/agents.py` → `AgentService.query()`
  - `AgentService.create_react_agent()` → `ReActAgent.run()`
  - Tools in `src/agents/tool.py` → `EmbeddingService`, `VectorStore`, `LLMService`.

- **Traditional RAG Request Path**
  - `QueryPage.tsx` → `lib/api.ts` → `POST /api/v1/query`
  - `src/api/routes/query.py` → `QueryProcessor.process_query()`
  - `EmbeddingService.generate_embedding()` → `VectorStore.search()` → `LLMService.generate_rag()`.

---

## 5. Summary

- The **Agentic RAG System** is composed of a **frontend SPA**, a **FastAPI backend**, and **Celery workers**, integrated with **Qdrant**, **Ollama**, and **Redis**.
- The **C4 view** clarifies how user requests flow from the browser through the frontend, into the API, then into services, agents, tools, and external infrastructure.
- The **Agentic RAG layer** builds on top of the traditional RAG pipeline by adding reasoning, planning, tools, reflection, and memory.


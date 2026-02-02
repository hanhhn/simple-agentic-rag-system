## High-Level Design – Agentic RAG System

This document explains the main architectural decisions, flows, and responsibilities at a **high level**, tying together the backend, agents, RAG pipeline, and frontend.

---

## 1. Architectural Goals

- **Extensible RAG platform**
  - Support both *traditional* RAG and *agentic* RAG from the same system.
- **Local-first AI**
  - Use **Ollama** for LLMs and **Qdrant** for vector search so the system can run locally.
- **Scalability and observability**
  - Async processing via **Celery + Redis**.
  - Metrics and logs via **Prometheus / Grafana / Loki**.
- **Separation of concerns**
  - Clear layering:
    - API layer.
    - Services / business logic.
    - Agents.
    - Embedding / LLM / vector store.
    - Infrastructure (config, logging, metrics, security).

---

## 2. Layered Architecture

### 2.1 Presentation Layer – Frontend SPA

- **Technologies**
  - React + TypeScript + Vite + Tailwind.
  - Located in `frontend/`.

- **Key pages**
  - `AgentPage.tsx` – Main entry for agentic RAG:
    - Inputs: query text, collection, temperature, agent type, reflection flag.
    - Shows: agent intermediate steps, tool usage, reflection info, final answer.
  - `QueryPage.tsx` – Traditional RAG:
    - Queries collections and shows retrieved documents and answers.
  - `DocumentsPage.tsx`, `CollectionsPage.tsx`, `TasksPage.tsx`, `AnalyticsPage.tsx`:
    - Document lifecycle, collection management, background tasks, analytics.

- **Responsibilities**
  - Provide a UX to:
    - Upload and manage documents.
    - Manage collections and tasks.
    - Run both RAG and agentic queries.
  - Call backend APIs via `lib/api.ts`.

### 2.2 API Layer – FastAPI

- **Entrypoint**
  - `src/api/main.py` – App creation, route registration, middleware, monitoring.

- **Routes**
  - **Agentic RAG API** – `src/api/routes/agents.py`
    - `POST /api/v1/agents/query` – Execute an agentic query using `AgentService`.
    - `POST /api/v1/agents/plan` – Plan a query (no execution).
    - `GET /api/v1/agents/tools` – List tools.
    - `DELETE /api/v1/agents/memory` – Clear conversation memory.
  - **Traditional RAG API** – `src/api/routes/query.py`
    - Query endpoints using `QueryProcessor`.
  - **Document & Collection APIs**
    - `documents.py`, `collections.py`: upload, list, delete, create collections.
  - **Tasks & Health**
    - `tasks.py`, `health.py`, `models.py`, `conversations.py`: task status, health checks, model info, conversations.

- **Cross-cutting concerns**
  - Validation and error handling via `src/core/exceptions.py`.
  - Request logging via `src/api/middleware/logging.py`.
  - Rate limiting via `src/api/middleware/rate_limit.py`.
  - Configuration via `src/core/config.py`.
  - Metrics via `src/core/metrics.py`.

### 2.3 Services Layer

- **`AgentService`**
  - Purpose:
    - Provide a high-level API for *agentic* operations.
  - Responsibilities:
    - Initialize and manage tools (`RetrievalTool`, `CalculatorTool`, `SummaryTool`, optional `WebSearchTool`).
    - Manage `ConversationMemory` (if enabled).
    - Create `ReActAgent` instances for each query.
    - Provide:
      - `query()` → agentic query execution.
      - `plan_query()` → planning only.
      - `get_available_tools()`, `clear_memory()`, `add_tool()`.

- **`QueryProcessor`**
  - Purpose:
    - Implement the classic RAG flow.
  - Responsibilities:
    - Validate query parameters.
    - Use `EmbeddingService` to embed the query.
    - Use `VectorStore` to search Qdrant.
    - Build context and call `LLMService.generate_rag()`.
    - Return answer + retrieved documents + metrics.

- **Other service classes**
  - `DocumentProcessor` – Parses documents, cleans text, chunks into segments.
  - `EmbeddingService` – Manages Granite model and embedding cache.
  - `VectorStore` – Qdrant abstraction (create collections, insert/search/delete).
  - `LLMService` – Common interface to Ollama LLMs (plain and RAG prompts).
  - `StorageManager` – Physical storage for uploads and artifacts.
  - `AnalyticsService` – Aggregates metrics (success rates, latencies, tool usage).

### 2.4 Agent Layer

- **Design goals**
  - Make agents:
    - **Composable** – Built from tools and services.
    - **Observable** – Emit intermediate steps, tools used, and timings.
    - **Configurable** – Control temperature, max iterations, memory, reflection.

- **Core elements**
  - `BaseAgent` – Common base class.
  - `ReActAgent` – Implements the ReAct loop:
    - Builds prompts describing available tools.
    - On each iteration:
      - LLM produces `Thought` and `Action`.
      - Agent executes the tool.
      - Agent appends an `Observation`.
    - Stops when it produces `Action: Answer(...)`.
  - `QueryPlanner` – Plans multi-step queries.
  - `Reflector` – Evaluates and can refine answers.
  - `ConversationMemory` / `ConversationManager` – Stores messages and metadata.
  - `Tool` and concrete implementations – Retrieval, calculator, summary, web search.

### 2.5 Embedding, Vector, and LLM Layers

- **Embedding**
  - Embedding model and cache in `src/embedding/`.
  - `EmbeddingService`:
    - Lazy loads Granite model.
    - Handles caching for performance.
    - Supports batch embedding and similarity.

- **Vector Store**
  - `VectorStore` abstracts Qdrant:
    - `create_collection`, `insert_vectors`, `search`, `delete_vectors`, `get_collection_info`, `list_collections`.
  - Responsible for:
    - Isolating Qdrant-specific details.
    - Validating collections and vector dimensions.
    - Handling Qdrant errors and mapping them to domain errors.

- **LLM**
  - `LLMService` uses `ollama_client` and `prompt_builder`:
    - Generic generations for agent thoughts/actions.
    - RAG generations combining query + context.
    - Streaming via `stream_handler`.

### 2.6 Async Processing Layer

- **Celery**
  - Configured in `src/tasks/celery_app.py`.
  - Uses Redis as broker and result backend.

- **Tasks**
  - `document_tasks.py`
    - Long-running operations:
      - Parse documents, chunk text, generate embeddings, insert into Qdrant.
  - `embedding_tasks.py`
    - Embedding-heavy operations that benefit from offloading.

- **Patterns**
  - API endpoints return a **task ID**.
  - Client polls `GET /api/v1/tasks/{task_id}` for status.

---

## 3. Data and Control Flows (High Level)

### 3.1 Document Ingestion Flow

1. User uploads a document via the frontend.
2. Frontend calls `POST /api/v1/documents`.
3. API validates request and stores file using `StorageManager`.
4. API enqueues a Celery task (e.g., `process_document`) with metadata.
5. Celery worker:
   - Parses the document using parser classes.
   - Cleans and chunks the text.
   - Generates embeddings via `EmbeddingService`.
   - Inserts vectors into Qdrant via `VectorStore`.
6. Task status is tracked and can be queried via `tasks` API.

### 3.2 Traditional RAG Query Flow

1. User submits a question via **Query page**.
2. Frontend calls `POST /api/v1/query`.
3. API passes request to `QueryProcessor.process_query()`:
   - Validate inputs.
   - Generate embedding for the query.
   - Search Qdrant for top-k similar documents.
   - Build context from document payloads.
   - Call `LLMService.generate_rag(query, contexts)`.
4. API returns:
   - Final answer.
   - Retrieved documents and scores.
   - RAG metadata and timings.

### 3.3 Agentic RAG Flow (Overview)

1. User submits a complex query via **Agent page** (e.g., “Compare Q1 and Q2 revenue and compute growth”).
2. Frontend calls `POST /api/v1/agents/query` with:
   - `query`, `collection`, `agent_type="react"`, `temperature`, `enable_reflection`.
3. API instantiates `AgentService` and calls `AgentService.query()`.
4. `AgentService` builds a `ReActAgent` and runs it:
   - Multiple `Thought → Action → Observation` loops.
   - Uses tools (retrieval, calculator, summary, etc.).
5. `ReActAgent` optionally calls `Reflector` to evaluate and refine the final answer.
6. API returns:
   - `answer`, `actions`, `intermediate_steps`, `confidence`, `metadata` (iterations, tools used, execution time).
7. Frontend renders both the **reasoning trace** and the final answer.

---

## 4. Cross-Cutting Concerns

- **Configuration**
  - Centralized in `src/core/config.py`.
  - `.env` and `env.example` provide environment variables for:
    - Qdrant / Ollama / Redis URLs.
    - Model names and embedding parameters.
    - Security (JWT, etc.).

- **Logging**
  - `src/core/logging.py` sets up structured logging.
  - API and services use `get_logger(__name__)` for contextual logs.
  - Loki integration via `src/core/loki_handler.py`.

- **Metrics and Monitoring**
  - `src/core/metrics.py` defines Prometheus metrics:
    - RAG query latencies, vector search latencies, tool usage, agent metrics.
  - Exposed at `/metrics` and visualized by Prometheus + Grafana dashboards.

- **Security**
  - `src/core/security.py` handles security utilities (e.g., JWT).
  - API-level authentication can be layered via middleware/routers (if configured).

---

## 5. Design Trade-offs and Rationale

- **Local-first vs cloud APIs**
  - Using **Ollama** and **Qdrant** keeps data local and private.
  - This favors control and privacy over turnkey managed services.

- **Agentic RAG built on top of traditional RAG**
  - Traditional RAG (`QueryProcessor`) remains simple and fast.
  - Agentic RAG (`AgentService` + `ReActAgent`) composes the same primitives into more powerful reasoning flows.

- **Services vs direct library calls**
  - Explicit `EmbeddingService`, `VectorStore`, and `LLMService` decouple:
    - Business logic from external libraries.
    - Agent logic from infrastructure details.
  - This makes the system easier to test, extend, and monitor.

- **Celery for async ingestion**
  - Document processing and embedding can be CPU- and IO-heavy.
  - Moving them to background workers keeps the API responsive and scalable.

---

## 6. Summary

- The system is **layered** with clear separation of concerns: frontend, API, services, agents, embeddings/LLM/vector, and infra.
- **Traditional RAG** and **agentic RAG** share core primitives (embeddings, vector search, LLM) but differ in orchestration.
- The design favors **extensibility**, **observability**, and **local privacy** while remaining approachable for experimentation and further enhancement.


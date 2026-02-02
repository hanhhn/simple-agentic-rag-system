## Sequence Diagrams – Agentic RAG System

This document captures the main interaction sequences between the frontend, backend, services, agents, and external systems.

---

## 1. Document Ingestion Sequence

**Scenario**: A user uploads a document to be indexed into a collection.

```text
User
  ↓
Frontend (DocumentsPage.tsx)
  ↓  HTTP: POST /api/v1/documents
Backend API (documents router)
  ↓
StorageManager.save_file()
  ↓
Celery: enqueue process_document task
  ↓
Celery Worker (document_tasks.py)
  ↓
DocumentProcessor.parse_and_chunk()
  ↓
EmbeddingService.generate_embeddings()
  ↓
VectorStore.insert_vectors() → Qdrant
  ↓
Update task status in Redis
  ↓
User polls GET /api/v1/tasks/{task_id} for completion
```

**Key steps**
- Synchronous API:
  - Validate request, store file, enqueue background task, return `task_id`.
- Asynchronous worker:
  - Parse → clean → chunk → embed → insert into Qdrant.

---

## 2. Traditional RAG Query Sequence

**Scenario**: User asks a question via the Query page and gets a RAG-based answer.

```text
User
  ↓
Frontend (QueryPage.tsx)
  ↓  HTTP: POST /api/v1/query
Backend API (query router)
  ↓
QueryProcessor.process_query()
  ↓
EmbeddingService.generate_embedding(query)
  ↓
VectorStore.search(collection, query_embedding)
  ↓
LLMService.generate_rag(query, contexts from retrieved docs)
  ↓
Backend builds response (answer + retrieved docs + metadata)
  ↓  HTTP Response
Frontend displays answer and supporting documents
```

**Key behaviors**
- Synchronous, single-pass RAG pipeline (no tools or multi-step reasoning).
- Metrics recorded for:
  - Validation, embedding, search, LLM, and total latency.

---

## 3. Agentic RAG Query (ReAct) Sequence

**Scenario**: User asks a complex question via the Agent page; the ReAct agent uses tools in multiple steps.

### 3.1 High-Level Sequence

```text
User
  ↓
Frontend (AgentPage.tsx)
  ↓  HTTP: POST /api/v1/agents/query
Backend API (agents.router.agent_query)
  ↓
AgentService.query()
  ↓
AgentService.create_react_agent()
  ↓
ReActAgent.run(query, collection, ...)
  ↓
[ReAct Loop: Thought → Action → Observation]*
  ↓
ReActAgent (optional) → Reflector.reflect_and_refine()
  ↓
AgentService builds response (answer + actions + intermediate_steps + metadata)
  ↓  HTTP Response
Frontend shows reasoning trace and final answer
```

### 3.2 ReAct Loop Detail

One iteration of the ReAct loop:

```text
ReActAgent
  ↓
Build initial/updated ReAct prompt
  ↓
LLMService.generate(prompt) via Ollama
  ↓
Parse LLM response → Thought + Action(tool_name, args)
  ↓
IF Action is "Answer":
    finalize answer (and optionally reflect)
    EXIT loop
ELSE:
    use_tool(tool_name, **args)
    ↓
    Tool (e.g., RetrievalTool, CalculatorTool, SummaryTool)
      ↓
      - RetrievalTool:
          EmbeddingService.generate_embedding()
          VectorStore.search()
      - CalculatorTool:
          Safe expression evaluation
      - SummaryTool:
          LLMService.generate(summary_prompt)
    ↓
    ToolResult → Observation string
    ↓
    Append Thought + Action + Observation to prompt
    ↓
    Next iteration of ReAct loop
```

**Notes**
- The loop stops when:
  - The LLM issues `Action: Answer(...)`, or
  - The agent hits `max_iterations`.
- All actions and intermediate observations are recorded in `AgentResponse`.

---

## 4. Agent Reflection Sequence

**Scenario**: After the ReAct loop finds an answer, the system evaluates and optionally refines it via a Reflector.

```text
ReActAgent
  ↓
Final answer from ReAct loop
  ↓  (if enable_reflection=True)
Collect retrieved_docs from previous tool actions
  ↓
Reflector.reflect(query, answer, context, retrieved_docs)
  ↓
LLMService.generate(reflection_prompt) via Ollama
  ↓
ReflectionResult (overall_score, should_refine, feedback)
  ↓
IF should_refine:
    Reflector.reflect_and_refine(...)
      ↓
      LLMService.generate(refinement_prompt) via Ollama
      ↓
      Refined answer + final reflection
  ELSE:
    Use original answer
  ↓
Update AgentResponse.answer, confidence, metadata["reflection"], metadata["refinement"]
```

**Key points**
- Reflection is **optional** and controlled via the `enable_reflection` flag.
- Reflection can:
  - Provide a quality/confidence score.
  - Improve correctness and clarity of the final answer.

---

## 5. Conversation Management Sequence

**Scenario**: Multi-turn conversation where agent reuses context and metadata.

```text
User sends first message
  ↓
Frontend → POST /api/v1/agents/query (conversation_id optional)
  ↓
AgentService (use_memory=True)
  ↓
ConversationMemory / ConversationManager:
    - Create or load conversation
    - Append user message
  ↓
ReActAgent.run() uses memory to build prompt with history
  ↓
ReActAgent produces answer and actions
  ↓
ConversationMemory:
    - Append assistant message
    - Update stats and metadata (tokens, confidence, tool usage, etc.)
  ↓
Response returned to frontend

User sends follow-up message
  ↓
Frontend → POST /api/v1/agents/query (with same conversation reference, if used)
  ↓
Same conversation loaded
  ↓
History-aware ReActAgent.run()
```

**Behavior**
- Memory allows:
  - Follow-up questions that depend on previous answers.
  - Better context for planning and reflection.

---

## 6. Monitoring & Analytics Sequence

**Scenario**: Operator or user wants to understand performance and usage.

```text
Backend services and agents
  ↓
Emit metrics via src/core/metrics.py
  ↓
Prometheus scrapes /metrics endpoint
  ↓
Grafana visualizes dashboards (RAG latencies, agent steps, tool usage, etc.)
  ↓
Loki collects logs from API and workers
  ↓
Grafana dashboards and log panels show:
    - Query volumes and latencies
    - Agent iteration counts and tool usage
    - Error rates and failure details
```

---

## 7. Summary

- Sequence diagrams highlight how **frontend**, **API**, **services**, **agents**, and **external systems** interact in practice.
- The **agentic RAG sequences** extend traditional RAG with **multi-step ReAct loops**, **tool usage**, **reflection**, and **conversation memory**, all while reusing the same embedding/vector/LLM infrastructure.


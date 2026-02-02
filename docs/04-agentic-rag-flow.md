## Agentic RAG Flow – Detailed Design

This document explains the end-to-end **Agentic RAG flow**, from an incoming request through agents, tools, RAG, reflection, and back to the user.

---

## 1. Overview

Agentic RAG extends traditional RAG by giving the system:

- **Reasoning** – decide what information is needed and in what order.
- **Tools** – retrieval, calculation, summarization, optional web search.
- **Memory** – track conversation history and prior steps.
- **Reflection** – self-assess and refine answers.

The implementation is centered around:

- `AgentService` – orchestrator for agentic operations.
- `ReActAgent` – core reasoning and acting loop.
- Tools from `src/agents/tool.py`.
- Reflection via `Reflector`.
- Conversation memory via `ConversationMemory` and `ConversationManager`.

---

## 2. End-to-End Request Flow

### 2.1 From Frontend to Agent Service

1. User interacts with the **Agent page** (`AgentPage.tsx`) and submits:
   - `query` (string).
   - `collection` (string).
   - `agent_type` (e.g., `"react"`).
   - `temperature` (float).
   - `enable_reflection` (bool).
2. Frontend calls:
   - `POST /api/v1/agents/query` (see `src/api/routes/agents.py`).
3. API endpoint:
   - Validates inputs (non-empty query and collection; allowed agent types).
   - Instantiates `AgentService` with:
     - `LLMService`, `VectorStore`, `EmbeddingService`.
     - `use_memory=True`, `verbose=True`.
   - Calls:
     - `await agent_service.query(query, collection, agent_type, enable_reflection=...)`.

### 2.2 AgentService Initialization

When `AgentService` is created:

- It stores references to:
  - `llm_service`, `vector_store`, `embedding_service`.
- It sets high-level parameters:
  - `use_memory` – controls whether a `ConversationMemory` is used.
  - `max_iterations` – maximum ReAct steps.
  - `verbose` – logging detail.
- It initializes the default tools:
  - `RetrievalTool(self.vector_store, self.embedding_service)`.
  - `CalculatorTool()`.
  - `SummaryTool(self.llm_service)`.
  - Optionally `WebSearchTool`.
- It creates `ConversationMemory` if memory is enabled.

When `query()` is called:

- It selects an agent type (currently `"react"`).
- It uses `create_react_agent()` to instantiate a `ReActAgent` with:
  - Tools.
  - LLM service.
  - Memory object.
  - Max iterations, verbosity, temperature.
  - Reflection settings (`enable_reflection`, optional custom `Reflector`).

---

## 3. ReActAgent – Internal Flow

### 3.1 Input and Context

`ReActAgent.run()` receives:

- `query` – the user question or task.
- `collection` – used by retrieval tools.
- `context` – optional extra context data.
- `**kwargs` – additional parameters.

It then:

- Builds an `execution_context` dict with:
  - `query`, `collection`, `context`, extra kwargs.
- Initializes an empty `AgentResponse` object:
  - `answer`, `actions`, `intermediate_steps`, `metadata`, `execution_time`, `confidence`.
- Builds the **initial ReAct prompt** including:
  - Instructions for Thought/Action/Observation.
  - A description of available tools and their parameters.
  - The user question and the directive to “Think step by step.”

### 3.2 ReAct Loop

The ReAct loop iterates up to `max_iterations`:

1. **LLM Generation**
   - Call `llm_service.generate(prompt, temperature=...)`.
   - The LLM produces a text block containing:
     - A `Thought: ...`.
     - An `Action: tool_name(args)` or an `Action: Answer(answer="...")`.

2. **Parsing Thought and Action**
   - `_parse_react_response()` uses regex to extract:
     - `thought` – text after `Thought:` and before `Action:`.
     - `action` – dictionary containing:
       - `tool` – tool name.
       - `args` – parsed parameters (JSON or key/value pairs).

3. **Check for Final Answer**
   - If `action` is `None` or `tool == "Answer"`:
     - Extract `final_answer` from `action.args["answer"]` or from the raw LLM response.
     - Proceed to **reflection phase** (if enabled).
     - Exit the loop.

4. **Execute Tool**
   - Extract `tool_name` and `tool_args`.
   - For retrieval actions:
     - If `collection` is not in `tool_args` and `tool_name == "retrieve_documents"`, inject the collection.
   - Call `await self.use_tool(tool_name, **tool_args)`, which:
     - Finds the tool by name from the agent’s tool list.
     - Executes its `execute` method.
     - Returns a `ToolResult`.

5. **Record Action and Observation**
   - Wrap the tool usage in an `AgentAction`:
     - `tool_name`, `tool_input`, `tool_output`, `thought`, `step`.
   - Append `AgentAction` to `response.actions` and `previous_actions`.
   - Convert `ToolResult` to a string `observation` via `tool_result.to_string()`.

6. **Update Prompt and Intermediate Steps**
   - Call `_update_react_prompt()` with:
     - Previous `prompt`, `thought`, `action`, `observation`, `iteration`.
   - Append:
     - `"Thought i: {thought}"`
     - `"Observation i: {observation[:200]}"`
     to `response.intermediate_steps`.
   - Loop continues with the updated prompt.

7. **Error Handling and Early Stop**
   - If `tool_result.success` is `False`, a warning is logged but the loop may continue with a revised plan in the next iteration.
   - If `max_iterations` is reached without a final answer, the agent exits with whatever information it has (implementation-specific; typically the last known state).

### 3.3 Finalization and Memory

After the loop:

- Compute `response.execution_time`.
- Populate `response.metadata` with:
  - `iterations`, `tools_used`, `collection`, `query_length`.
- Update memory via `update_memory(query, response)`:
  - Store user query and agent answer (and potentially actions) for future context.
- Return `AgentResponse`.

---

## 4. Tools and RAG Integration

### 4.1 RetrievalTool

**Purpose**: Expose the existing RAG retrieval capabilities as a tool to the agent.

**Flow**:

1. Given `query` and `collection` (and optional `top_k`, `score_threshold`):
2. `EmbeddingService.generate_embedding(query)`:
   - Embeds the query string with the Granite model.
3. `VectorStore.search(collection, query_embedding, top_k, score_threshold)`:
   - Queries Qdrant for similar vector points.
4. Pack results into a `ToolResult`:
   - Contains documents and scores (from Qdrant payloads and points).
5. Return as `ToolResult`, which becomes part of the observation text.

### 4.2 CalculatorTool

**Purpose**: Perform safe mathematical operations for numeric reasoning.

**Flow**:

1. Receives an expression string (e.g., `"1250000 + 890000 + 450000"`).
2. Parses and evaluates safely (disallowing arbitrary code execution).
3. Returns a `ToolResult` with:
   - `data.result` – numeric result.
   - `data.expression` – normalized expression.

### 4.3 SummaryTool

**Purpose**: Summarize long pieces of text, such as retrieved documents.

**Flow**:

1. Receives `text` (and optional `max_length`).
2. Calls `llm_service.generate()` or a dedicated summary method with a summary prompt.
3. Returns a shorter summary as `ToolResult`.

### 4.4 WebSearchTool (Optional)

**Purpose**: Extend the agent’s knowledge beyond the local corpus if integrated.

**Flow**:

1. Receives `query` and `num_results`.
2. Uses an external web search API.
3. Returns search results as `ToolResult`.

---

## 5. Reflection and Refinement Flow

If `enable_reflection=True` when calling `AgentService.query()`:

1. Once the ReAct loop proposes a `final_answer`:
   - `ReActAgent` gathers `retrieved_docs` from all previous `AgentAction`s:
     - It collects `tool_output.data["documents"]` for retrieval steps.
2. It calls:
   - `await reflector.reflect(query, answer, context, retrieved_docs)`.
3. The `Reflector`:
   - Builds a reflection prompt summarizing:
     - The question, the proposed answer, and relevant documents.
   - Uses `llm_service` to get a `ReflectionResult`:
     - `overall_score`.
     - `should_refine`.
     - Additional feedback.
4. If `should_refine` is `True`:
   - Call `reflector.reflect_and_refine(...)`, which:
     - Uses the feedback plus the original answer and documents.
     - Calls the LLM to produce a **refined** answer.
   - Update:
     - `response.answer` with refined answer.
     - `response.confidence` with final reflection score.
     - `response.metadata["refinement"]` with details.
5. If `should_refine` is `False`:
   - Keep `final_answer` as-is.
   - Use `reflection_result.overall_score` as confidence.

---

## 6. Conversation Memory and Analytics

### 6.1 Memory

- `ConversationMemory` and `ConversationManager` track:
  - Messages: user and assistant turns.
  - Metadata: tags, collection, priority, user, session.
  - Statistics: token counts, execution times, tool usage, success rates, reflection counts.
- The agent:
  - Can incorporate previous messages into prompts.
  - Supports multi-turn, context-aware answers.

### 6.2 Analytics

- Metrics (from `src/core/metrics.py`) capture:
  - `agent_query_total`.
  - `agent_execution_steps`.
  - `agent_execution_time_seconds`.
  - `agent_tool_usage_total`.
  - `agent_iterations_total`.
- These are exposed via `/metrics` and visualized using Prometheus + Grafana dashboards configured in `docker/`.

---

## 7. Failure Modes and Handling

- **Validation errors**
  - Input validation errors (empty query/collection, invalid agent type) are surfaced as `400 Bad Request` with structured error payloads.

- **Agent errors**
  - Unexpected exceptions during agent execution are caught in `AgentService.query()` and `agents.py` router.
  - Return structured error responses with `success=False` and an informative message.

- **Tool errors**
  - Individual tool failures are captured in `ToolResult`:
    - `success=False`, `error` populated.
  - ReAct loop can:
    - Log warnings.
    - Try alternate tools or strategies in subsequent iterations.

- **External system errors**
  - Vector/embedding/LLM issues raise domain-specific exceptions:
    - `VectorStoreError`, `EmbeddingError`, `ServiceError`, etc.
  - Logs and metrics reflect these failures for easier diagnosis.

---

## 8. Summary

- The **Agentic RAG flow** sits on top of the existing RAG building blocks:
  - `EmbeddingService`, `VectorStore`, `LLMService`.
- `AgentService` and `ReActAgent`:
  - Turn these primitives into a **multi-step, tool-using, reflective** agent.
- Reflection, memory, and rich metrics:
  - Enable **higher answer quality**, **traceability**, and **operations visibility** for complex real-world queries.


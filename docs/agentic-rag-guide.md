# Agentic RAG System Guide

## Overview

The Agentic RAG System extends traditional RAG with intelligent agents that can reason, plan, and use tools to answer complex queries. Instead of simple retrieval-and-generation, agents can:

- **Reason** about what information is needed
- **Plan** multi-step execution strategies
- **Use tools** to gather and process information
- **Reflect** on results and adjust approach
- **Remember** conversation history for context

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Agentic RAG System                      │
├─────────────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐      ┌────────────────────┐       │
│  │   Agent API   │─────▶│  Agent Service   │       │
│  └──────────────┘      └────────┬───────┘┘       │
│                                │                    │
│                                ▼                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │              ReAct Agent                      │  │
│  │  ┌──────────────┐  ┌────────────────┐    │  │
│  │  │   Planner   │  │    Memory     │    │  │
│  │  └──────────────┘  └────────────────┘    │  │
│  │         │                  │               │  │
│  │         ▼                  ▼               │  │
│  │  ┌──────────────────────────────┐          │  │
│  │  │         Tool Registry       │          │  │
│  │  │  - Retrieval Tool         │          │  │
│  │  │  - Calculator Tool        │          │  │
│  │  │  - Summary Tool          │          │  │
│  │  │  - Web Search Tool        │          │  │
│  │  └──────────────────────────────┘          │  │
│  └──────────────────────────────────────────────────┘  │
│                                │                    │
│                                ▼                    │
│  ┌────────────────────────────────────────┐         │
│  │       Traditional RAG Components      │         │
│  │  - Vector Store (Qdrant)          │         │
│  │  - Embedding Service             │         │
│  │  - LLM Service (Ollama)         │         │
│  └────────────────────────────────────────┘         │
│                                                      │
└─────────────────────────────────────────────────────────────┘
```

### Agent Types

#### 1. ReAct Agent (Reasoning + Acting)

The ReAct agent follows a think-act-observe loop:

```
User Query
    ↓
Agent thinks about what to do
    ↓
Agent selects a tool and executes it
    ↓
Agent observes the result
    ↓
Does agent have enough information?
    ├─ No → Repeat think-act-observe
    └─ Yes → Generate final answer
```

**Example Workflow:**

```python
# Query: "What is the total revenue mentioned in the Q1 report?"

Thought 1: I need to find the Q1 report first
Action 1: retrieve_documents(query="Q1 report", collection="financials")
Observation 1: Found document "Q1 2024 Financial Report.pdf"

Thought 2: Now I need to search for revenue in this document
Action 2: retrieve_documents(query="revenue", collection="financials")
Observation 2: Found multiple revenue figures

Thought 3: I need to sum the revenue figures
Action 3: calculator(expression="1250000 + 890000 + 450000")
Observation 3: Result: 2590000

Final Answer: The total revenue mentioned in the Q1 report is $2,590,000.
```

### Tools

Tools are callable functions that agents can use. Each tool has:

- **Name**: Unique identifier
- **Description**: What the tool does (for LLM understanding)
- **Parameters**: Required and optional arguments
- **Category**: Type of tool (retrieval, calculation, etc.)

#### Available Tools

1. **retrieve_documents**
   - Category: Retrieval
   - Purpose: Search knowledge base for relevant documents
   - Parameters:
     - `query` (required): Search query text
     - `collection` (required): Collection name
     - `top_k` (optional): Number of results (default: 5)
     - `score_threshold` (optional): Minimum similarity score (default: 0.0)

2. **calculator**
   - Category: Calculation
   - Purpose: Perform mathematical operations
   - Parameters:
     - `expression` (required): Mathematical expression (e.g., "2 + 2", "10 * 5")
   - Supports: +, -, *, /, **, %, and functions like abs(), min(), max()

3. **summarize**
   - Category: Generation
   - Purpose: Summarize long text
   - Parameters:
     - `text` (required): Text to summarize
     - `max_length` (optional): Max length in words (default: 200)

4. **web_search** (Optional)
   - Category: Search
   - Purpose: Search the web for information
   - Parameters:
     - `query` (required): Search query
     - `num_results` (optional): Number of results (default: 5)
   - Note: Requires integration with search API

## Memory System

### Conversation Memory

Stores full conversation history for multi-turn dialogues:

```python
# Agent remembers context across queries
User: "What is RAG?"
Agent: "RAG stands for Retrieval-Augmented Generation..."

User: "How does it work?"  # Agent knows context
Agent: "Based on RAG, it works by first retrieving relevant..."
```

### Vector Memory

Stores embeddings of past queries for semantic retrieval:

```python
# Agent can find similar past queries
New Query: "I need to implement a search system"
→ Retrieves: "How to add search functionality?" (from memory)
```

## Query Planning

Complex queries are decomposed into sub-queries:

### Query Types

1. **Simple**: Direct question, can be answered in one step
2. **Recursive**: Requires sequential steps
3. **Multi-part**: Has multiple sub-questions
4. **Comparison**: Compares multiple items
5. **Aggregation**: Combines information from multiple sources
6. **Calculation**: Requires mathematical operations
7. **Reasoning**: Requires logical reasoning

### Planning Example

```python
Query: "Compare the revenue of Q1 and Q2, and calculate the growth"

Plan:
┌─────────────────────────────────────────────────┐
│ Query Type: COMPARISON + CALCULATION        │
├─────────────────────────────────────────────────┤
│ Step 1: Retrieve Q1 revenue                │
│   Tool: retrieve_documents                  │
│   Query: "Q1 revenue"                     │
├─────────────────────────────────────────────────┤
│ Step 2: Retrieve Q2 revenue                │
│   Tool: retrieve_documents                  │
│   Query: "Q2 revenue"                     │
├─────────────────────────────────────────────────┤
│ Step 3: Calculate growth                   │
│   Tool: calculator                        │
│   Expression: "(Q2 - Q1) / Q1 * 100"    │
└─────────────────────────────────────────────────┘
```

## API Usage

### Execute Agentic Query

```bash
curl -X POST "http://localhost:8000/api/v1/agents/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the total revenue mentioned in the Q1 report?",
    "collection": "financials",
    "agent_type": "react",
    "temperature": 0.7
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "query": "What is the total revenue mentioned in the Q1 report?",
    "answer": "The total revenue mentioned in the Q1 report is $2,590,000.",
    "actions": [
      {
        "tool": "retrieve_documents",
        "input": {"query": "Q1 report", "collection": "financials", "top_k": 5},
        "output": {
          "success": true,
          "data": {
            "documents": [...],
            "count": 3
          }
        },
        "thought": "I need to find the Q1 report first",
        "step": 1
      },
      {
        "tool": "calculator",
        "input": {"expression": "1250000 + 890000 + 450000"},
        "output": {
          "success": true,
          "data": {"result": 2590000, "expression": "..."}
        },
        "thought": "Now I need to calculate the total revenue",
        "step": 2
      }
    ],
    "intermediate_steps": [
      "Thought 1: I need to find the Q1 report first",
      "Observation 1: Found document 'Q1 2024 Financial Report.pdf'",
      "Thought 2: Now I need to search for revenue in this document",
      "Observation 2: Found multiple revenue figures",
      "Thought 3: I need to sum the revenue figures",
      "Observation 3: Result: 2590000"
    ],
    "confidence": 0.8,
    "metadata": {
      "agent_type": "react",
      "iterations": 3,
      "tools_used": ["retrieve_documents", "calculator"],
      "execution_time": 2.5432
    }
  }
}
```

### Plan a Query

```bash
curl -X POST "http://localhost:8000/api/v1/agents/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare the revenue of Q1 and Q2, and calculate the growth",
    "collection": "financials"
  }'
```

### List Available Tools

```bash
curl -X GET "http://localhost:8000/api/v1/agents/tools"
```

### Clear Agent Memory

```bash
curl -X DELETE "http://localhost:8000/api/v1/agents/memory"
```

## Custom Tools

You can create custom tools by extending the `Tool` base class:

```python
from src.agents.tool import Tool, ToolResult, ToolCategory

class WeatherTool(Tool):
    """Custom tool for weather information."""
    
    def __init__(self, weather_api_key: str):
        super().__init__(
            name="get_weather",
            description="Get current weather for a city",
            category=ToolCategory.SEARCH,
            parameters={
                "city": {
                    "type": "string",
                    "description": "City name",
                    "required": True
                }
            }
        )
        self.api_key = weather_api_key
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute weather lookup."""
        city = kwargs["city"]
        
        # Call weather API
        weather_data = await self._fetch_weather(city)
        
        return ToolResult(
            success=True,
            data=weather_data,
            metadata={"city": city}
        )
    
    async def _fetch_weather(self, city: str) -> Dict:
        # Implementation here
        pass
```

**Adding custom tool to agent:**

```python
from src.services.agent_service import AgentService

service = AgentService(llm_service, vector_store, embedding_service)
service.add_tool(WeatherTool(api_key="your-api-key"))
```

## Advanced Features

### Streaming Responses

The agent can stream intermediate steps:

```python
agent = ReActAgent(tools, llm_service)

async for step_type, content in agent.stream_run(query, collection):
    if step_type == "thought":
        print(f"🤔 {content}")
    elif step_type == "action":
        print(f"🔧 {content}")
    elif step_type == "observation":
        print(f"👁️  {content}")
    elif step_type == "answer":
        print(f"✅ {content}")
```

### Configuration

Agent behavior can be configured:

```python
agent_service = AgentService(
    llm_service=llm_service,
    vector_store=vector_store,
    embedding_service=embedding_service,
    use_memory=True,      # Enable conversation memory
    max_iterations=10,     # Max reasoning steps
    verbose=True          # Detailed logging
)

agent = agent_service.create_react_agent(
    temperature=0.7,       # LLM temperature (0.0-1.0)
)
```

## Monitoring

Agent metrics are tracked in Prometheus:

- `agent_query_total`: Total agent queries
- `agent_execution_steps`: Distribution of steps taken
- `agent_execution_time_seconds`: Execution time distribution
- `agent_tool_usage_total`: Tool invocation counts
- `agent_iterations_total`: Total reasoning iterations

View metrics at: `http://localhost:8000/metrics`

## Best Practices

### 1. Design Clear Questions

❌ Bad: "tell me about the report"
✅ Good: "What is the total revenue in the Q1 2024 financial report?"

### 2. Use Appropriate Collections

```
- Use specific collection names: "financials", "technical_docs", "hr_policies"
- Organize documents logically
```

### 3. Monitor Tool Usage

```bash
# Check which tools are used most
curl http://localhost:8000/metrics | grep agent_tool_usage
```

### 4. Adjust Temperature

- **0.0-0.3**: Factual, precise answers
- **0.4-0.7**: Balanced (default)
- **0.8-1.0**: Creative, exploratory

### 5. Handle Complex Queries

For very complex tasks:
1. Break into smaller questions
2. Use planning endpoint to understand approach
3. Review intermediate steps
4. Iterate if needed

## Troubleshooting

### Agent Fails to Answer

**Problem**: Agent can't find information

**Solution**:
- Check collection has relevant documents
- Verify document embeddings are generated
- Adjust `top_k` parameter
- Lower `score_threshold`

### Too Many Tool Calls

**Problem**: Agent keeps using tools without answering

**Solution**:
- Reduce `max_iterations`
- Increase `temperature` for more decisive answers
- Review intermediate steps in response

### Memory Issues

**Problem**: Agent doesn't remember context

**Solution**:
- Ensure `use_memory=True` in AgentService
- Check conversation is active
- Verify memory not cleared between calls

## Examples

### Example 1: Simple Query

```
Query: "What is RAG?"
→ Single retrieval step
→ Direct answer from documents
```

### Example 2: Calculation

```
Query: "What is the average revenue across Q1, Q2, and Q3?"
→ Retrieve Q1 revenue
→ Retrieve Q2 revenue
→ Retrieve Q3 revenue
→ Calculate average: (Q1 + Q2 + Q3) / 3
→ Answer with result
```

### Example 3: Multi-step Reasoning

```
Query: "Which product had the highest growth rate, and by how much?"
→ Retrieve Q1 sales for all products
→ Retrieve Q2 sales for all products
→ Calculate growth for each product
→ Find maximum growth
→ Identify product and growth amount
→ Comprehensive answer
```

### Example 4: Summary

```
Query: "Summarize the key findings in the annual report"
→ Retrieve full report
→ Summarize key points
→ Provide structured summary
```

## Future Enhancements

Planned features for future releases:

- [ ] Reflection mechanism for answer quality
- [ ] Multi-agent collaboration
- [ ] Advanced tool orchestration
- [ ] Human-in-the-loop for verification
- [ ] Tool chaining and composition
- [ ] Knowledge graph integration
- [ ] Multi-modal support (images, tables)

## Contributing

To contribute new tools or agent types:

1. Implement the base class (Tool, BaseAgent)
2. Add comprehensive documentation
3. Include unit tests
4. Update API routes
5. Add metrics

## Support

For issues or questions:
- Open an issue on GitHub
- Check API docs at `/docs`
- Review logs for errors
- Monitor metrics at `/metrics`

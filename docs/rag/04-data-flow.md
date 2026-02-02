# Data Flow - RAG System

## Overview

This document provides detailed data flow diagrams showing how data moves through the RAG system during key operations. Each flowchart illustrates the step-by-step process of document ingestion, embedding generation, vector storage, query processing, and response generation.

## 1. Document Ingestion Flow

### Flow Description

The document ingestion flow handles the process of uploading and processing documents into the system. This includes file validation, text extraction, chunking, and preparing documents for embedding generation.

### Flowchart

```mermaid
flowchart TD
    Start([Start Document Ingestion]) --> Upload[Receive Document Upload]
    Upload --> Validate{Validate Document}
    
    Validate -->|Invalid| ReturnError1[Return Validation Error]
    ReturnError1 --> End1([End])
    
    Validate -->|Valid| ExtractText[Extract Text Content]
    ExtractText --> FormatCheck{Document Format}
    
    FormatCheck -->|PDF| ParsePDF[Parse PDF Content]
    FormatCheck -->|DOCX| ParseDocx[Parse DOCX Content]
    FormatCheck -->|TXT/MD| ParseText[Read Text Content]
    FormatCheck -->|HTML| ParseHTML[Parse HTML Content]
    
    ParsePDF --> CleanText
    ParseDocx --> CleanText
    ParseText --> CleanText
    ParseHTML --> CleanText
    
    CleanText[Clean and Normalize Text]
    CleanText --> ChunkDocument[Split Document into Chunks]
    
    ChunkDocument --> AddMetadata[Add Metadata to Chunks]
    AddMetadata --> QueueForEmbedding[Queue Chunks for Embedding]
    QueueForEmbedding --> StoreDocument[Store Original Document]
    
    StoreDocument --> ReturnSuccess[Return Success with Document ID]
    ReturnSuccess --> End2([End])
    
    style Start fill:#4CAF50,color:#fff
    style End1 fill:#F44336,color:#fff
    style End2 fill:#4CAF50,color:#fff
    style Validate fill:#FFC107,color:#000
    style FormatCheck fill:#FFC107,color:#000
```

### Data Transformation

**Input:**
- Document file (binary data)
- File metadata (name, size, type)

**Transformations:**
1. Binary → Text extraction
2. Text → Normalized text (whitespace, encoding)
3. Normalized text → Chunks (500-1000 tokens)
4. Chunks → Chunks with metadata

**Output:**
- Stored document record
- Queue of text chunks for embedding
- Document ID for tracking

---

## 2. Embedding Generation Flow

### Flow Description

The embedding generation flow converts text chunks into vector embeddings using the embedding service. This process includes batch processing, caching, and error handling.

### Flowchart

```mermaid
flowchart TD
    Start([Start Embedding Generation]) --> GetQueue[Get Chunk Queue]
    GetQueue --> HasChunks{Chunks Available?}
    
    HasChunks -->|No| Wait[Wait for New Chunks]
    Wait --> GetQueue
    
    HasChunks -->|Yes| CheckCache[Check Embedding Cache]
    CheckCache --> CacheHit{Cache Hit?}
    
    CacheHit -->|Yes| UseCached[Use Cached Embeddings]
    UseCached --> UpdateStatus1[Update Chunk Status]
    UpdateStatus1 --> ProcessNext1{More Chunks?}
    ProcessNext1 -->|Yes| GetQueue
    ProcessNext1 -->|No| End1([End])
    
    CacheHit -->|No| LoadModel[Load Embedding Model]
    LoadModel --> BatchChunks[Group Chunks into Batch]
    
    BatchChunks --> GenerateEmbeddings[Generate Embeddings]
    GenerateEmbeddings --> ValidateVectors{Vectors Valid?}
    
    ValidateVectors -->|No| RetryOrFail[Retry or Mark as Failed]
    RetryOrFail --> ProcessNext2{More Chunks?}
    ProcessNext2 -->|Yes| GetQueue
    ProcessNext2 -->|No| End2([End])
    
    ValidateVectors -->|Yes| StoreInCache[Store in Cache]
    StoreInCache --> PrepareVectorStore[Prepare for Vector Store]
    PrepareVectorStore --> UpdateStatus2[Update Chunk Status]
    UpdateStatus2 --> ProcessNext3{More Chunks?}
    ProcessNext3 -->|Yes| GetQueue
    ProcessNext3 -->|No| End3([End])
    
    style Start fill:#2196F3,color:#fff
    style End1 fill:#4CAF50,color:#fff
    style End2 fill:#F44336,color:#fff
    style End3 fill:#4CAF50,color:#fff
    style CacheHit fill:#FFC107,color:#000
    style ValidateVectors fill:#FFC107,color:#000
    style ProcessNext1 fill:#FFC107,color:#000
    style ProcessNext2 fill:#FFC107,color:#000
    style ProcessNext3 fill:#FFC107,color:#000
```

### Data Transformation

**Input:**
- Text chunks with metadata
- Chunk identifiers

**Transformations:**
1. Text → Embedding vector (384 or 768 dimensions)
2. Batch chunks → Batch vectors
3. Vectors → Normalized vectors (if required)

**Output:**
- Vector embeddings for each chunk
- Cache entries (if not already present)
- Updated chunk processing status

---

## 3. Vector Storage Flow

### Flow Description

The vector storage flow manages storing and indexing embeddings in Qdrant. This includes collection management, vector insertion, and indexing optimization.

### Flowchart

```mermaid
flowchart TD
    Start([Start Vector Storage]) --> ReceiveVectors[Receive Vectors from Embedding Service]
    ReceiveVectors --> CheckCollection{Collection Exists?}
    
    CheckCollection -->|No| CreateCollection[Create New Collection]
    CreateCollection --> ConfigureIndex[Configure Index and Parameters]
    ConfigureIndex --> PreparePayloads
    
    CheckCollection -->|Yes| PreparePayloads[Prepare Payloads with Metadata]
    
    PreparePayloads --> BuildBatch[Build Batch Insert Request]
    BuildBatch --> ValidateBatch{Batch Size OK?}
    
    ValidateBatch -->|No| SplitBatch[Split into Smaller Batches]
    SplitBatch --> BuildBatch
    
    ValidateBatch -->|Yes| InsertVectors[Insert Vectors to Qdrant]
    InsertVectors --> CheckResult{Insertion Successful?}
    
    CheckResult -->|No| LogError[Log Error and Retry]
    LogError --> RetryCount{Retry Count < Max?}
    RetryCount -->|Yes| InsertVectors
    RetryCount -->|No| MarkFailed[Mark Vectors as Failed]
    MarkFailed --> End1([End])
    
    CheckResult -->|Yes| UpdateIndex[Update Index Statistics]
    UpdateIndex --> UpdateMetadata[Update Document Metadata]
    UpdateMetadata --> NotifySuccess[Notify Success to Service]
    NotifySuccess --> End2([End])
    
    style Start fill:#9C27B0,color:#fff
    style End1 fill:#F44336,color:#fff
    style End2 fill:#4CAF50,color:#fff
    style CheckCollection fill:#FFC107,color:#000
    style ValidateBatch fill:#FFC107,color:#000
    style CheckResult fill:#FFC107,color:#000
    style RetryCount fill:#FFC107,color:#000
```

### Data Transformation

**Input:**
- Vector embeddings
- Chunk metadata
- Document ID

**Transformations:**
1. Vectors + metadata → Qdrant point structure
2. Multiple points → Batch insert request
3. Batch → Stored vectors with indexes

**Output:**
- Stored vector points in Qdrant
- Updated collection statistics
- Confirmation of successful storage

---

## 4. Query Processing Flow

### Flow Description

The query processing flow handles user queries by generating embeddings, performing similarity search, retrieving relevant documents, and preparing context for the LLM.

### Flowchart

```mermaid
flowchart TD
    Start([Start Query Processing]) --> ReceiveQuery[Receive User Query]
    ReceiveQuery --> ValidateQuery{Query Valid?}
    
    ValidateQuery -->|No| ReturnError1[Return Validation Error]
    ReturnError1 --> End1([End])
    
    ValidateQuery -->|Yes| SelectCollection{Select Collection}
    SelectCollection --> CollectionEmpty{Collection Empty?}
    
    CollectionEmpty -->|Yes| ReturnError2[Return No Documents Error]
    ReturnError2 --> End2([End])
    
    CollectionEmpty -->|No| GenerateQueryEmbedding[Generate Query Embedding]
    GenerateQueryEmbedding --> ConfigureSearch[Configure Search Parameters]
    
    ConfigureSearch --> PerformSearch[Perform Similarity Search in Qdrant]
    PerformSearch --> CheckResults{Results Found?}
    
    CheckResults -->|No| ReturnEmpty[Return No Relevant Results]
    ReturnEmpty --> End3([End])
    
    CheckResults -->|Yes| FilterResults[Filter by Score Threshold]
    FilterResults --> RankResults[Rank Results by Relevance]
    
    RankResults --> TopK{Select Top K Results}
    TopK --> RetrieveChunks[Retrieve Full Chunks]
    
    RetrieveChunks --> BuildContext[Build Context String]
    BuildContext --> PreparePrompt[Prepare Prompt with Context]
    PreparePrompt --> End4([Send to LLM Service])
    
    style Start fill:#FF5722,color:#fff
    style End1 fill:#F44336,color:#fff
    style End2 fill:#F44336,color:#fff
    style End3 fill:#FFC107,color:#000
    style End4 fill:#4CAF50,color:#fff
    style ValidateQuery fill:#FFC107,color:#000
    style SelectCollection fill:#FFC107,color:#000
    style CollectionEmpty fill:#FFC107,color:#000
    style CheckResults fill:#FFC107,color:#000
    style TopK fill:#FFC107,color:#000
```

### Data Transformation

**Input:**
- User query (text string)
- Collection ID (optional)

**Transformations:**
1. Query → Query embedding
2. Query embedding → Similarity search results
3. Search results → Filtered and ranked results
4. Top-K results → Context string
5. Context + query → Prompt for LLM

**Output:**
- Relevant document chunks
- Context string
- Prepared prompt for LLM

---

## 5. Response Generation Flow

### Flow Description

The response generation flow uses the LLM to generate context-aware answers based on the retrieved documents. This includes prompt construction, model inference, and response formatting.

### Flowchart

```mermaid
flowchart TD
    Start([Start Response Generation]) --> ReceivePrompt[Receive Prompt with Context]
    ReceivePrompt --> CheckModel{LLM Model Loaded?}
    
    CheckModel -->|No| LoadModel[Load LLM Model via Ollama]
    LoadModel --> PrepareParameters
    
    CheckModel -->|Yes| PrepareParameters[Prepare Generation Parameters]
    
    PrepareParameters --> ConstructFullPrompt[Construct Full System Prompt]
    ConstructFullPrompt --> ValidatePrompt{Prompt Valid?}
    
    ValidatePrompt -->|No| ReturnError1[Return Prompt Error]
    ReturnError1 --> End1([End])
    
    ValidatePrompt -->|Yes| CallLLM[Call Ollama API]
    CallLLM --> MonitorGeneration{Stream Response?}
    
    MonitorGeneration -->|Yes| ProcessStream[Process Streaming Tokens]
    ProcessStream --> AccumulateTokens[Accumulate Tokens]
    AccumulateTokens --> GenerationComplete{Generation Complete?}
    GenerationComplete -->|No| MonitorGeneration
    GenerationComplete -->|Yes| FinalizeResponse
    
    MonitorGeneration -->|No| WaitComplete[Wait for Complete Response]
    WaitComplete --> FinalizeResponse[Finalize Response]
    
    FinalizeResponse --> ValidateResponse{Response Valid?}
    
    ValidateResponse -->|No| RetryGeneration{Retry Count < Max?}
    RetryGeneration -->|Yes| CallLLM
    RetryGeneration -->|No| ReturnError2[Return Generation Error]
    ReturnError2 --> End2([End])
    
    ValidateResponse -->|Yes| FormatResponse[Format Response with Citations]
    FormatResponse --> AddMetadata[Add Response Metadata]
    AddMetadata --> CacheResponse[Cache Response if Needed]
    CacheResponse --> ReturnSuccess[Return Success Response]
    ReturnSuccess --> End3([End])
    
    style Start fill:#009688,color:#fff
    style End1 fill:#F44336,color:#fff
    style End2 fill:#F44336,color:#fff
    style End3 fill:#4CAF50,color:#fff
    style CheckModel fill:#FFC107,color:#000
    style ValidatePrompt fill:#FFC107,color:#000
    style MonitorGeneration fill:#FFC107,color:#000
    style GenerationComplete fill:#FFC107,color:#000
    style ValidateResponse fill:#FFC107,color:#000
    style RetryGeneration fill:#FFC107,color:#000
```

### Data Transformation

**Input:**
- Prompt with context
- Query
- Generation parameters (temperature, max_tokens, etc.)

**Transformations:**
1. Prompt + parameters → LLM inference request
2. LLM response → Raw text
3. Raw text → Formatted response
4. Formatted response → Response with metadata and citations

**Output:**
- Generated answer
- Source citations
- Response metadata (model used, tokens generated, etc.)

---

## 6. End-to-End RAG Flow

### Flow Description

This flowchart shows the complete RAG pipeline from user query to final response, integrating all the individual flows.

### Flowchart

```mermaid
flowchart TD
    User([User Submits Query]) --> API[API Layer Receives Request]
    API --> Validate[Validate Request]
    Validate -->|Invalid| Error1[Return Error]
    
    Validate -->|Valid| QueryProcessor[Query Processor]
    QueryProcessor --> EmbedQuery[Generate Query Embedding]
    
    EmbedQuery --> VectorSearch[Vector Store Search]
    VectorSearch --> RetrieveDocs[Retrieve Relevant Documents]
    
    RetrieveDocs --> BuildContext[Build Context from Documents]
    BuildContext --> LLMService[LLM Service]
    
    LLMService --> GenerateResponse[Generate Response]
    GenerateResponse --> FormatResponse[Format Response with Citations]
    
    FormatResponse --> APIResponse[API Returns Response]
    APIResponse --> UserSuccess([User Receives Answer])
    
    Error1 --> UserError([User Receives Error])
    
    style User fill:#E91E63,color:#fff
    style UserSuccess fill:#4CAF50,color:#fff
    style UserError fill:#F44336,color:#fff
    style API fill:#2196F3,color:#fff
    style APIResponse fill:#2196F3,color:#fff
    style QueryProcessor fill:#FF9800,color:#000
    style VectorSearch fill:#9C27B0,color:#fff
    style LLMService fill:#009688,color:#fff
```

### Key Data Transitions

1. **User Query** → Text string
2. **Query** → Embedding vector (384/768 dim)
3. **Embedding** → Similarity search results (score + document IDs)
4. **Results** → Document chunks (text + metadata)
5. **Chunks** → Context string
6. **Context + Query** → Prompt
7. **Prompt** → LLM response
8. **Response** → Formatted answer with citations

---

## 7. Error Handling Flow

### Flow Description

This flowchart shows how errors are handled throughout the system, including retry logic, fallback mechanisms, and error reporting.

### Flowchart

```mermaid
flowchart TD
    Start([Error Detected]) --> IdentifyError[Identify Error Type]
    IdentifyError --> Categorize{Error Category}
    
    Categorize -->|Transient| RetryOperation[Retry Operation]
    RetryOperation --> IncrementRetry[Increment Retry Counter]
    IncrementRetry --> CheckRetryCount{Retry Count < Max?}
    
    CheckRetryCount -->|Yes| ApplyBackoff[Apply Exponential Backoff]
    ApplyBackoff --> RetryOp[Retry Operation]
    RetryOp --> Success{Operation Success?}
    
    Success -->|Yes| LogSuccess[Log Recovery]
    LogSuccess --> EndSuccess([Continue Normal Flow])
    
    Success -->|No| CheckRetryCount
    
    CheckRetryCount -->|No| LogMaxRetries[Log Max Retries Reached]
    
    Categorize -->|Validation| ValidationError[Return Validation Error]
    ValidationError --> LogValidation[Log Validation Error]
    LogValidation --> NotifyUser[Notify User with Details]
    
    Categorize -->|System| SystemError[Return System Error]
    SystemError --> LogSystem[Log System Error]
    LogSystem --> NotifyAdmin[Notify Administrators]
    
    Categorize -->|Resource| ResourceError[Resource Unavailable]
    ResourceError --> CheckFallback{Fallback Available?}
    
    CheckFallback -->|Yes| UseFallback[Use Fallback Service]
    UseFallback --> CheckRetryCount
    
    CheckFallback -->|No| DegradeGracefully[Degrade Gracefully]
    
    LogMaxRetries --> NotifyUser
    NotifyAdmin --> EndError([Terminate Operation])
    DegradeGracefully --> EndError
    NotifyUser --> EndError
    
    style Start fill:#F44336,color:#fff
    style EndSuccess fill:#4CAF50,color:#fff
    style EndError fill:#F44336,color:#fff
    style Categorize fill:#FFC107,color:#000
    style CheckRetryCount fill:#FFC107,color:#000
    style Success fill:#FFC107,color:#000
    style CheckFallback fill:#FFC107,color:#000
```

### Error Categories

1. **Transient Errors:** Network timeouts, temporary service unavailability
   - Strategy: Retry with exponential backoff
   
2. **Validation Errors:** Invalid input, malformed requests
   - Strategy: Return immediate error to user
   
3. **System Errors:** Service crashes, out of memory
   - Strategy: Log and notify administrators
   
4. **Resource Errors:** Database connection issues, model loading failures
   - Strategy: Use fallback or graceful degradation

---

## Data Flow Summary

### Primary Data Streams

| Flow | Input | Processing | Output |
|------|-------|------------|--------|
| Document Ingestion | File (binary) | Extract → Clean → Chunk → Add Metadata | Text chunks + Document ID |
| Embedding Generation | Text chunks | Cache check → Model inference → Batch process | Vector embeddings |
| Vector Storage | Vectors + Metadata | Prepare → Batch insert → Index | Stored vectors in Qdrant |
| Query Processing | Query text | Embed → Search → Filter → Rank | Relevant document chunks |
| Response Generation | Context + Query | Construct prompt → LLM inference → Format | Formatted answer + citations |

### Key Data Structures

**Document Chunk:**
```python
{
  "id": str,
  "text": str,
  "metadata": {
    "document_id": str,
    "page_number": int,
    "chunk_index": int,
    "source": str
  }
}
```

**Vector Point:**
```python
{
  "id": str,
  "vector": List[float],  # 384 or 768 dimensions
  "payload": {
    "text": str,
    "document_id": str,
    "metadata": dict
  }
}
```

**Search Result:**
```python
{
  "id": str,
  "score": float,
  "payload": {
    "text": str,
    "document_id": str,
    "metadata": dict
  }
}
```

**Response:**
```python
{
  "answer": str,
  "citations": List[dict],
  "sources": List[str],
  "metadata": {
    "model": str,
    "tokens_used": int,
    "retrieved_docs": int
  }
}
```

## Related Documents

- **[Basic Design](01-basic-design.md)** - System components and architecture
- **[C4 Model](02-c4-model.md)** - System architecture diagrams
- **[High-Level Design](03-high-level-design.md)** - Design patterns and deployment
- **[Sequence Diagrams](05-sequence-diagrams.md)** - Component interaction sequences
- **[Genomics/Bioinformatics Use Case](06-genomics-bioinformatics-use-case.md)** - Application to genomics and biomedical research

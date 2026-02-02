# Simple RAG System

A Retrieval-Augmented Generation (RAG) system that combines large language models with vector-based information retrieval. The system enables users to upload documents, process them into embeddings, and ask natural language questions that are answered based on the document content.

## Features

- 📄 **Document Ingestion**: Support for PDF, TXT, MD, and DOCX files
- 🔍 **Vector Search**: High-performance similarity search using Qdrant
- 🤖 **Local LLM**: Privacy-focused responses using local LLM models via Ollama
- 🚀 **REST API**: Clean and well-documented API endpoints
- 🎯 **Multiple Collections**: Support for multiple document collections
- 📊 **Monitoring**: Built-in metrics and monitoring support
- ⚡ **Async Task Processing**: Celery-based background processing for documents

## Architecture

The system follows a layered architecture:

- **API Layer**: FastAPI-based REST API
- **Service Layer**: Business logic and orchestration
- **Data Layer**: Vector database (Qdrant) and file storage
- **Infrastructure Layer**: Configuration, logging, and monitoring
- **Task Queue Layer**: Celery with Redis for async document processing

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Vector Database**: Qdrant
- **LLM Runtime**: Ollama (Llama 2, Mistral, etc.)
- **Embeddings**: sentence-transformers (Granite embedding model)
  - Model: `ibm-granite/granite-embedding-small-english-r2`
  - Dimension: 384
  - Max context: 8192 tokens
  - Libraries: transformers 5.0.0+, sentence-transformers 5.2.2+, torch 2.10.0+
- **Document Processing**: PyPDF2, python-docx
- **Task Queue**: Celery with Redis
- **Deployment**: Docker, Docker Compose

**Note:** For more details on the Granite model migration, see [VERSION_UPDATES.md](VERSION_UPDATES.md) or [GRANITE_MIGRATION.md](GRANITE_MIGRATION.md).

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Step 1: Clone and Setup Environment

```bash
git clone https://github.com/yourusername/simple-agentic-rag-system.git
cd simple-agentic-rag-system

# Create .env file from template
# Windows:
copy env.example .env
# Linux/Mac:
cp env.example .env

# Or use setup script
# Windows:
scripts\setup_env.bat
# Linux/Mac:
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
```

### Step 2: Start Services

**Option A: Docker Compose (Recommended)**

```bash
# Start all services (Qdrant, Ollama, Redis, Celery Worker)
docker-compose up -d qdrant ollama redis celery-worker

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Option B: Run Services Individually**

```bash
# Qdrant
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest

# Ollama
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest
docker exec ollama ollama pull llama2  # Pull model

# Redis
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

**Note**: When using Docker Compose, Ollama will automatically pull the model configured in `OLLAMA_MODEL` on startup.

### Step 3: Install Dependencies

**Option A: Using Conda (Recommended for Data Science/ML workflows)**

```bash
# Create conda environment from environment.yml
conda env create -f environment.yml

# Activate environment
conda activate simple-rag-system

# Or create environment with dev dependencies
conda env create -f environment-dev.yml
conda activate simple-rag-system-dev

# If you want to add dev dependencies later:
conda activate simple-rag-system
pip install -r requirements-dev.txt
```

**Option B: Using venv (Python virtual environment)**

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 4: Run the Application

**With Conda:**

```bash
# Windows
scripts\start_with_conda.bat

# Linux/Mac
chmod +x scripts/start_with_conda.sh
./scripts/start_with_conda.sh

# Or manually:
conda activate simple-rag-system
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**With venv:**

```bash
# Activate environment first
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run application
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Or run directly:**

```bash
python -m src.api.main
```

### Step 5: Access the System

- **API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Usage Examples

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "collection=my_collection"
```

### Query the System

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic of the document?",
    "collection": "my_collection",
    "top_k": 5
  }'
```

### List Collections

```bash
curl -X GET "http://localhost:8000/api/v1/collections"
```

### Check Task Status (for async document processing)

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}"
```

## Project Structure

```
simple-rag-system/
├── src/                                   # Application source code
│   ├── api/                               # API Layer
│   │   ├── main.py                        # FastAPI entry point
│   │   ├── middleware/                   # Custom middleware
│   │   │   ├── auth.py                   # Authentication middleware
│   │   │   ├── logging.py                # Logging middleware
│   │   │   └── rate_limit.py             # Rate limiting middleware
│   │   ├── routes/                       # API route definitions
│   │   │   ├── documents.py              # Document endpoints
│   │   │   ├── query.py                  # Query endpoints
│   │   │   ├── collections.py            # Collection endpoints
│   │   │   ├── tasks.py                  # Task status tracking endpoints
│   │   │   └── health.py                 # Health check endpoints
│   │   └── models/                       # Pydantic models
│   ├── services/                          # Business Logic Layer
│   │   ├── document_processor.py        # Document processing
│   │   ├── embedding_service.py         # Embedding generation
│   │   ├── vector_store.py              # Vector store (Qdrant)
│   │   ├── llm_service.py               # LLM service (Ollama)
│   │   ├── query_processor.py          # Query processing
│   │   └── storage_manager.py           # File storage
│   ├── tasks/                            # Background Task Processing
│   │   ├── celery_app.py                # Celery configuration
│   │   ├── document_tasks.py            # Document processing tasks
│   │   └── embedding_tasks.py           # Embedding tasks
│   ├── core/                             # Core functionality
│   │   ├── config.py                     # Configuration management
│   │   ├── exceptions.py                 # Custom exceptions
│   │   ├── logging.py                    # Logging setup
│   │   └── security.py                   # Security utilities
│   ├── utils/                            # Utility functions
│   │   ├── text_chunker.py             # Text chunking strategies
│   │   ├── validators.py                # Input validators
│   │   ├── text_cleaner.py             # Text cleaning utilities
│   │   └── helpers.py                   # Helper functions
│   ├── parsers/                         # Document parsers
│   │   ├── base.py                      # Base parser interface
│   │   ├── pdf_parser.py                # PDF parser
│   │   ├── docx_parser.py               # Word document parser
│   │   ├── txt_parser.py                # Plain text parser
│   │   └── md_parser.py                 # Markdown parser
│   ├── embedding/                       # Embedding models
│   │   ├── base.py                      # Base embedding model
│   │   ├── model_loader.py              # Model loader
│   │   ├── cache.py                     # Embedding cache
│   │   └── models/                      # Model implementations
│   └── llm/                            # LLM integration
│       ├── base.py                      # Base LLM interface
│       ├── ollama_client.py            # Ollama client
│       ├── prompt_builder.py           # Prompt builder
│       ├── templates/                  # Prompt templates
│       └── stream_handler.py           # Stream response handler
├── scripts/                            # Utility scripts
│   ├── setup_env.bat                  # Environment setup (Windows)
│   ├── setup_env.sh                   # Environment setup (Linux/Mac)
│   ├── start_with_conda.bat            # Start with Conda (Windows)
│   ├── start_with_conda.sh            # Start with Conda (Linux/Mac)
│   ├── start_celery_worker.bat        # Start Celery worker (Windows)
│   └── start_celery_worker.sh         # Start Celery worker (Linux/Mac)
├── deployments/                       # Deployment configurations
│   └── docker/
│       ├── Dockerfile                # Application Dockerfile
│       ├── docker-compose.yml       # Docker Compose for dev
│       └── docker-compose.prod.yml  # Docker Compose for production
├── docs/                              # Documentation
│   ├── 01-basic-design.md            # Basic design document
│   ├── 02-c4-model.md               # C4 model diagrams
│   ├── 03-high-level-design.md     # High-level architecture
│   ├── 04-data-flow.md             # Data flow diagrams
│   └── 05-sequence-diagrams.md     # Sequence diagrams
├── data/                             # Data directories
│   ├── documents/                   # Uploaded documents
│   ├── models/                      # Downloaded models
│   └── cache/                       # Cache directory
├── logs/                            # Log files
├── requirements.txt                  # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── environment.yml                  # Conda environment
├── environment-dev.yml             # Conda dev environment
├── docker-compose.yml             # Docker Compose configuration
├── env.example                     # Environment variables template
└── README.md                       # This file
```

## Environment Configuration

The `.env` file contains all necessary configuration. Key variables:

### Application Settings
- `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_HOST`, `APP_PORT`

### Service URLs
- `QDRANT_URL`: http://localhost:6333 (or http://qdrant:6333 for Docker)
- `OLLAMA_URL`: http://localhost:11434 (or http://ollama:11434 for Docker)
- `CELERY_BROKER_URL`: redis://localhost:6379/0 (or redis://redis:6379/0)

### Model Configuration
- `OLLAMA_MODEL`: LLM model to use (default: llama2)
- `EMBEDDING_MODEL`: Embedding model (default: ibm-granite/granite-embedding-small-english-r2)
- `EMBEDDING_DEVICE`: cpu or cuda (if GPU available)

### Document Processing
- `DOCUMENT_MAX_SIZE`: 10485760 (10MB)
- `DOCUMENT_CHUNK_SIZE`: 1000
- `DOCUMENT_CHUNK_OVERLAP`: 200

### Security
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS`: Token expiration time

### Celery Configuration
- `CELERY_BROKER_URL`: Redis broker URL
- `CELERY_RESULT_BACKEND`: Redis result backend URL
- `CELERY_TASK_TIME_LIMIT`: Task time limit in seconds
- `CELERY_WORKER_PREFETCH_MULTIPLIER`: Worker prefetch multiplier

See `env.example` for all available configuration options.

## Conda Environment Management

### Create Environment

```bash
# Basic environment
conda env create -f environment.yml

# Environment with dev dependencies
conda env create -f environment-dev.yml
```

### Manage Environment

```bash
# List environments
conda env list

# Activate environment
conda activate simple-rag-system

# Update environment
conda env update -f environment.yml --prune

# Install additional packages
conda activate simple-rag-system
pip install package-name

# Install dev dependencies to basic environment
conda activate simple-rag-system
pip install -r requirements-dev.txt

# Remove environment
conda deactivate
conda env remove -n simple-rag-system

# Export environment
conda env export > environment-custom.yml
```

### Environment Comparison

| Feature | Conda | venv |
|---------|-------|------|
| Python version management | ✅ | ❌ |
| System dependencies | ✅ | ❌ |
| Binary packages | ✅ | ❌ (mostly source) |
| Size | Larger | Smaller |
| Install speed | Faster (binary) | Slower (compile) |
| Best for | Data science, ML | Simple web apps |

## Celery Worker Setup

The system uses Celery for asynchronous document processing:

### Start Celery Worker

**Windows:**
```bash
scripts\start_celery_worker.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/start_celery_worker.sh
./scripts/start_celery_worker.sh
```

**Or manually:**
```bash
conda activate simple-rag-system
celery -A src.tasks.celery_app worker --loglevel=info --queues=documents,embeddings --concurrency=4
```

### Task Queue Architecture

- **Documents Queue**: For I/O intensive document processing tasks
- **Embeddings Queue**: For CPU/GPU intensive embedding generation tasks
- **Task Status**: Tracked via Redis result backend
- **API Integration**: Task status available at `GET /api/v1/tasks/{task_id}`

### Task Processing Flow

1. **Upload Document**: `POST /api/v1/documents/upload` → Returns task ID immediately
2. **Check Status**: `GET /api/v1/tasks/{task_id}` → Monitor task progress
3. **Background Processing**: Celery workers process tasks asynchronously
4. **Result**: Task status updates from PENDING → STARTED → SUCCESS

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_document_processor.py

# Run integration tests
pytest tests/integration/

# Run e2e tests
pytest tests/e2e/
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Debug Mode

Enable debug mode in `.env`:
```
APP_DEBUG=True
LOG_LEVEL=DEBUG
```

## Troubleshooting

### Connection Errors

**Qdrant Connection:**
```bash
# Check Qdrant is running
docker ps | grep qdrant
curl http://localhost:6333/health

# Check QDRANT_URL in .env
```

**Ollama Connection:**
```bash
# Check Ollama is running
docker ps | grep ollama
docker exec ollama ollama list

# Check OLLAMA_URL and OLLAMA_MODEL in .env
```

**Redis Connection:**
```bash
# Check Redis is running
docker ps | grep redis
docker exec redis redis-cli ping

# Check CELERY_BROKER_URL in .env
```

### Import Errors

```bash
# Ensure environment is activated
# With venv:
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# With conda:
conda activate simple-rag-system

# Run from project root
python -m src.api.main

# Check Python version (requires 3.11+)
python --version
```

### NumPy Version Incompatibility

If you encounter `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x`:

```bash
# With Conda:
conda activate simple-rag-system
conda install "numpy<2" -y
# Or:
pip install "numpy<2" --upgrade

# With venv:
pip install "numpy<2" --upgrade
```

**Note**: `requirements.txt`, `environment.yml`, and `environment-dev.yml` are configured with `numpy<2` to avoid this issue.

### KeyError 'modernbert'

If you encounter `KeyError: 'modernbert'` when running the application with Granite embedding model:

**Cause**: Old version of `transformers` doesn't support ModernBERT architecture used by Granite model.

**Solution**:

```bash
# With Conda:
conda activate simple-rag-system
conda env update -f environment.yml --prune

# Or install manually:
conda activate simple-rag-system
pip install --upgrade transformers sentence-transformers torch
```

**Minimum versions required:**
- `transformers>=5.0.0`
- `sentence-transformers>=5.2.2`
- `torch>=2.10.0`

**Note**: `requirements.txt`, `environment.yml`, and `environment-dev.yml` have been updated with these versions.

### Conda Issues

**Conda command not found:**
- Ensure conda is installed and added to PATH
- On Windows, restart terminal after installing conda
- Check: `conda --version`

**Environment not found:**
```bash
# Check if environment exists
conda env list

# Recreate if needed
conda env create -f environment.yml
```

**Cannot activate environment (Windows):**
```bash
conda init cmd.exe
# Or:
conda init powershell
```
Then restart terminal.

### Package Conflicts

```bash
# Update conda
conda update conda

# Recreate environment
conda env remove -n simple-rag-system
conda env create -f environment.yml
```

## Deployment

### Production Deployment

```bash
# Build and run with production configuration
docker-compose -f deployments/docker/docker-compose.prod.yml up -d
```

### Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

To enable monitoring:

```bash
docker-compose -f deployments/docker/docker-compose.yml --profile monitoring up -d
```

## Documentation

For detailed technical documentation:

- [Basic Design](docs/01-basic-design.md) - System overview
- [C4 Model](docs/02-c4-model.md) - Architecture diagrams
- [High-Level Design](docs/03-high-level-design.md) - Architectural patterns
- [Data Flow](docs/04-data-flow.md) - Data flow diagrams
- [Sequence Diagrams](docs/05-sequence-diagrams.md) - Interaction sequences

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Qdrant](https://qdrant.tech/) - Vector similarity search engine
- [Ollama](https://ollama.ai/) - Run LLMs locally
- [sentence-transformers](https://www.sbert.net/) - Sentence embeddings
- [LangChain](https://langchain.com/) - Framework for LLM applications

## Support

For issues, questions, or contributions, please:
- Open an issue on GitHub
- Contact: your.email@example.com

## Roadmap

- [ ] Web UI for easier document management
- [ ] Chat history and conversation memory
- [ ] Multi-modal support (images, audio)
- [ ] Advanced chunking strategies
- [ ] Reranking models
- [ ] Multi-language support
- [ ] Fine-tuning capabilities

---

**Note**: This is a simple RAG system designed for demonstration and learning purposes. For production use, consider additional security measures, monitoring, and optimization.

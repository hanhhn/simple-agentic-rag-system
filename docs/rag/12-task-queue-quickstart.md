# Task Queue Quick Start Guide

## Tổng quan nhanh

Hệ thống sử dụng **Celery + Redis** để xử lý document processing và embedding generation một cách bất đồng bộ.

## Kiến trúc đơn giản

```
User Upload → API Server → Redis Queue → Celery Worker → Services → Qdrant
```

## Cài đặt nhanh

### 1. Start Services

```bash
# Start Redis và Celery Worker
docker-compose up redis celery-worker -d

# Hoặc start tất cả
docker-compose up -d
```

### 2. Verify Services

```bash
# Check Redis
redis-cli ping
# Response: PONG

# Check Celery Worker
celery -A src.tasks.celery_app inspect active
# Response: List of active workers
```

## Sử dụng

### Upload Document (Async)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf" \
  -F "collection=my_collection"
```

**Response:**
```json
{
  "task_id": "abc-123-def-456",
  "document_id": "doc-xyz-789",
  "filename": "document.pdf",
  "collection": "my_collection",
  "status": "PENDING",
  "message": "Document upload queued for processing"
}
```

### Check Task Status

```bash
curl "http://localhost:8000/api/v1/tasks/abc-123-def-456"
```

**Response (PENDING):**
```json
{
  "task_id": "abc-123-def-456",
  "status": "PENDING",
  "task_name": "src.tasks.document_tasks.process_document_task",
  "result": null
}
```

**Response (SUCCESS):**
```json
{
  "task_id": "abc-123-def-456",
  "status": "SUCCESS",
  "task_name": "src.tasks.document_tasks.process_document_task",
  "result": {
    "success": true,
    "chunk_count": 150,
    "embedding_task_id": "emb-789-xyz"
  },
  "completed_at": "2024-01-30T10:02:30Z"
}
```

## Flow đơn giản

1. **Upload** → Nhận task_id ngay lập tức
2. **Check Status** → Polling hoặc webhook
3. **Done** → Document đã sẵn sàng để query

## Troubleshooting

### Task không được xử lý

```bash
# Check worker đang chạy
docker-compose ps celery-worker

# Check logs
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker
```

### Task bị stuck

```bash
# Revoke task
curl -X POST "http://localhost:8000/api/v1/tasks/{task_id}/revoke"
```

### Check Queue Status

```bash
# Connect Redis
redis-cli

# Check queue length
LLEN documents
LLEN embeddings
```

## Next Steps

Xem **[Task Queue Architecture](12-task-queue-architecture.md)** để hiểu chi tiết về:
- Architecture chi tiết
- Configuration options
- Monitoring & debugging
- Performance optimization

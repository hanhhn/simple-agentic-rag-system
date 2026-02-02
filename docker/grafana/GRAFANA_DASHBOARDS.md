# Grafana Dashboards for RAG System

This document describes the available Grafana dashboards for monitoring the RAG (Retrieval-Augmented Generation) system.

## Access Grafana

- **URL**: http://localhost:3000
- **Default Username**: `admin`
- **Default Password**: `admin123`

## Available Dashboards

### 1. RAG System Overview (`rag-system-overview`)

**Purpose**: High-level monitoring of all system components

**Panels**:
- **Service Status**: Real-time status of Backend, Qdrant, Loki, and Celery workers
- **API Request Rate**: HTTP request rate per endpoint (GET, POST, etc.)
- **API Response Time**: P95 and P99 latency metrics
- **Error Rate**: HTTP 4xx and 5xx error percentages
- **Celery Task Throughput**: Tasks received, started, succeeded, and failed
- **Task Queue Length**: Number of pending tasks in each queue
- **CPU Usage**: CPU utilization for backend and celery workers
- **Memory Usage**: Memory consumption by service

**Data Sources**: Prometheus

---

### 2. RAG System Logs - Search & Monitor (`rag-logs-search-dashboard`)

**Purpose**: Advanced log search and analysis with Loki

**Panels**:
- **System Logs - Search Here**: Main log explorer with full-text search capabilities
  - Search queries: Type in the search bar to filter logs
  - Example searches:
    - `error` - Find all error messages
    - `duration` - Find logs with duration metrics
    - `user_id=123` - Find logs for specific user
- **Log Rate by Service**: Log volume per service over time
- **Error & Warning Rate**: Error and warning log rates by service
- **Log Distribution by Level**: Pie chart showing INFO, WARNING, ERROR distribution
- **Error Logs Only**: Filtered view showing only error logs
- **Request Duration**: Timing information extracted from logs
- **Events by Type**: Rate of different event types

**Variables**:
- **Log Level**: Filter by log level (INFO, WARNING, ERROR, etc.)
- **Logger**: Filter by logger name/component
- **Service**: Filter by service (backend, celery-worker, etc.)
- **Search Query**: Free-text search filter

**Data Sources**: Loki

**Tips**:
- Use the search box to find specific log messages
- Click on log entries to view full details
- Use the "Explore" mode for ad-hoc queries
- Filter by service to focus on specific components

---

### 3. Qdrant Vector Store Performance (`qdrant-performance-dashboard`)

**Purpose**: Monitor vector database performance and storage

**Panels**:
- **System Status**:
  - Qdrant Status: Service health (UP/DOWN)
  - Total Collections: Number of collections
  - Total Points: Total number of vectors stored
  - Total Memory Usage: Storage memory consumption
  - Search Rate: Number of search operations per second
  - Insert Rate: Number of insert operations per second

- **Performance Metrics**:
  - Operation Latency (P95): Response times for search and insert operations
  - Request Rate by Operation: Throughput for search, insert, delete, update

- **Storage & Collections**:
  - Points per Collection: Distribution of vectors across collections
  - Storage Usage by Collection: Data, index, and payload index sizes

- **Error Rates**:
  - Error Rate: Failed search and insert operations

**Variables**:
- **Collection**: Filter by specific collection

**Data Sources**: Prometheus

**Metrics Monitored**:
- `qdrant_search_latency_seconds`
- `qdrant_insert_latency_seconds`
- `qdrant_points_count`
- `qdrant_collections_segment_data_size_bytes`
- And more...

---

### 4. Task Queue Monitor - Celery & Redis (`task-queue-monitor-dashboard`)

**Purpose**: Monitor asynchronous task processing

**Panels**:
- **Worker Status**:
  - Celery Worker: Worker health status
  - Active Tasks: Currently executing tasks
  - Queue Length: Number of pending tasks
  - Reserved Tasks: Tasks reserved but not yet started

- **Task Throughput**:
  - Tasks Received: Rate of tasks entering the queue
  - Tasks Started: Rate of tasks being processed
  - Tasks Success: Rate of completed tasks
  - Tasks Failed: Rate of failed tasks
  - Tasks Retry: Rate of retried tasks

- **Task Performance**:
  - Task Runtime Distribution: P50, P95, P99 execution times
  - Task Success/Failure Rate: Percentage of successful and failed tasks

- **Queue Details**:
  - Queue Length by Queue: Pending tasks per queue (documents, embeddings)

- **Task Types**:
  - Tasks by Type (Rate): Distribution by task type
  - Failed Tasks by Type (Rate): Failed tasks distribution

- **Redis Connection**:
  - Redis Connected Clients: Active connections
  - Redis Memory Used: Memory consumption
  - Redis Commands/sec: Operation rate
  - Redis Total Keys: Number of keys stored

**Variables**:
- **Task Name**: Filter by specific task type
- **Queue**: Filter by specific queue name

**Data Sources**: Prometheus

**Task Types Monitored**:
- Document processing tasks
- Embedding generation tasks
- Data crawling tasks

---

## Data Sources

### Prometheus
- **URL**: http://prometheus:9090
- **Purpose**: Metrics collection and storage
- **Scrape Interval**: 15s (default)

### Loki
- **URL**: http://loki:3100
- **Purpose**: Log aggregation and querying
- **Log Collection**: Promtail agent from all services

---

## Troubleshooting

### Dashboards Not Loading

1. **Restart Grafana**:
   ```bash
   docker-compose restart grafana
   ```

2. **Check Dashboard Files**:
   ```bash
   ls -la docker/grafana/provisioning/dashboards/
   ```

3. **Verify Grafana Logs**:
   ```bash
   docker logs rag-grafana -f
   ```

4. **Check Data Sources**:
   - Go to Configuration → Data Sources
   - Verify Prometheus and Loki are healthy
   - Test connection for each data source

### No Data Showing

1. **Check Prometheus Targets**:
   - Go to http://localhost:9090/targets
   - Verify all targets are UP

2. **Check Metrics Availability**:
   - In Prometheus UI, query: `up`
   - Should see metrics from all services

3. **Check Loki Logs**:
   - Verify Promtail is running: `docker logs rag-promtail`
   - Check logs directory: `ls -la logs/`

4. **Backend Metrics**:
   - Ensure `/metrics` endpoint is enabled in backend
   - Check: `curl http://localhost:8000/metrics`

### Dashboard Configuration

Dashboard files are located at:
```
docker/grafana/provisioning/dashboards/
├── dashboards.yml                    # Dashboard provider configuration
├── loki-logs-dashboard.json          # Log search and monitoring
├── qdrant-performance.json           # Vector store metrics
├── rag-system-overview.json          # System overview
└── task-queue-monitor.json           # Celery task monitoring
```

## Customization

### Add Custom Panels

1. Open dashboard in Grafana
2. Click "Add panel" button
3. Configure data source and query
4. Save dashboard

### Modify Dashboards

1. Edit JSON files in `docker/grafana/provisioning/dashboards/`
2. Restart Grafana: `docker-compose restart grafana`
3. Changes will be persisted (if you disable updates in `dashboards.yml`)

### Change Refresh Intervals

Each dashboard has a `refresh` field (e.g., `"refresh": "10s"`). Modify this to:
- `"5s"` - Faster updates (more CPU usage)
- `"30s"` - Slower updates (less CPU usage)
- `"off"` - Manual refresh only

## Alerts (Future Enhancement)

To set up alerts:

1. Go to Alerting → New alert rule
2. Select query and conditions
3. Set notification channels (email, Slack, etc.)
4. Define alert evaluation intervals

Example alert conditions:
- API error rate > 5%
- Celery queue length > 50
- Qdrant search latency P95 > 500ms
- Memory usage > 90%

## Performance Tips

1. **Adjust Time Ranges**: Use shorter ranges (1h, 6h) for better performance
2. **Reduce Panel Count**: Remove unused panels from dashboards
3. **Cache Queries**: Enable query caching in data source settings
4. **Optimize Intervals**: Increase refresh interval if not needed
5. **Use Query Variables**: Use variables to reduce query complexity

## Export/Import Dashboards

### Export
1. Open dashboard
2. Click "Share" → "Export"
3. Choose "Export for sharing externally"
4. Save JSON file

### Import
1. Go to Dashboards → Import
2. Upload JSON file or paste content
3. Select data source
4. Click "Import"

---

## Support

For issues or questions:
1. Check Grafana documentation: https://grafana.com/docs/
2. Check Prometheus documentation: https://prometheus.io/docs/
3. Check Loki documentation: https://grafana.com/docs/loki/latest/
4. Review logs in the `logs/` directory

---

**Last Updated**: 2026-01-31
**Version**: 1.0

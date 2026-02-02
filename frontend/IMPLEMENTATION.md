# Frontend Implementation - RAG System

## Overview
This document describes the comprehensive frontend implementation for the RAG (Retrieval-Augmented Generation) system.

## Tech Stack
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Shadcn UI** - Component library
- **Radix UI** - Headless UI primitives
- **Lucide React** - Icons

## Architecture

### Directory Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Shadcn UI components
│   │   ├── layout/        # Layout components
│   │   └── HealthStatus.tsx
│   ├── pages/             # Page components
│   ├── lib/
│   │   ├── api.ts         # API client
│   │   └── utils.ts      # Utility functions
│   ├── hooks/
│   │   └── use-toast.ts  # Toast notifications
│   └── App.tsx
├── public/
└── package.json
```

## Pages

### 1. Query Page (`/`)
**Purpose:** Submit natural language queries to the RAG system

**Features:**
- Collection selection dropdown
- Query input with configurable parameters (Top K, Score Threshold, RAG toggle)
- Display of generated answers
- Retrieved documents with similarity scores and metadata
- Loading states and error handling
- Toast notifications for success/failure

**API Endpoints Used:**
- `GET /collections` - Load available collections
- `POST /query` - Submit query

### 2. Collections Page (`/collections`)
**Purpose:** Manage vector collections

**Features:**
- List all collections with vector counts, dimensions, status, and distance metrics
- Create new collections with configurable parameters
- Delete collections (with confirmation dialog)
- Status badges for collection state
- Auto-refresh on operations
- Toast notifications

**API Endpoints Used:**
- `GET /collections` - List collections
- `POST /collections` - Create collection
- `DELETE /collections/{name}` - Delete collection

### 3. Documents Page (`/documents`)
**Purpose:** Upload and manage documents

**Features:**
- Upload documents (PDF, TXT, MD, DOCX) to selected collections
- List documents with metadata (filename, chunk count, upload date)
- Download original documents
- Delete documents with confirmation
- Task ID display for async processing
- Toast notifications

**API Endpoints Used:**
- `GET /collections` - Load collections for dropdown
- `GET /documents/list/{collection}` - List documents
- `POST /documents/upload` - Upload document
- `GET /documents/download/{collection}/{filename}` - Download document
- `DELETE /documents/{collection}/{filename}` - Delete document

### 4. Tasks Page (`/tasks`)
**Purpose:** Monitor background processing tasks

**Features:**
- List all active and completed tasks
- Auto-refresh every 3 seconds (toggleable)
- View task details (status, progress, result, error, traceback, metadata)
- Cancel/revoke running tasks
- Progress bars for in-progress tasks
- Status badges with icons
- Manual refresh button
- Toast notifications

**API Endpoints Used:**
- `GET /tasks` - List tasks
- `GET /tasks/{task_id}` - Get task details
- `POST /tasks/{task_id}/revoke` - Cancel task

## Components

### UI Components (Shadcn)
- **Button** - Primary, secondary, outline, destructive, ghost variants
- **Card** - Content containers with header, title, description
- **Input** - Text input fields
- **Textarea** - Multi-line text input
- **Badge** - Status indicators
- **Table** - Data tables with header, body, rows, cells
- **Dialog** - Modal dialogs for confirmations
- **Progress** - Progress bars
- **Skeleton** - Loading placeholders
- **Toast** - Notifications (with Toaster component)
- **Label** - Form labels

### Custom Components

#### HealthStatus
Real-time system health monitoring dashboard.

**Features:**
- Overall system status badge (healthy/unhealthy)
- Service status cards (Embedding, LLM, Vector Store, Storage)
- Auto-refresh every 30 seconds
- Visual indicators with icons
- Last check timestamp

**API Endpoint:**
- `GET /health/status`

## API Client (`lib/api.ts`)

### Base Configuration
- Base URL: `http://localhost:8000/api/v1` (configurable via `VITE_API_URL` env var)
- Timeout: 30 seconds
- Content-Type: `application/json`

### Types

```typescript
// Collection
interface CollectionInfo {
  name: string;
  vector_count: number;
  dimension: number;
  status: string;
  created_at: string;
  distance_metric: string;
}

// Document
interface DocumentData {
  document_id: string;
  filename: string;
  collection: string;
  chunk_count: number;
  uploaded_at: string;
  metadata: Record<string, any>;
}

// Query
interface QueryResponse {
  query: string;
  answer?: string;
  answer_chunks?: string[];
  retrieved_documents: RetrievedDocument[];
  retrieval_count: number;
  collection: string;
  top_k: number;
  score_threshold: number;
  use_rag: boolean;
  timestamp?: string;
}

// Task
interface TaskResponse {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
  task_name: string;
  result?: Record<string, any> | null;
  error?: string | null;
  traceback?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  progress?: number | null;
  metadata: Record<string, any>;
}

// Health
interface HealthStatus {
  status: string;
  timestamp: string;
  services: {
    embedding: boolean;
    llm: boolean;
    vector_store: boolean;
    storage: boolean;
  };
}
```

## State Management

The application uses React's built-in state management with hooks:
- `useState` - Component state
- `useEffect` - Side effects (data fetching, intervals)
- `useToast` - Toast notifications

## Error Handling

### Error Display
- Toast notifications for user feedback
- Console logging for debugging
- Descriptive error messages

### Error Types
1. **Network Errors** - Failed API calls
2. **Validation Errors** - Invalid inputs
3. **Server Errors** - Backend issues
4. **Processing Errors** - Task failures

## Loading States

### Loading Indicators
- Spinner icons (`Loader2` with animation)
- Skeleton loaders for content placeholders
- Progress bars for long-running tasks
- Disabled buttons during operations

## Features Implemented

### ✅ Collections Management
- List all collections
- Create new collections
- Delete collections
- View collection details (vector count, dimension, status, metric)

### ✅ Documents Management
- Upload documents (PDF, TXT, MD, DOCX)
- List documents in collections
- Delete documents
- Download documents
- View document metadata

### ✅ Query Interface
- Submit natural language queries
- Select collection
- Configure Top K and Score Threshold
- Toggle RAG generation
- View answers and retrieved documents
- Display similarity scores and metadata

### ✅ Task Monitoring
- List all tasks
- View task details
- Cancel running tasks
- Auto-refresh every 3 seconds
- Progress tracking
- Status badges with icons

### ✅ System Health
- Real-time health monitoring
- Service status indicators
- Auto-refresh every 30 seconds
- Overall system status

### ✅ User Experience
- Toast notifications
- Loading states
- Error handling
- Confirmation dialogs
- Responsive design
- Clean, modern UI

## Setup Instructions

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure API URL (optional)
If backend is not on `localhost:8000`, create `.env` file:
```
VITE_API_URL=http://your-api-url:port/api/v1
```

### 3. Start Development Server
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 4. Build for Production
```bash
npm run build
```

Built files will be in `dist/` directory.

## Environment Variables

- `VITE_API_URL` - Backend API base URL (default: `http://localhost:8000/api/v1`)

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

## Accessibility

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Screen reader friendly
- Color contrast compliance

## Performance Optimizations

- Code splitting with React Router
- Lazy loading of components
- Optimized re-renders
- Efficient API calls with cancellation
- Debounced auto-refresh

## Security

- CORS handling
- Input validation
- XSS prevention via React escaping
- Secure HTTP headers

## Future Enhancements

### Potential Features
1. **Query History** - Save and load previous queries
2. **Streaming Responses** - Real-time LLM output
3. **Advanced Filters** - Filter by document type, date, etc.
4. **Export Results** - Download query results as PDF/CSV
5. **Dark Mode** - Theme toggle
6. **Pagination** - For large document/task lists
7. **Search** - Within collections and tasks
8. **Analytics Dashboard** - Usage statistics and insights
9. **Batch Operations** - Upload/delete multiple documents
10. **Document Preview** - View document content before querying

### UI Improvements
1. Drag-and-drop file upload
2. Rich text editor for queries
3. Collapsible document details
4. Keyboard shortcuts
5. Mobile app version

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check backend is running on port 8000
   - Verify CORS configuration
   - Check `VITE_API_URL` environment variable

2. **Document Upload Fails**
   - Check file size limits
   - Verify supported file format
   - Check task status in Tasks page

3. **Query Returns No Results**
   - Verify collection has documents
   - Lower score threshold
   - Increase Top K value

4. **Tasks Stuck in PENDING**
   - Check Celery worker is running
   - Review backend logs
   - Try restarting Celery

## API Compatibility

This frontend is fully compatible with the backend API documented in:
- `src/api/routes/collections.py`
- `src/api/routes/documents.py`
- `src/api/routes/query.py`
- `src/api/routes/tasks.py`
- `src/api/models/` (all Pydantic models)

All response types match the backend Pydantic models.

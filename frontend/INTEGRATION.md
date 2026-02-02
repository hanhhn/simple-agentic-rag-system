# Frontend Integration Guide

This document describes how the React frontend integrates with the RAG System API.

## API Integration

The frontend communicates with the FastAPI backend through the API client located at `src/lib/api.ts`. The API base URL can be configured via the `VITE_API_URL` environment variable (defaults to `http://localhost:8000`).

## Features

### 1. Collections Management (`/collections`)
- List all collections
- Create new collections
- Delete collections
- View collection details (vector count, dimension, status)

### 2. Documents Management (`/documents`)
- List documents in a collection
- Upload documents (PDF, TXT, MD, DOCX)
- Delete documents
- View document metadata

### 3. Query Interface (`/`)
- Submit natural language queries
- Select collection to query
- Configure query parameters (top_k, use_rag)
- View answers and retrieved documents
- Display similarity scores

### 4. Task Monitoring (`/tasks`)
- View all background tasks
- Monitor task status and progress
- Auto-refresh functionality
- Task details (creation time, completion time, errors)

## API Endpoints Used

### Collections
- `GET /api/v1/collections` - List collections
- `POST /api/v1/collections` - Create collection
- `GET /api/v1/collections/{name}` - Get collection details
- `DELETE /api/v1/collections/{name}` - Delete collection

### Documents
- `GET /api/v1/documents/list/{collection}` - List documents
- `POST /api/v1/documents/upload` - Upload document
- `DELETE /api/v1/documents/{collection}/{filename}` - Delete document
- `GET /api/v1/documents/download/{collection}/{filename}` - Download document

### Query
- `POST /api/v1/query` - Process query

### Tasks
- `GET /api/v1/tasks` - List tasks
- `GET /api/v1/tasks/{task_id}` - Get task status
- `POST /api/v1/tasks/{task_id}/revoke` - Revoke task

## Running the Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure API URL (optional):
```bash
cp .env.example .env
# Edit .env if your API is not on localhost:8000
```

3. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port Vite assigns).

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Shadcn UI** - Component library
- **Tailwind CSS** - Styling
- **React Router** - Routing
- **Axios** - HTTP client

## Component Structure

```
src/
├── components/
│   ├── ui/          # Shadcn UI components
│   └── layout/      # Layout components
├── lib/
│   ├── api.ts       # API client
│   └── utils.ts     # Utility functions
├── pages/           # Page components
│   ├── QueryPage.tsx
│   ├── CollectionsPage.tsx
│   ├── DocumentsPage.tsx
│   └── TasksPage.tsx
└── App.tsx          # Main app component
```

## Environment Variables

- `VITE_API_URL` - Backend API URL (default: `http://localhost:8000`)

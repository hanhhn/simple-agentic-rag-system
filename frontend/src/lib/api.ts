import axios, { type AxiosInstance } from 'axios';

// Base configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Types based on backend API models
export interface CollectionInfo {
  name: string;
  vector_count: number;
  dimension: number;
  status: string;
  created_at: string;
  distance_metric: string;
}

export interface DocumentResponse {
  document_id: string;
  filename: string;
  collection: string;
  chunk_count: number;
  uploaded_at: string;
  metadata: Record<string, any>;
}

export interface RetrievedDocument {
  id: string;
  score: number;
  text: string;
  metadata: Record<string, any>;
}

export interface QueryResponse {
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

export interface TaskResponse {
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

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  services: {
    qdrant?: string;
    ollama?: string;
    embeddings?: string;
    [key: string]: string | undefined;
  };
}

// API client object
export const api = {
  // Collections API
  collections: {
    list: async () => {
      const response = await client.get<{ collections: CollectionInfo[] }>('/api/v1/collections');
      return response.data;
    },

    create: async (name: string, dimension?: number, distance_metric?: string) => {
      const response = await client.post<{ collection: CollectionInfo }>('/api/v1/collections', {
        name,
        dimension,
        distance_metric,
      });
      return response.data;
    },

    get: async (name: string) => {
      const response = await client.get<{ collection: CollectionInfo }>(`/api/v1/collections/${name}`);
      return response.data;
    },

    delete: async (name: string) => {
      await client.delete(`/api/v1/collections/${name}`);
    },
  },

  // Documents API
  documents: {
    list: async (collection: string) => {
      const response = await client.get<{ documents: DocumentResponse[]; total: number; collection: string }>(`/api/v1/documents/list/${collection}`);
      return response.data;
    },

    upload: async (collection: string, file: File, chunkSize?: number, chunkOverlap?: number, chunkerType?: string) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('collection', collection);
      if (chunkSize) formData.append('chunk_size', chunkSize.toString());
      if (chunkOverlap) formData.append('chunk_overlap', chunkOverlap.toString());
      if (chunkerType) formData.append('chunker_type', chunkerType);

      // For FormData, axios automatically sets Content-Type with boundary
      // Create a request without the default Content-Type header
      const response = await axios.post<{ task_id: string; document_id: string; filename: string; collection: string; status: string; message: string }>(
        `${API_BASE_URL}/api/v1/documents/upload`,
        formData,
        {
          timeout: 30000,
          // Axios will automatically set Content-Type with boundary for FormData
        }
      );
      return response.data;
    },

    download: async (collection: string, filename: string) => {
      const response = await client.get(
        `/api/v1/documents/download/${collection}/${filename}`,
        {
          responseType: 'blob',
        }
      );
      return response.data;
    },

    delete: async (collection: string, filename: string) => {
      await client.delete(`/api/v1/documents/${collection}/${filename}`);
    },
  },

  // Query API
  query: {
    process: async (params: {
      query: string;
      collection: string;
      top_k?: number;
      score_threshold?: number;
      use_rag?: boolean;
      stream?: boolean;
    }) => {
      const response = await client.post<QueryResponse>('/api/v1/query', params);
      return response.data;
    },

    stream: async (params: {
      query: string;
      collection: string;
      top_k?: number;
      score_threshold?: number;
      use_rag?: boolean;
      stream?: boolean;
    }) => {
      const response = await client.post<QueryResponse>('/api/v1/query/stream', params);
      return response.data;
    },
  },

  // Tasks API
  tasks: {
    list: async (status?: string, limit: number = 100) => {
      const params: any = { limit };
      if (status) params.status = status;
      const response = await client.get<{ tasks: TaskResponse[]; total: number }>('/api/v1/tasks', { params });
      return response.data;
    },

    get: async (taskId: string) => {
      const response = await client.get<TaskResponse>(`/api/v1/tasks/${taskId}`);
      return response.data;
    },

    revoke: async (taskId: string) => {
      await client.post(`/api/v1/tasks/${taskId}/revoke`);
    },
  },

  // Health API
  health: {
    check: async () => {
      const response = await client.get<HealthResponse>('/health');
      return response.data;
    },

    ready: async () => {
      const response = await client.get<{ status: string; timestamp: string }>('/health/ready');
      return response.data;
    },
  },
};

export default api;

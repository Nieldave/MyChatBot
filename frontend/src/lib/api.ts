import axios from 'axios';
import { auth } from './firebase';
import { onAuthStateChanged, signOut } from 'firebase/auth';

const API_URL = import.meta.env.VITE_API_URL || 'https://chatbot-platform-api.onrender.com/';

// --------------------
// AXIOS INSTANCE
// --------------------
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --------------------
// AUTH READY PROMISE (CRITICAL FIX)
// --------------------
let authReadyResolve: () => void;
const authReady = new Promise<void>((resolve) => {
  authReadyResolve = resolve;
});

onAuthStateChanged(auth, () => {
  authReadyResolve();
});

// --------------------
// REQUEST INTERCEPTOR
// --------------------
api.interceptors.request.use(
  async (config) => {
    // WAIT until Firebase restores session
    await authReady;

    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// --------------------
// RESPONSE INTERCEPTOR
// --------------------
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.warn('Unauthorized – logging out');
      await signOut(auth);
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// --------------------
// AUTH API
// --------------------
export const registerUser = async (
  email: string,
  password: string,
  displayName: string
) => {
  const response = await api.post('/api/auth/register', {
    email,
    password,
    display_name: displayName,
  });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

// --------------------
// PROJECTS API
// --------------------
export interface Project {
  id: string;
  name: string;
  systemPrompt: string;
  createdAt: string;
}

export const getProjects = async (): Promise<Project[]> => {
  const response = await api.get('/api/projects');
  return response.data.projects;
};

export const createProject = async (name: string, systemPrompt: string) => {
  const response = await api.post('/api/projects', {
    name,
    system_prompt: systemPrompt,
  });
  return response.data;
};

export const getProject = async (projectId: string): Promise<Project> => {
  const response = await api.get(`/api/projects/${projectId}`);
  return response.data;
};

export const deleteProject = async (projectId: string) => {
  const response = await api.delete(`/api/projects/${projectId}`);
  return response.data;
};

// --------------------
// CHAT API
// --------------------
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const sendMessage = async (
  projectId: string,
  message: string
): Promise<string> => {
  const response = await api.post(`/api/chat/${projectId}`, { message });
  return response.data.response;
};

export const getChatHistory = async (
  projectId: string
): Promise<ChatMessage[]> => {
  const response = await api.get(`/api/chat/${projectId}/history`);
  return response.data.history;
};

// --------------------
// FILE API (BONUS)
// --------------------
export const uploadFile = async (projectId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(
    `/api/projects/${projectId}/files`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );

  return response.data;
};

export const listFiles = async (projectId: string) => {
  const response = await api.get(`/api/projects/${projectId}/files`);
  return response.data.files;
};

export const deleteFile = async (projectId: string, fileId: string) => {
  const response = await api.delete(
    `/api/projects/${projectId}/files/${fileId}`
  );
  return response.data;
};

export default api;

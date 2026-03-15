import axios from 'axios';
import type {
  Book,
  BookPreference,
  CreatePreferencePayload,
  CreateReadingSessionPayload,
  QuickRecommendation,
  ReadingSession,
  ReadingStats,
  Recommendation,
} from '../types';

// Update this to your backend's IP/hostname when running on a physical device
const API_BASE_URL = 'http://localhost:8000/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Books ──────────────────────────────────────────────────────────────────

export const booksApi = {
  search: (query: string) =>
    client.get<Book[]>('/books', { params: { query } }).then((r) => r.data),

  getById: (id: number) =>
    client.get<Book>(`/books/${id}`).then((r) => r.data),

  searchExternal: (query: string) =>
    client
      .get<Book[]>('/integrations/search-books', { params: { query } })
      .then((r) => r.data),
};

// ── Preferences ────────────────────────────────────────────────────────────

export const preferencesApi = {
  getAll: (status?: string) =>
    client
      .get<BookPreference[]>('/preferences', { params: status ? { status } : undefined })
      .then((r) => r.data),

  getForBook: (bookId: number) =>
    client.get<BookPreference>(`/books/${bookId}/preference`).then((r) => r.data),

  upsert: (bookId: number, data: CreatePreferencePayload) =>
    client.post<BookPreference>(`/books/${bookId}/preference`, data).then((r) => r.data),

  delete: (bookId: number) =>
    client.delete(`/books/${bookId}/preference`).then((r) => r.data),
};

// ── Reading Sessions ───────────────────────────────────────────────────────

export const sessionsApi = {
  create: (data: CreateReadingSessionPayload) =>
    client.post<ReadingSession>('/reading-sessions', data).then((r) => r.data),

  getAll: (params?: { book_id?: number; limit?: number }) =>
    client.get<ReadingSession[]>('/reading-sessions', { params }).then((r) => r.data),

  getStats: () =>
    client.get<ReadingStats>('/reading-sessions/statistics').then((r) => r.data),
};

// ── Recommendations ────────────────────────────────────────────────────────

export const recommendationsApi = {
  getQuick: () =>
    client.get<QuickRecommendation>('/recommendations/quick').then((r) => r.data),

  getAll: () =>
    client.get<Recommendation[]>('/recommendations').then((r) => r.data),

  click: (id: number) =>
    client.post(`/recommendations/${id}/click`).then((r) => r.data),

  dismiss: (id: number) =>
    client.post(`/recommendations/${id}/dismiss`).then((r) => r.data),
};

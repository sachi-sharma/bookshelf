import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
})

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface Book {
  id: number
  title: string
  author?: string
  isbn?: string
  genre?: string
  cover_image_url?: string
  description?: string
  page_count?: number
}

export interface ReadingSession {
  id: number
  book_id: number
  action: 'taken' | 'returned'
  timestamp: string
  duration_minutes?: number
  mood?: string
  location?: string
  notes?: string
  status?: string  // "want_to_read", "currently_reading", "read", "abandoned"
  tags?: string[]  // User-defined tags array
  pages_read?: number
  book?: Book
}

export interface Recommendation {
  id: number
  book_id: number
  score: number
  reason?: string
  factors?: Record<string, any>
  book?: Book
}

export interface BookCreate {
  title: string
  author?: string
  isbn?: string
  genre?: string
  publisher?: string
  publication_date?: string
  tags?: string[]
  description?: string
  cover_image_url?: string
  page_count?: number
  language?: string
}

export interface BookPreference {
  id: number
  book_id: number
  rating?: number
  review?: string
  status?: string  // "read", "want_to_read", "currently_reading", "abandoned"
  favorite: boolean
  tags?: string[]
  book?: Book
}

export const booksApi = {
  search: (query?: string, limit?: number) => api.get<Book[]>('/books', { params: { q: query, limit } }),
  getById: (id: number) => api.get<Book>(`/books/${id}`),
  getByIds: (ids: number[]) => api.get<Book[]>('/books/bulk', { params: { ids: ids.join(',') } }),
  create: (book: BookCreate) => api.post<Book>('/books', book),
}

export const sessionsApi = {
  create: (session: Partial<ReadingSession>) => api.post<ReadingSession>('/reading-sessions', session),
  getAll: (params?: any) => api.get<ReadingSession[]>('/reading-sessions', { params }),
  getBookIds: () => api.get<{ book_ids: number[] }>('/reading-sessions/book-ids'),
}

export interface QuickRecommendationResponse {
  recommendation: Recommendation | null
  context: {
    current_time: {
      time_of_day: string
      day_of_week: string
      month: number
    }
    user_context: {
      mood?: string
      location?: string
      available_time_minutes?: number
    }
    available_books: number[]
    reading_stats: {
      average_pace_pages_per_minute?: number
    }
  }
  alternatives?: Recommendation[]
  message?: string
}

export const recommendationsApi = {
  get: (mood?: string, limit = 10) => api.get<Recommendation[]>('/recommendations', { params: { mood, limit } }),
  getQuick: (params?: {
    mood?: string
    location?: string
    available_time_minutes?: number
    only_available?: boolean
    refresh?: boolean
  }) => api.get<QuickRecommendationResponse>('/recommendations/quick', { params }),
}

export const integrationsApi = {
  get: () => api.get('/integrations'),
  connect: (platform: string, data: any) => api.post(`/integrations/${platform}/connect`, data),
  sync: (platform: string) => api.post(`/integrations/${platform}/sync`),
  disconnect: (platform: string) => 
    api.delete(`/integrations/${platform}/disconnect`),
  searchBooks: (query: string, source: 'google_books' | 'openlibrary' = 'google_books', limit = 20) => 
    api.get('/integrations/search-books', { params: { q: query, source, limit } }),
  getBookByIsbn: (isbn: string, source: 'google_books' | 'openlibrary' = 'google_books') =>
    api.get('/integrations/book-by-isbn', { params: { isbn, source } }),
}

export const preferencesApi = {
  get: (bookId: number) => api.get<BookPreference>(`/books/${bookId}/preference`),
  createOrUpdate: (bookId: number, data: { status?: string | null; rating?: number; review?: string; favorite?: boolean; tags?: string[] }) =>
    api.post<BookPreference>(`/books/${bookId}/preference`, data),
  getAll: (status?: string) => api.get<BookPreference[]>('/preferences', { params: { status } }),
  delete: (bookId: number) => api.delete(`/books/${bookId}/preference`),
}


export default api


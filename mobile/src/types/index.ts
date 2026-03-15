export interface Book {
  id: number;
  title: string;
  author: string;
  isbn?: string;
  genre?: string;
  description?: string;
  cover_image_url?: string;
  page_count?: number;
  publisher?: string;
  publication_date?: string;
  tags?: string[];
}

export interface BookPreference {
  id: number;
  user_id: number;
  book_id: number;
  rating?: number;
  review?: string;
  status: ReadingStatus;
  favorite: boolean;
  tags?: string[];
  created_at: string;
  updated_at: string;
  book?: Book;
}

export type ReadingStatus =
  | 'want_to_read'
  | 'currently_reading'
  | 'read'
  | 'abandoned';

export type SessionAction = 'taken' | 'returned';

export type Mood =
  | 'focused'
  | 'relaxed'
  | 'curious'
  | 'tired'
  | 'energized'
  | 'sad'
  | 'happy';

export type Location = 'home' | 'commute' | 'cafe' | 'library' | 'outdoors' | 'other';

export interface ReadingSession {
  id: number;
  user_id: number;
  book_id: number;
  action: SessionAction;
  timestamp: string;
  duration_minutes?: number;
  mood?: Mood;
  location?: Location;
  notes?: string;
  pages_read?: number;
  status?: ReadingStatus;
  book?: Book;
}

export interface ReadingStats {
  total_sessions: number;
  total_duration_minutes: number;
  total_pages_read: number;
  books_read: number;
  average_session_duration: number;
}

export interface Recommendation {
  id: number;
  user_id: number;
  book_id: number;
  score: number;
  reason: string;
  factors?: Record<string, unknown>;
  book?: Book;
}

export interface QuickRecommendation {
  book: Book;
  reason: string;
  context: string;
}

export interface CreateReadingSessionPayload {
  book_id: number;
  action: SessionAction;
  duration_minutes?: number;
  mood?: Mood;
  location?: Location;
  notes?: string;
  pages_read?: number;
  status?: ReadingStatus;
}

export interface CreatePreferencePayload {
  status: ReadingStatus;
  rating?: number;
  review?: string;
  favorite?: boolean;
}

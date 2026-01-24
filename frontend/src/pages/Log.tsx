/**
 * Log - Answers: "What just happened?"
 * 
 * Fast, minimal, boring
 * Required: book, duration
 * Optional: mood
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useLocation } from 'react-router-dom'
import { sessionsApi, booksApi, integrationsApi, ReadingSession, Book } from '../services/api'
import { BookOpen, Clock, Search } from 'lucide-react'

const moods = ['relaxed', 'focused', 'curious', 'stressed', 'excited', 'calm']

export default function Log() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedBook, setSelectedBook] = useState<Book | null>(
    location.state?.bookId ? { id: location.state.bookId } as Book : null
  )
  const [duration, setDuration] = useState<string>('')
  const [mood, setMood] = useState<string>('')

  // Search books
  const { data: searchResults } = useQuery({
    queryKey: ['books', 'search', searchQuery],
    queryFn: () => booksApi.search(searchQuery, 10).then(res => res.data),
    enabled: searchQuery.length > 2 && !selectedBook,
  })

  // Search external APIs if no local results
  const { data: externalResults } = useQuery({
    queryKey: ['external-search', searchQuery],
    queryFn: () => integrationsApi.searchBooks(searchQuery, 'google_books', 5).then(res => res.data),
    enabled: searchQuery.length > 2 && !selectedBook && (!searchResults || searchResults.length === 0),
  })

  // Create book from external if needed
  const createBookMutation = useMutation({
    mutationFn: async (bookData: any) => {
      return booksApi.create({
        title: bookData.title,
        author: bookData.author,
        isbn: bookData.isbn,
        genre: bookData.genre,
        description: bookData.description,
        cover_image_url: bookData.cover_image_url,
        page_count: bookData.page_count,
      }).then(res => res.data)
    },
  })

  const logMutation = useMutation({
    mutationFn: async () => {
      let bookId: number
      
      if (selectedBook?.id) {
        // Existing book with ID
        bookId = selectedBook.id
      } else if (selectedBook && 'title' in selectedBook) {
        // External book, need to create it first
        const created = await createBookMutation.mutateAsync(selectedBook as any)
        bookId = created.id
      } else {
        throw new Error('Please select a book')
      }

      if (!duration) {
        throw new Error('Duration is required')
      }

      const durationNum = parseFloat(duration)
      if (isNaN(durationNum) || durationNum <= 0) {
        throw new Error('Duration must be a positive number')
      }

      return sessionsApi.create({
        book_id: bookId,
        action: 'taken',
        duration_minutes: durationNum,
        mood: mood || undefined,
        status: 'currently_reading',
      }).then(res => res.data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
      queryClient.invalidateQueries({ queryKey: ['statistics'] })
      queryClient.invalidateQueries({ queryKey: ['preferences'] })
      navigate('/')
    },
    onError: (error: any) => {
      console.error('Failed to log reading:', error)
      alert(error?.response?.data?.detail || error?.message || 'Failed to log reading. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    logMutation.mutate()
  }

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <h1 className="text-2xl font-light text-gray-900 mb-8 text-center">
        What just happened?
      </h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Book Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Book
          </label>
          {!selectedBook ? (
            <>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search for a book..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              
              {/* Search Results */}
              {(searchResults && searchResults.length > 0) && (
                <div className="mt-2 border border-gray-200 rounded-lg max-h-48 overflow-y-auto">
                  {searchResults.map((book) => (
                    <button
                      key={book.id}
                      type="button"
                      onClick={() => setSelectedBook(book)}
                      className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{book.title}</div>
                      {book.author && (
                        <div className="text-sm text-gray-600">by {book.author}</div>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* External Results */}
              {(externalResults?.books && externalResults.books.length > 0) && (
                <div className="mt-2 border border-gray-200 rounded-lg max-h-48 overflow-y-auto">
                  {externalResults.books.map((book: any, idx: number) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        // Ensure book has required fields
                        setSelectedBook({
                          title: book.title,
                          author: book.authors?.[0] || book.author || 'Unknown',
                          isbn: book.isbn || book.isbn13 || book.industryIdentifiers?.[0]?.identifier,
                          genre: book.categories?.[0] || book.genre,
                          description: book.description,
                          cover_image_url: book.imageLinks?.thumbnail || book.thumbnail || book.cover_image_url,
                          page_count: book.pageCount || book.page_count,
                        })
                      }}
                      className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{book.title}</div>
                      <div className="text-sm text-gray-600">
                        by {book.authors?.[0] || book.author || 'Unknown'}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900">{selectedBook.title}</div>
                {selectedBook.author && (
                  <div className="text-sm text-gray-600">by {selectedBook.author}</div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedBook(null)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Change
              </button>
            </div>
          )}
        </div>

        {/* Duration (Required) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Duration (minutes) <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <Clock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="30"
              required
              min="1"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>

        {/* Mood (Optional) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Mood (optional)
          </label>
          <select
            value={mood}
            onChange={(e) => setMood(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">None</option>
            {moods.map(m => (
              <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
            ))}
          </select>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={logMutation.isPending || !selectedBook || !duration}
          className="w-full px-4 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {logMutation.isPending ? 'Logging...' : 'Log Reading'}
        </button>
      </form>
    </div>
  )
}


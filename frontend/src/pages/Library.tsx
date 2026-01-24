/**
 * Library - A quiet space for books you're in relationship with
 */
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { booksApi, preferencesApi, sessionsApi, recommendationsApi } from '../services/api'
import { BookPreference } from '../services/api'
import './library.css'

export default function Library() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  // Get all preferences
  const { data: preferences } = useQuery({
    queryKey: ['preferences'],
    queryFn: () => preferencesApi.getAll().then(res => res.data),
  })

  // Get book IDs with sessions
  const { data: bookIdsData } = useQuery({
    queryKey: ['sessions', 'book-ids'],
    queryFn: () => sessionsApi.getBookIds().then(res => res.data.book_ids || []),
  })

  // Get all books - fetch by IDs from both sessions and preferences
  const { data: allBooks } = useQuery({
    queryKey: ['books', 'all', bookIdsData, preferences],
    queryFn: async () => {
      const allRelevantBookIds = new Set<number>();
      
      // Add book IDs from sessions
      if (bookIdsData) {
        bookIdsData.forEach(id => allRelevantBookIds.add(id));
      }
      
      // Add book IDs from preferences
      if (preferences) {
        preferences.forEach(pref => allRelevantBookIds.add(pref.book_id));
      }
      
      if (allRelevantBookIds.size === 0) return [];
      
      // Fetch books by their IDs for efficiency
      return booksApi.getByIds(Array.from(allRelevantBookIds)).then(res => res.data)
    },
    enabled: !!bookIdsData && !!preferences, // Wait for both to be available
  })

  // Get recent sessions for last activity
  const { data: recentSessions } = useQuery({
    queryKey: ['sessions', 'recent'],
    queryFn: () => sessionsApi.getAll({ limit: 100 }).then(res => res.data),
  })

  const queryClient = useQueryClient()
  const [recommendationData, setRecommendationData] = useState<any>(null)
  const [isThinking, setIsThinking] = useState(false)
  const [thinkingMessage, setThinkingMessage] = useState<string>('')

  // Load stored recommendation from database on mount (no LLM call)
  const { data: storedRecommendation } = useQuery({
    queryKey: ['recommendation', 'stored'],
    queryFn: async () => {
      const response = await recommendationsApi.getQuick({ refresh: false }).then(res => res.data)
      // Only return if there's a strong recommendation with book data and reason
      if (response.recommendation && response.recommendation.book && response.recommendation.reason) {
        return response.recommendation
      }
      return null
    },
    refetchOnWindowFocus: false,
    retry: 1,
  })

  // Update state when stored recommendation loads
  useEffect(() => {
    if (storedRecommendation) {
      setRecommendationData(storedRecommendation)
    }
  }, [storedRecommendation])

  // Fetch new recommendation with agentic thinking states (calls LLM)
  const fetchNewRecommendation = async () => {
    setIsThinking(true)
    setThinkingMessage('Considering your reading patterns...')
    
    try {
      // Simulate thinking phases
      const thinkingPhases = [
        { delay: 800, message: 'Analyzing your recent activity...' },
        { delay: 1000, message: 'Matching books to your current context...' },
        { delay: 600, message: 'Selecting the best match...' },
      ]

      for (const phase of thinkingPhases) {
        await new Promise(resolve => setTimeout(resolve, phase.delay))
        setThinkingMessage(phase.message)
      }

      const response = await recommendationsApi.getQuick({ refresh: true }).then(res => res.data)
      
      if (response.recommendation && response.recommendation.book && response.recommendation.reason) {
        setRecommendationData(response.recommendation)
        // Invalidate stored recommendation query to refresh cache
        queryClient.invalidateQueries({ queryKey: ['recommendation', 'stored'] })
      } else {
        setRecommendationData(null)
      }
    } catch (error) {
      console.error('Failed to get recommendation:', error)
      setThinkingMessage('Unable to generate recommendation')
    } finally {
      setIsThinking(false)
      setThinkingMessage('')
    }
  }

  // Build book list with status and last activity
  const booksWithStatus = (() => {
    if (!allBooks) return []
    
    const preferenceMap = new Map<number, BookPreference>()
    if (preferences) {
      preferences.forEach(pref => preferenceMap.set(pref.book_id, pref))
    }
    
    const sessionMap = new Map<number, any>()
    recentSessions?.forEach(session => {
      const existing = sessionMap.get(session.book_id)
      if (!existing || new Date(session.timestamp) > new Date(existing.timestamp)) {
        sessionMap.set(session.book_id, session)
      }
    })

    // Get recommendation book ID to exclude it from regular sections
    const recommendationBookId = recommendationData?.book_id || recommendationData?.book?.id
    const recommendationTitle = recommendationData?.book?.title?.toLowerCase().trim()
    const recommendationAuthor = recommendationData?.book?.author?.toLowerCase().trim()

    // Deduplicate by book ID and exclude recommendation
    const seenBookIds = new Set<number>()
    const seenBookKeys = new Set<string>() // For title+author deduplication
    
    if (recommendationBookId) {
      seenBookIds.add(recommendationBookId)
    }
    if (recommendationTitle && recommendationAuthor) {
      seenBookKeys.add(`${recommendationTitle}|${recommendationAuthor}`)
    }

    return allBooks
      .filter(book => {
        // Skip if we've already seen this book ID
        if (seenBookIds.has(book.id)) {
          return false
        }
        
        // Skip if this is the recommendation book (by title+author match)
        if (recommendationTitle && recommendationAuthor) {
          const bookTitle = book.title?.toLowerCase().trim()
          const bookAuthor = book.author?.toLowerCase().trim()
          if (bookTitle === recommendationTitle && bookAuthor === recommendationAuthor) {
            return false
          }
        }
        
        // Deduplicate by title+author (handle duplicate book entries)
        const bookKey = `${book.title?.toLowerCase().trim()}|${book.author?.toLowerCase().trim()}`
        if (seenBookKeys.has(bookKey)) {
          return false
        }
        
        seenBookIds.add(book.id)
        seenBookKeys.add(bookKey)
        return true
      })
      .map(book => {
        const pref = preferenceMap.get(book.id)
        const lastSession = sessionMap.get(book.id)
        return {
          book,
          status: pref?.status || (lastSession?.status || 'none'),
          lastActivity: lastSession?.timestamp,
          preference: pref,
          session: lastSession,
        }
      })
      .sort((a, b) => {
        // Sort by last activity (most recent first)
        if (a.lastActivity && b.lastActivity) {
          return new Date(b.lastActivity).getTime() - new Date(a.lastActivity).getTime()
        }
        if (a.lastActivity) return -1
        if (b.lastActivity) return 1
        return 0
      })
  })()

  // Filter books based on status filter
  const filteredBooks = statusFilter 
    ? booksWithStatus.filter(item => {
        if (statusFilter === 'reading') return item.status === 'currently_reading'
        if (statusFilter === 'paused') return item.status === 'paused'
        if (statusFilter === 'finished') return item.status === 'read'
        if (statusFilter === 'want_to_read') return item.status === 'want_to_read'
        return true
      })
    : booksWithStatus

  // Group filtered books
  const filteredByStatus = {
    reading: filteredBooks.filter(item => item.status === 'currently_reading'),
    paused: filteredBooks.filter(item => item.status === 'paused'),
    finished: filteredBooks.filter(item => item.status === 'read'),
    wantToRead: filteredBooks.filter(item => item.status === 'want_to_read'),
  }

  // Parse recommendation reason to extract a calm sentence
  const getRecommendationReason = (reason?: string): string | null => {
    if (!reason) return null
    
    try {
      const parsed = JSON.parse(reason)
      if (typeof parsed === 'object' && parsed !== null) {
        // Prefer explanation if available, otherwise use primary_signal
        return parsed.explanation || parsed.primary_signal || null
      }
    } catch {
      // If parsing fails, treat as plain string
      return reason
    }
    return null
  }

  const recommendationReason = recommendationData?.reason 
    ? getRecommendationReason(recommendationData.reason)
    : null

  return (
    <div className="library-root">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="library-filters mb-8">
          <button
            onClick={() => setStatusFilter(null)}
            className={`library-filter ${statusFilter === null ? 'library-filter-active' : ''}`}
          >
            All
          </button>
          <button
            onClick={() => setStatusFilter('reading')}
            className={`library-filter ${statusFilter === 'reading' ? 'library-filter-active' : ''}`}
          >
            Reading
          </button>
          <button
            onClick={() => setStatusFilter('paused')}
            className={`library-filter ${statusFilter === 'paused' ? 'library-filter-active' : ''}`}
          >
            Paused
          </button>
          <button
            onClick={() => setStatusFilter('finished')}
            className={`library-filter ${statusFilter === 'finished' ? 'library-filter-active' : ''}`}
          >
            Finished
          </button>
          <button
            onClick={() => setStatusFilter('want_to_read')}
            className={`library-filter ${statusFilter === 'want_to_read' ? 'library-filter-active' : ''}`}
          >
            Want to Read
          </button>
        </div>

        {/* Recommendation at the top */}
        {(recommendationData || isThinking) && (
          <div className="library-recommendation-top mb-10">
            <div className="library-recommendation-card">
              <div className="library-recommendation-content">
                <div className="library-recommendation-header">
                  <span className="library-recommendation-label">
                    {isThinking ? 'Thinking...' : 'Suggested'}
                  </span>
                  {!isThinking && (
                    <button
                      onClick={fetchNewRecommendation}
                      className="library-recommendation-refresh"
                      title="Get a new recommendation"
                    >
                      ↻
                    </button>
                  )}
                </div>
                {isThinking ? (
                  <div className="library-recommendation-thinking">
                    <div className="library-recommendation-thinking-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <p className="library-recommendation-thinking-message">{thinkingMessage}</p>
                  </div>
                ) : recommendationData && recommendationData.book ? (
                  <>
                    <h3 className="library-recommendation-title">
                      {recommendationData.book.title}
                    </h3>
                    {recommendationData.book.author && (
                      <p className="library-recommendation-author">by {recommendationData.book.author}</p>
                    )}
                    {recommendationReason && (
                      <p className="library-recommendation-reason">{recommendationReason}</p>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          </div>
        )}
        
        {/* Show refresh button if no recommendation exists */}
        {!recommendationData && !isThinking && (
          <div className="library-recommendation-top mb-10">
            <button
              onClick={fetchNewRecommendation}
              className="library-recommendation-get-button"
            >
              Get a recommendation
            </button>
          </div>
        )}

        {/* Books List - Sectioned by spacing */}
        <div>
          {/* Reading now - closest to top, tighter spacing */}
          {filteredByStatus.reading.length > 0 && (
            <section className="library-section library-section-reading mb-8">
              <div>
                {filteredByStatus.reading.map(({ book, preference, session, lastActivity, status }) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    preference={preference}
                    session={session}
                    lastActivity={lastActivity}
                    status={status}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Paused - more vertical spacing */}
          {filteredByStatus.paused.length > 0 && (
            <section className="library-section library-section-paused mb-16">
              <div>
                {filteredByStatus.paused.map(({ book, preference, session, lastActivity, status }) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    preference={preference}
                    session={session}
                    lastActivity={lastActivity}
                    status={status}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Finished - most spaced out, visually quieter */}
          {filteredByStatus.finished.length > 0 && (
            <section className="library-section library-section-finished mb-16">
              <div>
                {filteredByStatus.finished.map(({ book, preference, session, lastActivity, status }) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    preference={preference}
                    session={session}
                    lastActivity={lastActivity}
                    status={status}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Want to Read - at the bottom, quietest */}
          {filteredByStatus.wantToRead.length > 0 && (
            <section className="library-section library-section-want-to-read">
              <div>
                {filteredByStatus.wantToRead.map(({ book, preference, session, lastActivity, status }) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    preference={preference}
                    session={session}
                    lastActivity={lastActivity}
                    status={status}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

interface BookCardProps {
  book: any
  preference?: BookPreference
  session?: any
  lastActivity?: string
  status?: string
}

function BookCard({ book, preference, session, lastActivity, status }: BookCardProps) {
  const [showStatusMenu, setShowStatusMenu] = useState(false)
  const queryClient = useQueryClient()
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowStatusMenu(false)
      }
    }
    
    if (showStatusMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showStatusMenu])
  
  // Get tags from preference or session
  const tags = preference?.tags || session?.tags || []
  
  // Format last activity
  const formatLastActivity = (timestamp?: string) => {
    if (!timestamp) return null
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const statusLabel = status === 'currently_reading' ? 'Reading' 
    : status === 'paused' ? 'Paused'
    : status === 'read' ? 'Finished'
    : status === 'want_to_read' ? 'Want to Read'
    : null

  const statusOptions = [
    { value: 'currently_reading', label: 'Reading' },
    { value: 'paused', label: 'Paused' },
    { value: 'read', label: 'Finished' },
    { value: 'want_to_read', label: 'Want to Read' },
    { value: null, label: 'None' },
  ]

  const updateStatusMutation = useMutation({
    mutationFn: async (newStatus: string | null) => {
      return preferencesApi.createOrUpdate(book.id, { status: newStatus })
    },
    onSuccess: () => {
      // Invalidate queries to refresh the library
      queryClient.invalidateQueries({ queryKey: ['preferences'] })
      queryClient.invalidateQueries({ queryKey: ['books', 'all'] })
      queryClient.invalidateQueries({ queryKey: ['sessions', 'recent'] })
      setShowStatusMenu(false)
    },
  })

  const handleStatusChange = (newStatus: string | null) => {
    updateStatusMutation.mutate(newStatus)
  }

  return (
    <div className="library-card">
      <div className="library-card-content">
        <h3 className="library-card-title">
          {book.title}
        </h3>
        {book.author && (
          <p className="library-card-author">by {book.author}</p>
        )}
        {tags && tags.length > 0 && (
          <div className="library-card-tags">
            {tags.map((tag: string, idx: number) => (
              <span key={idx} className="library-card-tag">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="library-card-metadata">
          <div className="library-card-status-container" ref={menuRef}>
            {statusLabel ? (
              <button
                onClick={() => setShowStatusMenu(!showStatusMenu)}
                className="library-card-status-button"
                data-status={status || 'none'}
                disabled={updateStatusMutation.isPending}
              >
                {statusLabel}
              </button>
            ) : (
              <button
                onClick={() => setShowStatusMenu(!showStatusMenu)}
                className="library-card-status-button library-card-status-button-empty"
                disabled={updateStatusMutation.isPending}
              >
                Set status
              </button>
            )}
            {showStatusMenu && (
              <div className="library-card-status-menu">
                {statusOptions.map((option) => (
                  <button
                    key={option.value || 'none'}
                    onClick={() => handleStatusChange(option.value)}
                    data-status={option.value || 'none'}
                    className={`library-card-status-option ${
                      status === option.value ? 'library-card-status-option-active' : ''
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          {lastActivity && (
            <span className="library-card-activity">{formatLastActivity(lastActivity)}</span>
          )}
        </div>
      </div>
    </div>
  )
}


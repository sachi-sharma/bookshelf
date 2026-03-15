import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import BookCard from '../components/BookCard';
import EmptyState from '../components/EmptyState';
import { booksApi, preferencesApi } from '../services/api';
import type { Book, ReadingStatus } from '../types';

const QUICK_STATUSES: { key: ReadingStatus; label: string; color: string }[] = [
  { key: 'want_to_read', label: 'Want to Read', color: '#43b89c' },
  { key: 'currently_reading', label: 'Reading', color: '#6c63ff' },
];

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Book[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [addingId, setAddingId] = useState<number | null>(null);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      // Try local first, then external
      let books = await booksApi.search(query.trim());
      if (!books.length) {
        books = await booksApi.searchExternal(query.trim());
      }
      setResults(books);
    } catch {
      Alert.alert('Search failed', 'Could not reach the backend. Is it running?');
    } finally {
      setLoading(false);
    }
  }, [query]);

  const addToLibrary = useCallback(async (book: Book, status: ReadingStatus) => {
    setAddingId(book.id);
    try {
      await preferencesApi.upsert(book.id, { status });
      Alert.alert(
        'Added!',
        `"${book.title}" added to your library as "${status.replace(/_/g, ' ')}".`,
      );
    } catch {
      Alert.alert('Error', 'Could not add book to your library.');
    } finally {
      setAddingId(null);
    }
  }, []);

  return (
    <View style={styles.container}>
      {/* Search bar */}
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder="Search books by title or author…"
          placeholderTextColor="#bbb"
          returnKeyType="search"
          onSubmitEditing={search}
        />
        <TouchableOpacity style={styles.searchBtn} onPress={search} disabled={loading}>
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.searchBtnText}>Search</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Results */}
      <ScrollView style={styles.list} contentContainerStyle={styles.listContent}>
        {!searched && (
          <EmptyState
            icon="🔍"
            title="Find your next book"
            subtitle="Search by title or author to add books to your library"
          />
        )}
        {searched && !loading && !results.length && (
          <EmptyState
            icon="😕"
            title="No books found"
            subtitle={`No results for "${query}"`}
          />
        )}
        {results.map((book) => (
          <View key={book.id}>
            <BookCard
              book={book}
              subtitle={
                [book.genre, book.page_count ? `${book.page_count} pages` : null]
                  .filter(Boolean)
                  .join(' · ') || undefined
              }
            />
            <View style={styles.actionRow}>
              {QUICK_STATUSES.map((s) => (
                <TouchableOpacity
                  key={s.key}
                  style={[styles.actionBtn, { borderColor: s.color }]}
                  onPress={() => addToLibrary(book, s.key)}
                  disabled={addingId === book.id}
                >
                  {addingId === book.id ? (
                    <ActivityIndicator size="small" color={s.color} />
                  ) : (
                    <Text style={[styles.actionBtnText, { color: s.color }]}>
                      + {s.label}
                    </Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f9' },
  searchBar: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    gap: 8,
    alignItems: 'center',
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#f5f5f9',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: '#1a1a2e',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  searchBtn: {
    backgroundColor: '#6c63ff',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
    minWidth: 70,
    alignItems: 'center',
  },
  searchBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  list: { flex: 1 },
  listContent: { padding: 16, paddingBottom: 32 },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: -6,
    marginBottom: 14,
  },
  actionBtn: {
    flex: 1,
    borderWidth: 1.5,
    borderRadius: 8,
    paddingVertical: 7,
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  actionBtnText: { fontSize: 12, fontWeight: '600' },
});

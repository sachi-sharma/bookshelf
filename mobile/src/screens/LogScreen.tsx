import React, { useCallback, useEffect, useState } from 'react';
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
import { sessionsApi, preferencesApi, booksApi } from '../services/api';
import type { Book, Mood, Location, ReadingSession, ReadingStatus } from '../types';

const MOODS: Mood[] = ['focused', 'relaxed', 'curious', 'tired', 'energized', 'sad', 'happy'];
const MOOD_EMOJIS: Record<Mood, string> = {
  focused: '🎯',
  relaxed: '😌',
  curious: '🤔',
  tired: '😴',
  energized: '⚡',
  sad: '😢',
  happy: '😊',
};
const LOCATIONS: Location[] = ['home', 'commute', 'cafe', 'library', 'outdoors', 'other'];
const LOCATION_EMOJIS: Record<Location, string> = {
  home: '🏠',
  commute: '🚌',
  cafe: '☕',
  library: '🏛️',
  outdoors: '🌳',
  other: '📍',
};
const STATUSES: { key: ReadingStatus; label: string }[] = [
  { key: 'currently_reading', label: 'Reading' },
  { key: 'want_to_read', label: 'Want to Read' },
  { key: 'read', label: 'Finished' },
  { key: 'abandoned', label: 'Abandoned' },
];

export default function LogScreen() {
  const [myBooks, setMyBooks] = useState<Book[]>([]);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [duration, setDuration] = useState('');
  const [pages, setPages] = useState('');
  const [mood, setMood] = useState<Mood | null>(null);
  const [location, setLocation] = useState<Location | null>(null);
  const [status, setStatus] = useState<ReadingStatus>('currently_reading');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [recentSessions, setRecentSessions] = useState<ReadingSession[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [prefs, sessions] = await Promise.all([
        preferencesApi.getAll(),
        sessionsApi.getAll({ limit: 5 }),
      ]);
      setMyBooks(prefs.map((p) => p.book).filter(Boolean) as Book[]);
      setRecentSessions(sessions);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = useCallback(async () => {
    if (!selectedBook) {
      Alert.alert('Select a book', 'Please choose which book you read.');
      return;
    }
    setSubmitting(true);
    try {
      await sessionsApi.create({
        book_id: selectedBook.id,
        action: 'taken',
        duration_minutes: duration ? parseInt(duration, 10) : undefined,
        pages_read: pages ? parseInt(pages, 10) : undefined,
        mood: mood ?? undefined,
        location: location ?? undefined,
        notes: notes || undefined,
        status,
      });
      // Update preference status too
      await preferencesApi.upsert(selectedBook.id, { status });
      Alert.alert('Session logged!', `Logged reading for "${selectedBook.title}".`);
      setDuration('');
      setPages('');
      setNotes('');
      setMood(null);
      setLocation(null);
      await loadData();
    } catch {
      Alert.alert('Error', 'Could not log session. Is the backend running?');
    } finally {
      setSubmitting(false);
    }
  }, [selectedBook, duration, pages, mood, location, notes, status, loadData]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Log a Reading Session</Text>

      {/* Book picker */}
      <Text style={styles.label}>Book</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.bookPicker}
        contentContainerStyle={styles.bookPickerContent}
      >
        {myBooks.length === 0 && (
          <Text style={styles.emptyHint}>No books in your library yet.</Text>
        )}
        {myBooks.map((book) => (
          <TouchableOpacity
            key={book.id}
            style={[styles.bookChip, selectedBook?.id === book.id && styles.bookChipActive]}
            onPress={() => setSelectedBook(book)}
          >
            <Text
              style={[styles.bookChipText, selectedBook?.id === book.id && styles.bookChipTextActive]}
              numberOfLines={2}
            >
              {book.title}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Duration & pages */}
      <View style={styles.row}>
        <View style={styles.halfInput}>
          <Text style={styles.label}>Minutes read</Text>
          <TextInput
            style={styles.input}
            value={duration}
            onChangeText={setDuration}
            keyboardType="number-pad"
            placeholder="e.g. 30"
            placeholderTextColor="#bbb"
          />
        </View>
        <View style={[styles.halfInput, { marginLeft: 10 }]}>
          <Text style={styles.label}>Pages read</Text>
          <TextInput
            style={styles.input}
            value={pages}
            onChangeText={setPages}
            keyboardType="number-pad"
            placeholder="e.g. 25"
            placeholderTextColor="#bbb"
          />
        </View>
      </View>

      {/* Mood */}
      <Text style={styles.label}>Mood</Text>
      <View style={styles.chipRow}>
        {MOODS.map((m) => (
          <TouchableOpacity
            key={m}
            style={[styles.chip, mood === m && styles.chipActive]}
            onPress={() => setMood(mood === m ? null : m)}
          >
            <Text style={styles.chipEmoji}>{MOOD_EMOJIS[m]}</Text>
            <Text style={[styles.chipText, mood === m && styles.chipTextActive]}>{m}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Location */}
      <Text style={styles.label}>Where did you read?</Text>
      <View style={styles.chipRow}>
        {LOCATIONS.map((loc) => (
          <TouchableOpacity
            key={loc}
            style={[styles.chip, location === loc && styles.chipActive]}
            onPress={() => setLocation(location === loc ? null : loc)}
          >
            <Text style={styles.chipEmoji}>{LOCATION_EMOJIS[loc]}</Text>
            <Text style={[styles.chipText, location === loc && styles.chipTextActive]}>{loc}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Status */}
      <Text style={styles.label}>Reading status</Text>
      <View style={styles.chipRow}>
        {STATUSES.map((s) => (
          <TouchableOpacity
            key={s.key}
            style={[styles.chip, status === s.key && styles.chipActive]}
            onPress={() => setStatus(s.key)}
          >
            <Text style={[styles.chipText, status === s.key && styles.chipTextActive]}>
              {s.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Notes */}
      <Text style={styles.label}>Notes (optional)</Text>
      <TextInput
        style={[styles.input, styles.notesInput]}
        value={notes}
        onChangeText={setNotes}
        placeholder="Any thoughts on what you read…"
        placeholderTextColor="#bbb"
        multiline
        numberOfLines={3}
      />

      {/* Submit */}
      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        {submitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitBtnText}>Log Session</Text>
        )}
      </TouchableOpacity>

      {/* Recent sessions */}
      {recentSessions.length > 0 && (
        <>
          <Text style={[styles.heading, { marginTop: 28, fontSize: 17 }]}>Recent Sessions</Text>
          {recentSessions.map((session) => (
            <View key={session.id} style={styles.sessionCard}>
              <Text style={styles.sessionTitle}>
                {session.book?.title ?? `Book #${session.book_id}`}
              </Text>
              <Text style={styles.sessionMeta}>
                {session.duration_minutes ? `${session.duration_minutes} min` : ''}
                {session.mood ? `  •  ${MOOD_EMOJIS[session.mood as Mood] ?? ''} ${session.mood}` : ''}
                {session.location
                  ? `  •  ${LOCATION_EMOJIS[session.location as Location] ?? ''} ${session.location}`
                  : ''}
              </Text>
              {session.notes ? (
                <Text style={styles.sessionNotes} numberOfLines={2}>
                  {session.notes}
                </Text>
              ) : null}
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f9' },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 20, fontWeight: '800', color: '#1a1a2e', marginBottom: 14 },
  label: { fontSize: 13, fontWeight: '600', color: '#555', marginBottom: 6, marginTop: 14 },
  row: { flexDirection: 'row' },
  halfInput: { flex: 1 },
  input: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    color: '#1a1a2e',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  notesInput: { minHeight: 80, textAlignVertical: 'top' },
  bookPicker: { marginBottom: 4 },
  bookPickerContent: { paddingRight: 16, gap: 8 },
  bookChip: {
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1.5,
    borderColor: '#e0e0e0',
    maxWidth: 140,
    minWidth: 80,
  },
  bookChipActive: { borderColor: '#6c63ff', backgroundColor: '#6c63ff11' },
  bookChipText: { fontSize: 12, color: '#444', fontWeight: '500' },
  bookChipTextActive: { color: '#6c63ff', fontWeight: '700' },
  emptyHint: { fontSize: 13, color: '#bbb', paddingVertical: 10 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderWidth: 1.5,
    borderColor: '#e0e0e0',
    gap: 4,
  },
  chipActive: { borderColor: '#6c63ff', backgroundColor: '#6c63ff11' },
  chipEmoji: { fontSize: 14 },
  chipText: { fontSize: 12, color: '#555', fontWeight: '500' },
  chipTextActive: { color: '#6c63ff', fontWeight: '700' },
  submitBtn: {
    backgroundColor: '#6c63ff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  sessionCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  sessionTitle: { fontSize: 14, fontWeight: '600', color: '#1a1a2e', marginBottom: 3 },
  sessionMeta: { fontSize: 12, color: '#888' },
  sessionNotes: { fontSize: 12, color: '#aaa', marginTop: 4, fontStyle: 'italic' },
});

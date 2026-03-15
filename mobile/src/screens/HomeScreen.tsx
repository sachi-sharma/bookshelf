import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import StatCard from '../components/StatCard';
import BookCard from '../components/BookCard';
import SectionHeader from '../components/SectionHeader';
import { recommendationsApi, sessionsApi } from '../services/api';
import type { QuickRecommendation, ReadingStats } from '../types';

export default function HomeScreen() {
  const [stats, setStats] = useState<ReadingStats | null>(null);
  const [recommendation, setRecommendation] = useState<QuickRecommendation | null>(null);
  const [loadingRec, setLoadingRec] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const data = await sessionsApi.getStats();
      setStats(data);
    } catch {
      // stats are optional; silently fail
    }
  }, []);

  const loadRecommendation = useCallback(async () => {
    setLoadingRec(true);
    setError(null);
    try {
      const data = await recommendationsApi.getQuick();
      setRecommendation(data);
    } catch {
      setError('Could not load recommendation. Is the backend running?');
    } finally {
      setLoadingRec(false);
    }
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([loadStats(), loadRecommendation()]);
    setRefreshing(false);
  }, [loadStats, loadRecommendation]);

  useEffect(() => {
    loadStats();
    loadRecommendation();
  }, [loadStats, loadRecommendation]);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Good reading 📚</Text>
        <Text style={styles.tagline}>Your personal reading companion</Text>
      </View>

      {/* Stats row */}
      {stats && (
        <>
          <SectionHeader title="Your Reading" />
          <View style={styles.statsRow}>
            <StatCard label="Sessions" value={stats.total_sessions} color="#6c63ff" />
            <StatCard label="Books Read" value={stats.books_read} color="#ff6584" />
            <StatCard
              label="Avg (min)"
              value={Math.round(stats.average_session_duration)}
              color="#43b89c"
            />
          </View>
        </>
      )}

      {/* Recommendation */}
      <SectionHeader title="What to Read Now" />
      {loadingRec ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6c63ff" />
          <Text style={styles.loadingText}>Thinking of something perfect…</Text>
        </View>
      ) : error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadRecommendation}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : recommendation ? (
        <View style={styles.recCard}>
          <BookCard book={recommendation.book} badge="Recommended" />
          <Text style={styles.recReason}>{recommendation.reason}</Text>
          {recommendation.context ? (
            <Text style={styles.recContext}>{recommendation.context}</Text>
          ) : null}
          <TouchableOpacity style={styles.refreshBtn} onPress={loadRecommendation}>
            <Text style={styles.refreshBtnText}>↻  Suggest another</Text>
          </TouchableOpacity>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f9' },
  content: { padding: 16, paddingBottom: 32 },
  header: { marginBottom: 4 },
  greeting: { fontSize: 26, fontWeight: '800', color: '#1a1a2e' },
  tagline: { fontSize: 13, color: '#888', marginTop: 2 },
  statsRow: { flexDirection: 'row', marginBottom: 4 },
  center: { alignItems: 'center', paddingVertical: 32 },
  loadingText: { marginTop: 12, color: '#888', fontSize: 14 },
  errorBox: {
    backgroundColor: '#fff0f0',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  errorText: { color: '#c0392b', fontSize: 13, textAlign: 'center', marginBottom: 10 },
  retryBtn: {
    backgroundColor: '#6c63ff',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
  },
  retryText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  recCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  recReason: {
    fontSize: 13,
    color: '#444',
    lineHeight: 18,
    marginTop: 6,
  },
  recContext: {
    fontSize: 12,
    color: '#aaa',
    marginTop: 4,
    fontStyle: 'italic',
  },
  refreshBtn: {
    marginTop: 12,
    alignSelf: 'center',
    paddingHorizontal: 20,
    paddingVertical: 8,
    backgroundColor: '#6c63ff11',
    borderRadius: 20,
  },
  refreshBtnText: {
    color: '#6c63ff',
    fontWeight: '600',
    fontSize: 13,
  },
});

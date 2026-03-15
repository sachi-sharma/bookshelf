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
import BookCard from '../components/BookCard';
import SectionHeader from '../components/SectionHeader';
import EmptyState from '../components/EmptyState';
import { preferencesApi } from '../services/api';
import type { BookPreference, ReadingStatus } from '../types';

const STATUS_TABS: { key: ReadingStatus | 'all'; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'currently_reading', label: 'Reading' },
  { key: 'want_to_read', label: 'Want to Read' },
  { key: 'read', label: 'Finished' },
  { key: 'abandoned', label: 'Abandoned' },
];

const STATUS_COLORS: Record<ReadingStatus, string> = {
  currently_reading: '#6c63ff',
  want_to_read: '#43b89c',
  read: '#ff6584',
  abandoned: '#aaa',
};

const STATUS_LABELS: Record<ReadingStatus, string> = {
  currently_reading: 'Reading',
  want_to_read: 'Want to read',
  read: 'Finished',
  abandoned: 'Abandoned',
};

export default function LibraryScreen() {
  const [prefs, setPrefs] = useState<BookPreference[]>([]);
  const [activeTab, setActiveTab] = useState<ReadingStatus | 'all'>('all');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await preferencesApi.getAll();
      setPrefs(data);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered =
    activeTab === 'all'
      ? prefs
      : prefs.filter((p) => p.status === activeTab);

  const grouped = {
    currently_reading: prefs.filter((p) => p.status === 'currently_reading'),
    want_to_read: prefs.filter((p) => p.status === 'want_to_read'),
    read: prefs.filter((p) => p.status === 'read'),
    abandoned: prefs.filter((p) => p.status === 'abandoned'),
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6c63ff" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Status tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.tabBar}
        contentContainerStyle={styles.tabBarContent}
      >
        {STATUS_TABS.map((tab) => {
          const count =
            tab.key === 'all'
              ? prefs.length
              : grouped[tab.key as ReadingStatus]?.length ?? 0;
          return (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tab, activeTab === tab.key && styles.tabActive]}
              onPress={() => setActiveTab(tab.key)}
            >
              <Text
                style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}
              >
                {tab.label}
              </Text>
              {count > 0 && (
                <View style={[styles.tabCount, activeTab === tab.key && styles.tabCountActive]}>
                  <Text style={[styles.tabCountText, activeTab === tab.key && styles.tabCountTextActive]}>
                    {count}
                  </Text>
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Book list */}
      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {activeTab === 'all' ? (
          <>
            {(Object.keys(grouped) as ReadingStatus[]).map((status) => {
              const books = grouped[status];
              if (!books.length) return null;
              return (
                <View key={status}>
                  <SectionHeader title={STATUS_LABELS[status]} count={books.length} />
                  {books.map((pref) =>
                    pref.book ? (
                      <BookCard
                        key={pref.id}
                        book={pref.book}
                        badge={STATUS_LABELS[status]}
                        badgeColor={STATUS_COLORS[status]}
                        subtitle={pref.rating ? `★ ${pref.rating}/5` : undefined}
                      />
                    ) : null,
                  )}
                </View>
              );
            })}
            {!prefs.length && (
              <EmptyState
                icon="📚"
                title="Your library is empty"
                subtitle="Log a reading session to add books to your library"
              />
            )}
          </>
        ) : (
          <>
            {filtered.map((pref) =>
              pref.book ? (
                <BookCard
                  key={pref.id}
                  book={pref.book}
                  badge={STATUS_LABELS[pref.status]}
                  badgeColor={STATUS_COLORS[pref.status]}
                  subtitle={pref.rating ? `★ ${pref.rating}/5` : undefined}
                />
              ) : null,
            )}
            {!filtered.length && (
              <EmptyState
                icon="🔍"
                title="Nothing here yet"
                subtitle={`No books marked as "${STATUS_TABS.find((t) => t.key === activeTab)?.label}"`}
              />
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f9' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tabBar: {
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    maxHeight: 52,
  },
  tabBarContent: {
    paddingHorizontal: 12,
    alignItems: 'center',
    gap: 8,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 20,
    gap: 6,
  },
  tabActive: { backgroundColor: '#6c63ff' },
  tabText: { fontSize: 13, fontWeight: '500', color: '#666' },
  tabTextActive: { color: '#fff', fontWeight: '700' },
  tabCount: {
    backgroundColor: '#eee',
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 1,
  },
  tabCountActive: { backgroundColor: '#ffffff44' },
  tabCountText: { fontSize: 11, fontWeight: '600', color: '#666' },
  tabCountTextActive: { color: '#fff' },
  list: { flex: 1 },
  listContent: { padding: 16, paddingBottom: 32 },
});

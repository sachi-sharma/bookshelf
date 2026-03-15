# Bookshelf Mobile App

A React Native / Expo mobile companion for the Bookshelf smart reading tracker.

## Features

- **Home** – AI-powered "What to read now?" recommendation + reading stats
- **Library** – Browse your books by status (Reading, Want to Read, Finished, Abandoned)
- **Log Session** – Record reading sessions with mood, location, duration, pages read
- **Search** – Search books locally or via Open Library / Google Books and add to your library

## Tech Stack

- [Expo](https://expo.dev) (SDK 51, file-based routing via `expo-router`)
- React Native 0.74
- TypeScript
- Axios (API client)

## Prerequisites

- Node.js 18+
- [Expo CLI](https://docs.expo.dev/get-started/installation/) or `npx expo`
- The Bookshelf backend running at `http://localhost:8000`

## Getting Started

```bash
cd mobile
npm install
npx expo start
```

Then scan the QR code with **Expo Go** on your phone, or press `a` for Android emulator / `i` for iOS simulator.

## Configuration

The API base URL is set in `src/services/api.ts`:

```ts
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

When running on a **physical device**, replace `localhost` with your machine's local IP address (e.g. `192.168.1.x`).

## Project Structure

```
mobile/
├── app/                  # Expo Router routes (tab pages)
│   ├── _layout.tsx       # Tab navigation layout
│   ├── index.tsx         # Home tab
│   ├── library.tsx       # Library tab
│   ├── log.tsx           # Log Session tab
│   └── search.tsx        # Search tab
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── BookCard.tsx
│   │   ├── StatCard.tsx
│   │   ├── SectionHeader.tsx
│   │   └── EmptyState.tsx
│   ├── screens/          # Screen implementations
│   │   ├── HomeScreen.tsx
│   │   ├── LibraryScreen.tsx
│   │   ├── LogScreen.tsx
│   │   └── SearchScreen.tsx
│   ├── services/
│   │   └── api.ts        # Axios API client
│   └── types/
│       └── index.ts      # TypeScript types
├── app.json              # Expo config
├── babel.config.js
├── package.json
└── tsconfig.json
```

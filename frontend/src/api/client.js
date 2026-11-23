// VITE_USE_FIXTURES=true answers every call below from local fixtures captured from a
// real Steam profile, so the UI can be worked on without the backend. The fixtures are
// imported lazily, so they stay out of the production bundle.
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true';
// Empty = same origin: Caddy routes /api and /auth. Set only if the API lives elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const mockMe = () => import('../data/me.json').then((m) => m.default);
const mockLibrary = () => import('../data/library.json').then((m) => m.default);

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
  });
  if (!res.ok) {
    const err = new Error(`${path} -> ${res.status}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

// undefined = still checking, null = signed out, object = signed in.
// Auth is optional site-wide — this is only used to offer a "my profile" shortcut.
export async function getMe() {
  if (USE_FIXTURES) return mockMe();
  try {
    return await request('/api/me');
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

// lookup — SteamID64 or vanity name. Throws with .status 404 if it resolves to nothing.
export async function getUser(lookup) {
  if (USE_FIXTURES) return { ...(await mockMe()).steam, visibility: 'public' };
  return request(`/api/users/${encodeURIComponent(lookup)}`);
}

// steamId — resolved SteamID64 from getUser(). Throws with .status 403 if the profile is private.
export async function getUserLibrary(steamId) {
  if (USE_FIXTURES) return mockLibrary();
  return request(`/api/users/${encodeURIComponent(steamId)}/library`);
}

// Fetches achievement counts for every owned game and returns the updated library.
// Separate from getUserLibrary because it's slow (one Steam API call per game) — triggered
// on demand by a button rather than on every profile load.
export async function refreshLibraryAchievements(steamId) {
  if (USE_FIXTURES) return mockLibrary();
  return request(`/api/users/${encodeURIComponent(steamId)}/library/achievements`, { method: 'POST' });
}

// Polled while refreshLibraryAchievements() is in flight to drive a progress bar.
export async function getAchievementsProgress(steamId) {
  if (USE_FIXTURES) return { done: 1, total: 1 };
  return request(`/api/users/${encodeURIComponent(steamId)}/library/achievements/progress`);
}

// app_id -> SteamSPY-style stats (online count, owners, review ratio) from the
// separate steamspy-service, routed by Caddy at /api/games/{app_id}.
// Returns null both when the backend isn't wired up (fixture mode) and when
// SteamSPY simply has no data for that game (404) — the caller treats both the same.
export async function getGameStats(appId) {
  if (USE_FIXTURES) return null;
  try {
    return await request(`/api/games/${encodeURIComponent(appId)}`);
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

// Global top-100-by-online-in-2-weeks list from steamspy-service, not tied to any profile.
export async function getTopGames() {
  if (USE_FIXTURES) return [];
  return request('/api/games/top');
}

// Resolves a free-text game name to app_id candidates (Steam's own store search,
// not SteamSPY — SteamSPY has no search-by-name endpoint of its own).
export async function searchGames(term) {
  if (USE_FIXTURES) return [];
  return request(`/api/games/search?q=${encodeURIComponent(term)}`);
}

export async function logout() {
  if (USE_FIXTURES) return;
  await request('/api/auth/logout', { method: 'POST' });
}

export function steamLoginUrl() {
  return USE_FIXTURES ? null : `${API_BASE}/auth/steam/login`;
}

export const isMocked = USE_FIXTURES;

import mockMe from '../data/me.json';
import mockLibrary from '../data/library.json';

// Point VITE_API_BASE_URL at the FastAPI backend once it exists (see /API_CONTRACT.md
// at the repo root). Until then every call below resolves from the local fixtures
// captured from a real Steam profile, so the UI can be built against real shapes.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

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
  if (!API_BASE) return mockMe;
  try {
    return await request('/api/me');
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

// lookup — SteamID64 or vanity name. Throws with .status 404 if it resolves to nothing.
export async function getUser(lookup) {
  if (!API_BASE) return { ...mockMe.steam, visibility: 'public' };
  return request(`/api/users/${encodeURIComponent(lookup)}`);
}

// steamId — resolved SteamID64 from getUser(). Throws with .status 403 if the profile is private.
export async function getUserLibrary(steamId) {
  if (!API_BASE) return mockLibrary;
  return request(`/api/users/${encodeURIComponent(steamId)}/library`);
}

export async function logout() {
  if (!API_BASE) return;
  await request('/api/auth/logout', { method: 'POST' });
}

export function steamLoginUrl() {
  return API_BASE ? `${API_BASE}/auth/steam/login` : null;
}

export const isMocked = !API_BASE;

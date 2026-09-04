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
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export async function getMe() {
  if (!API_BASE) return mockMe;
  return request('/api/me');
}

export async function getLibrary() {
  if (!API_BASE) return mockLibrary;
  return request('/api/library');
}

export async function logout() {
  if (!API_BASE) return;
  await request('/api/auth/logout', { method: 'POST' });
}

export function steamLoginUrl() {
  return API_BASE ? `${API_BASE}/auth/steam/login` : null;
}

export const isMocked = !API_BASE;

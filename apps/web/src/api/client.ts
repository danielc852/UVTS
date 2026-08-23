import createClient from 'openapi-fetch';

import type { paths } from './generated/schema';

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window === 'undefined' ? 'http://localhost:5173' : window.location.origin);

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  credentials: 'include',
});

export function apiUrl(path: string): string {
  return `${apiBaseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}

export const BASE_URL = import.meta.env.VITE_API_URL || '';
const API_PREFIX = '/api/v1';

const getHeaders = () => ({
  'Content-Type': 'application/json',
  'X-User-Email': 'coordinator@clinicaltrial.ai',
  'X-User-Role': 'research_coordinator',
});

function getFullUrl(endpoint: string): string {
  if (endpoint.startsWith('http')) return endpoint;
  if (endpoint.startsWith('/api/')) return `${BASE_URL}${endpoint}`;
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${BASE_URL}${API_PREFIX}${path}`;
}

export async function apiGet<T>(endpoint: string): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(getFullUrl(endpoint), {
    headers: getHeaders(),
  });
  return res.json();
}

export async function apiPost<T>(endpoint: string, body?: any): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(getFullUrl(endpoint), {
    method: 'POST',
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

export async function apiPut<T>(endpoint: string, body?: any): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(getFullUrl(endpoint), {
    method: 'PUT',
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

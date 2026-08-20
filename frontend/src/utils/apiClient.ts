const BASE_URL = '/api/v1';

const getHeaders = () => ({
  'Content-Type': 'application/json',
  'X-User-Email': 'coordinator@clinicaltrial.ai',
  'X-User-Role': 'research_coordinator',
});

export async function apiGet<T>(endpoint: string): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: getHeaders(),
  });
  return res.json();
}

export async function apiPost<T>(endpoint: string, body?: any): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

export async function apiPut<T>(endpoint: string, body?: any): Promise<{ success: boolean; data?: T; error?: string }> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

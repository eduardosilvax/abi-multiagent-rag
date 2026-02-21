// Server hook: proxy /api requests to the FastAPI backend in production.
// In dev mode, Vite handles proxying via vite.config.ts.

import type { Handle } from '@sveltejs/kit';

const API_BASE = process.env.API_BASE_URL || process.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY || process.env.VITE_API_KEY || '';

export const handle: Handle = async ({ event, resolve }) => {
  // Proxy /api/* requests to the FastAPI backend
  if (event.url.pathname.startsWith('/api/')) {
    const targetUrl = `${API_BASE}${event.url.pathname}${event.url.search}`;

    const headers = new Headers(event.request.headers);
    if (API_KEY) {
      headers.set('X-API-Key', API_KEY);
    }
    // Remove host header to avoid conflicts
    headers.delete('host');

    try {
      const response = await fetch(targetUrl, {
        method: event.request.method,
        headers,
        body: event.request.method !== 'GET' ? await event.request.text() : undefined
      });

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ detail: 'Backend API unavailable' }),
        { status: 502, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }

  return resolve(event);
};

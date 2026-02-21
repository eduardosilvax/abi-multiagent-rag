// Cliente HTTP para comunicação com a API FastAPI do ABI Smart Assistant.

import type { ChatApiRequest, ChatApiResponse, HealthResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const API_KEY  = import.meta.env.VITE_API_KEY || '';

function headers(): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return h;
}

/**
 * Envia uma pergunta ao pipeline multi-agente e retorna a resposta completa.
 */
export async function sendMessage(
  question: string,
  threadId: string | null
): Promise<ChatApiResponse> {
  const body: ChatApiRequest = { question, thread_id: threadId };

  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => 'Erro desconhecido');
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return res.json() as Promise<ChatApiResponse>;
}

/**
 * Verifica se a API está saudável.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json() as Promise<HealthResponse>;
}

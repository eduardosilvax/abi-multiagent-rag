// Tipo de mensagem no chat
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  meta?: ResponseMeta;
}

// Metadados retornados pela API (detalhes técnicos)
export interface ResponseMeta {
  compliance_approved: boolean;
  compliance_reason: string;
  route: string;
  validation_passed: boolean | null;
  validation_notes: string;
  sources_cited: string[];
  steps_taken: string[];
}

// Shape da request/response da API
export interface ChatApiRequest {
  question: string;
  thread_id: string | null;
}

export interface ChatApiResponse {
  answer: string;
  thread_id: string;
  compliance_approved: boolean;
  compliance_reason: string;
  route: string;
  validation_passed: boolean | null;
  validation_notes: string;
  sources_cited: string[];
  steps_taken: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

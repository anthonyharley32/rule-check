const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Citation {
  ref_num: number;
  source_ref: string;
  content_preview: string;
  book?: string;
  penalty_text?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

export interface StreamEvent {
  type: 'text' | 'citations' | 'done' | 'error';
  content?: string;
  citations?: Citation[];
  message?: string;
}

export async function chat(question: string, topK = 5): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function* chatStream(
  question: string,
  topK = 5
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          yield event;
        } catch {
          console.error('Failed to parse SSE event:', line);
        }
      }
    }
  }
}

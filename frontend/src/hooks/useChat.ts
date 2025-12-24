import { useState, useCallback } from 'react';
import { chatStream } from '../lib/api';
import type { Citation } from '../lib/api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
    };

    // Add placeholder assistant message
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      let citations: Citation[] = [];
      let content = '';

      for await (const event of chatStream(question)) {
        if (event.type === 'citations') {
          citations = event.citations || [];
        } else if (event.type === 'text') {
          content += event.content || '';
        } else if (event.type === 'error') {
          throw new Error(event.message);
        }

        // Update assistant message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content, citations, isStreaming: event.type !== 'done' }
              : msg
          )
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Remove failed assistant message
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}

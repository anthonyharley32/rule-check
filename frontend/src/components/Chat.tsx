import { useState, useRef, useEffect, useMemo } from 'react';
import { useChat } from '../hooks/useChat';
import { Message } from './Message';
import { CitationSidebar } from './CitationSidebar';
import type { Citation } from '../lib/api';

export function Chat() {
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Collect all citations from all assistant messages
  const allCitations = useMemo(() => {
    const citations: Citation[] = [];
    for (const message of messages) {
      if (message.role === 'assistant' && message.citations) {
        citations.push(...message.citations);
      }
    }
    return citations;
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setSidebarOpen(true);
    setHighlightedCitation(citation.ref_num);
  };

  const handleCloseSidebar = () => {
    setSidebarOpen(false);
    setHighlightedCitation(null);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">
            NFHS Basketball Rules
          </h1>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
            >
              Clear chat
            </button>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <p className="text-lg mb-2">Ask a question about NFHS basketball rules</p>
              <p className="text-sm">
                Examples: "What is basket interference?" or "Can a coach stand during play?"
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <Message
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
                isStreaming={message.isStreaming}
                onCitationClick={handleCitationClick}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error */}
        {error && (
          <div className="px-4 py-2 bg-red-50 text-red-700 text-sm">
            Error: {error}
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white px-4 py-4 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
          <div className="flex gap-3 max-w-3xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about basketball rules..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700
                         disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors"
            >
              {isLoading ? 'Thinking...' : 'Send'}
            </button>
          </div>
        </form>
      </div>

      {/* Citation Sidebar */}
      <CitationSidebar
        citations={allCitations}
        isOpen={sidebarOpen}
        highlightedRef={highlightedCitation}
        onClose={handleCloseSidebar}
      />
    </div>
  );
}

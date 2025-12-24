import { useMemo } from 'react';
import type { Citation } from '../lib/api';
import { CitationButton } from './CitationButton';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  onCitationClick: (citation: Citation) => void;
}

export function Message({
  role,
  content,
  citations = [],
  isStreaming,
  onCitationClick,
}: MessageProps) {
  // Parse content and replace [N] or [N, M, ...] with citation buttons
  const renderedContent = useMemo(() => {
    if (!content) return null;

    // Match both [N] and [N, M, ...] patterns
    const citationPattern = /(\[\d+(?:,\s*\d+)*\])/g;
    const parts = content.split(citationPattern);

    return parts.map((part, index) => {
      // Check if this part is a citation pattern
      const match = part.match(/^\[(\d+(?:,\s*\d+)*)\]$/);
      if (match) {
        // Extract all numbers from the citation (handles [3, 5] -> [3, 5])
        const nums = match[1].split(/,\s*/).map((n) => parseInt(n.trim(), 10));

        // Render a button for each citation number
        return (
          <span key={index}>
            {nums.map((refNum, btnIndex) => {
              const citation = citations.find((c) => c.ref_num === refNum);
              if (citation) {
                return (
                  <CitationButton
                    key={`${index}-${btnIndex}`}
                    refNum={refNum}
                    citation={citation}
                    onClick={onCitationClick}
                  />
                );
              }
              // If citation not found, render as plain text
              return <span key={`${index}-${btnIndex}`}>[{refNum}]</span>;
            })}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  }, [content, citations, onCitationClick]);

  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white text-gray-900 shadow-sm border border-gray-100'
        }`}
      >
        <div className="whitespace-pre-wrap leading-relaxed">{renderedContent}</div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse rounded-sm" />
        )}
      </div>
    </div>
  );
}

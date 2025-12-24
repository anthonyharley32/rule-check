import { useEffect, useRef } from 'react';
import type { Citation } from '../lib/api';

interface CitationSidebarProps {
  citations: Citation[];
  isOpen: boolean;
  highlightedRef: number | null;
  onClose: () => void;
}

const bookLabels: Record<string, string> = {
  rules: 'Rules Book',
  casebook: 'Casebook',
  manual: 'Officials Manual',
};

export function CitationSidebar({
  citations,
  isOpen,
  highlightedRef,
  onClose,
}: CitationSidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const citationRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Scroll to highlighted citation when it changes
  useEffect(() => {
    if (highlightedRef !== null && isOpen) {
      const element = citationRefs.current.get(highlightedRef);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Add highlight animation
        element.classList.add('ring-2', 'ring-blue-500');
        setTimeout(() => {
          element.classList.remove('ring-2', 'ring-blue-500');
        }, 1500);
      }
    }
  }, [highlightedRef, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      ref={sidebarRef}
      className="w-96 bg-white border-l border-gray-200 flex flex-col h-full shadow-lg"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h2 className="font-semibold text-gray-900">Sources</h2>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer rounded-lg hover:bg-gray-200 transition-colors"
          aria-label="Close sidebar"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Citations list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {citations.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">
            No sources available
          </p>
        ) : (
          citations.map((citation) => (
            <div
              key={citation.ref_num}
              ref={(el) => {
                if (el) citationRefs.current.set(citation.ref_num, el);
              }}
              className="bg-gray-50 rounded-xl p-4 transition-all duration-300"
            >
              {/* Citation number badge */}
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                  {citation.ref_num}
                </span>
                <div className="flex-1 min-w-0">
                  {/* Source type label */}
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    {bookLabels[citation.book || 'rules'] || citation.book}
                  </span>
                  {/* Source reference */}
                  <h3 className="font-semibold text-gray-900 mt-0.5">
                    {citation.source_ref}
                  </h3>
                </div>
              </div>

              {/* Content preview */}
              <p className="text-sm text-gray-700 mt-3 whitespace-pre-wrap leading-relaxed">
                {citation.content_preview}
              </p>

              {/* Penalty text */}
              {citation.penalty_text && (
                <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-1">
                    Penalty
                  </p>
                  <p className="text-sm text-amber-700 whitespace-pre-wrap">
                    {citation.penalty_text}
                  </p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

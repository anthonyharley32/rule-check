import type { Citation } from '../lib/api';

interface CitationButtonProps {
  refNum: number;
  citation: Citation;
  onClick: (citation: Citation) => void;
}

export function CitationButton({ refNum, citation, onClick }: CitationButtonProps) {
  return (
    <button
      onClick={() => onClick(citation)}
      className="inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1 mx-0.5
                 text-xs font-medium text-blue-700 bg-blue-100 rounded
                 hover:bg-blue-200 transition-colors cursor-pointer"
      title={citation.source_ref}
    >
      {refNum}
    </button>
  );
}

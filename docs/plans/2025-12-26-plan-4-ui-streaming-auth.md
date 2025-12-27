# UI, Streaming & Auth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix choppy streaming, add authentication, and improve citation UX with inline rule quotes and a sidebar for supporting references.

**Architecture:** Switch to `x-ai/grok-4.1-fast` for smooth streaming. Add Supabase Auth for user management. Refactor response format so primary rules are quoted inline as markdown blockquotes, while supporting references (case plays, cross-refs) use `[N]` badges that open in sidebar.

**Response Format Example:**
```
Quick summary in plain language.

Rule 4-15-1 says:
> "Exact quoted rule text here..."

[More explanation if needed]

See also Case Play 4.15.1A [1] and 4.15.1B [2] for examples.
```

**Tech Stack:** FastAPI, Supabase Auth, React, OpenRouter, x-ai/grok-4.1-fast

---

## Task 1: Switch Streaming Model

**Files:**
- Modify: `backend/functions/chat.py:59` (model parameter)

**Step 1: Update model constant**

In `backend/functions/chat.py`, change the default model:

```python
# Line 59: Change from
model: str = "google/gemini-2.0-flash-001"
# To
model: str = "x-ai/grok-4.1-fast"
```

**Step 2: Test streaming locally**

```bash
cd backend
python -c "from functions.chat import ChatService; cs = ChatService(); [print(chunk) for chunk in cs.chat_stream('What is a travel?')]"
```

Expected: Chunks should arrive smoothly, not character-by-character.

**Step 3: Verify frontend streaming**

```bash
cd frontend && npm run dev
# Open http://localhost:5173, ask "What is a travel?"
```

Expected: Text appears in smooth word/phrase chunks, not choppy single characters.

**Step 4: Commit**

```bash
git add backend/functions/chat.py
git commit -m "PLAN 4: feat: switch to grok-4.1-fast for smooth streaming"
```

---

## Task 2: Investigate Multi-Turn Context

**Files:**
- Read: `backend/main.py`
- Read: `frontend/src/hooks/useChat.ts`
- Create: `docs/research/2025-12-26-multi-turn-investigation.md`

**Step 1: Analyze backend endpoint**

Check if `/chat/stream` accepts conversation history or just a single question.

**Step 2: Analyze frontend hook**

Check `useChat.ts` to see if it sends conversation history.

**Step 3: Document findings**

Create `docs/research/2025-12-26-multi-turn-investigation.md`:

```markdown
# Multi-Turn Context Investigation

## Current State
- Backend endpoint: [Does/Does not] accept message history
- Frontend hook: [Does/Does not] send message history
- LLM prompt: [Does/Does not] include prior context

## Gap Analysis
[What needs to change for multi-turn to work]

## Recommendation
[Minimal changes needed]
```

**Step 4: Commit**

```bash
git add docs/research/2025-12-26-multi-turn-investigation.md
git commit -m "PLAN 4: docs: investigate multi-turn context state"
```

---

## Task 3: Update LLM Prompt for Inline Rule Quotes

**Files:**
- Modify: `backend/functions/chat.py`

**Step 1: Update the prompt to use blockquotes for primary rules**

In `backend/functions/chat.py`, replace `build_prompt()`:

```python
@traceable(name="build_prompt")
def build_prompt(question: str, sources: list[SearchResult]) -> str:
    """Build the prompt with sources for the LLM."""

    sources_text = []
    for i, source in enumerate(sources, 1):
        source_block = f"[{i}] {source.source_ref}\n{source.content}"
        if source.penalty_text:
            source_block += f"\n\nPENALTY: {source.penalty_text}"
        sources_text.append(source_block)

    sources_section = "\n\n---\n\n".join(sources_text)

    prompt = f"""You are an expert on NFHS (National Federation of High Schools) basketball rules. Answer the question using ONLY the provided sources.

RESPONSE FORMAT:
1. Start with a brief plain-language summary (1-2 sentences)
2. Quote the primary rule(s) that answer the question using markdown blockquotes:

   Rule X-Y-Z says:
   > "Exact text from the rule..."

3. Add any additional explanation if needed
4. Reference supporting materials (case plays, other rules) with citation numbers like [1], [2]
   Example: "See also Case Play 4.15.1A [1] for a similar scenario."

IMPORTANT:
- Use blockquotes (>) for PRIMARY rules that directly answer the question
- Use [N] citations for SUPPORTING references (case plays, cross-references, examples)
- Quote rules EXACTLY as written - do not paraphrase the rule text inside blockquotes
- Include the penalty if relevant to the question

SOURCES:
{sources_section}

---

QUESTION: {question}

Provide a clear, accurate answer following the format above. If the sources don't contain enough information to fully answer, say so."""

    return prompt
```

**Step 2: Test the new prompt format**

```bash
cd backend
python -c "
from functions.chat import ChatService
cs = ChatService()
answer, _ = cs.chat('What is a travel?')
print(answer)
"
```

Expected: Response includes blockquoted rule text.

**Step 3: Commit**

```bash
git add backend/functions/chat.py
git commit -m "PLAN 4: feat: update prompt for inline rule blockquotes"
```

---

## Task 4: Filter Citations to Only [N] References

**Files:**
- Modify: `backend/functions/chat.py`

**Step 1: Modify citation extraction to only include [N] refs**

The blockquoted rules are shown inline - we only need citations for `[N]` references. Update `chat_stream`:

```python
@traceable(name="chat_stream")
def chat_stream(self, question: str, top_k: int = 5) -> Generator[dict, None, None]:
    sources = search_chunks(question, top_k=top_k)

    if not sources:
        yield {"type": "text", "content": "I couldn't find any relevant information."}
        return

    prompt = build_prompt(question, sources)

    # Build ALL citations (we'll filter after)
    all_citations = [
        {
            "ref_num": i,
            "source_ref": source.source_ref,
            "content_preview": source.content,  # Full content for sidebar
            "book": source.book,
            "penalty_text": source.penalty_text
        }
        for i, source in enumerate(sources, 1)
    ]

    # Accumulate full response to extract used [N] citations
    full_response = ""

    stream = self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
            yield {"type": "text", "content": content}

    # Extract only [N] style citations (not blockquoted rules)
    import re
    used_refs = set(int(m) for m in re.findall(r'\[(\d+)\]', full_response))

    # Filter to only [N] referenced citations
    used_citations = [c for c in all_citations if c["ref_num"] in used_refs]

    yield {"type": "citations", "citations": used_citations}
    yield {"type": "done"}
```

**Step 2: Test**

```bash
cd backend
python -c "
from functions.chat import ChatService
cs = ChatService()
for chunk in cs.chat_stream('What is a travel?'):
    print(chunk)
"
```

Expected: `citations` event only contains refs used as `[N]` in the text.

**Step 3: Commit**

```bash
git add backend/functions/chat.py
git commit -m "PLAN 4: feat: filter citations to only [N] references"
```

---

## Task 5: Install react-markdown

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install package**

```bash
cd frontend && npm install react-markdown
```

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "PLAN 4: chore: add react-markdown dependency"
```

---

## Task 6: Create InlineCitation Component

**Files:**
- Create: `frontend/src/components/InlineCitation.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/InlineCitation.tsx
import { useState } from 'react';
import type { Citation } from '../lib/api';

interface InlineCitationProps {
  citation: Citation;
  onExpand: (citation: Citation) => void;
}

export function InlineCitation({ citation, onExpand }: InlineCitationProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <span className="relative inline">
      {/* Citation badge */}
      <button
        className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium
                   bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200
                   cursor-pointer transition-colors mx-0.5"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => onExpand(citation)}
        aria-label={`Citation ${citation.ref_num}: ${citation.source_ref}`}
      >
        {citation.ref_num}
      </button>

      {/* Hover preview */}
      {isHovered && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-72 p-3
                        bg-white rounded-lg shadow-lg border border-gray-200
                        text-left text-sm text-gray-700">
          <div className="font-semibold text-gray-900 mb-1">
            {citation.source_ref}
          </div>
          <div className="line-clamp-3">
            {citation.content_preview}
          </div>
          <div className="text-xs text-blue-600 mt-2">
            Click to expand →
          </div>
        </div>
      )}
    </span>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/InlineCitation.tsx
git commit -m "PLAN 4: feat: add InlineCitation component with hover preview"
```

---

## Task 7: Update Message Component for Markdown

**Files:**
- Modify: `frontend/src/components/Message.tsx`

**Step 1: Update to render markdown blockquotes**

```tsx
// frontend/src/components/Message.tsx
import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Citation } from '../lib/api';
import { InlineCitation } from './InlineCitation';

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
  const processedContent = useMemo(() => {
    if (!content) return null;

    // Split content by citation patterns [N] or [N, M]
    const citationPattern = /(\[\d+(?:,\s*\d+)*\])/g;
    const parts = content.split(citationPattern);

    return parts.map((part, index) => {
      // Check if this part is a citation pattern
      const match = part.match(/^\[(\d+(?:,\s*\d+)*)\]$/);
      if (match) {
        const nums = match[1].split(/,\s*/).map((n) => parseInt(n.trim(), 10));
        return (
          <span key={index}>
            {nums.map((refNum, btnIndex) => {
              const citation = citations.find((c) => c.ref_num === refNum);
              if (citation) {
                return (
                  <InlineCitation
                    key={`${index}-${btnIndex}`}
                    citation={citation}
                    onExpand={onCitationClick}
                  />
                );
              }
              return <span key={`${index}-${btnIndex}`}>[{refNum}]</span>;
            })}
          </span>
        );
      }

      // Render markdown for non-citation text
      return (
        <ReactMarkdown
          key={index}
          components={{
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-blue-500 bg-blue-50 pl-4 py-2 my-3 text-gray-700 rounded-r">
                {children}
              </blockquote>
            ),
            p: ({ children }) => <span className="inline">{children} </span>,
          }}
        >
          {part}
        </ReactMarkdown>
      );
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
        <div className="leading-relaxed">{processedContent}</div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse rounded-sm" />
        )}
      </div>
    </div>
  );
}
```

**Step 2: Test blockquote rendering**

```bash
cd frontend && npm run dev
# Ask "What is a travel?"
# Verify: blockquoted rule text appears with blue left border
```

**Step 3: Commit**

```bash
git add frontend/src/components/Message.tsx
git commit -m "PLAN 4: feat: render markdown blockquotes for rule citations"
```

---

## Task 8: Update Sidebar Header

**Files:**
- Modify: `frontend/src/components/CitationSidebar.tsx`

**Step 1: Change header to "Supporting References"**

```tsx
{/* Header */}
<div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
  <h2 className="font-semibold text-gray-900">Supporting References</h2>
  ...
</div>
```

**Step 2: Show full content with scroll**

```tsx
{/* Content - full text with scroll */}
<p className="text-sm text-gray-700 mt-3 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">
  {citation.content_preview}
</p>
```

**Step 3: Commit**

```bash
git add frontend/src/components/CitationSidebar.tsx
git commit -m "PLAN 4: feat: update sidebar for supporting references"
```

---

## Task 9: Add Rule Explorer Modal

**Files:**
- Create: `frontend/src/components/RuleExplorerModal.tsx`
- Modify: `frontend/src/components/CitationSidebar.tsx`
- Modify: `backend/functions/search.py`
- Modify: `backend/main.py`

**Step 1: Add backend endpoint for surrounding rules**

In `backend/functions/search.py`:

```python
def get_surrounding_chunks(source_ref: str, window: int = 2) -> list[SearchResult]:
    """Get chunks before and after a given source reference."""
    # Implementation depends on your chunk storage structure
    # Query database for adjacent sections
    pass
```

In `backend/main.py`:

```python
@app.get("/rules/context/{source_ref}")
async def get_rule_context(source_ref: str, window: int = 2):
    """Get surrounding rules for context exploration."""
    from functions.search import get_surrounding_chunks
    chunks = get_surrounding_chunks(source_ref, window)
    return {"chunks": [...]}
```

**Step 2: Create RuleExplorerModal component**

```tsx
// frontend/src/components/RuleExplorerModal.tsx
import { useEffect, useState } from 'react';
import type { Citation } from '../lib/api';

interface RuleExplorerModalProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
}

export function RuleExplorerModal({ citation, isOpen, onClose }: RuleExplorerModalProps) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!citation || !isOpen) return;
    setLoading(true);
    fetch(`${import.meta.env.VITE_API_URL}/rules/context/${encodeURIComponent(citation.source_ref)}`)
      .then(res => res.json())
      .then(data => setChunks(data.chunks))
      .finally(() => setLoading(false));
  }, [citation, isOpen]);

  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Explore: {citation.source_ref}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">✕</button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-4">
          {loading ? <div>Loading...</div> : chunks.map((chunk, i) => (
            <div key={i} className={`p-4 rounded-lg ${chunk.source_ref === citation.source_ref ? 'bg-blue-50 border-2 border-blue-300' : 'bg-gray-50'}`}>
              <div className="font-semibold">{chunk.source_ref}</div>
              <div className="text-sm mt-2">{chunk.content}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Add "Explore" button to sidebar**

**Step 4: Wire up modal in Chat**

**Step 5: Commit**

```bash
git add frontend/src/components/RuleExplorerModal.tsx frontend/src/components/CitationSidebar.tsx backend/functions/search.py backend/main.py
git commit -m "PLAN 4: feat: add modal for exploring surrounding rules"
```

---

## Task 10: Implement Supabase Auth

**Files:**
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/components/AuthForm.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Install Supabase client**

```bash
cd frontend && npm install @supabase/supabase-js
```

**Step 2: Create Supabase client**

```typescript
// frontend/src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

**Step 3: Create AuthContext with signIn, signUp, signOut, signInWithGoogle**

**Step 4: Create AuthForm component**

**Step 5: Update App.tsx to require auth**

**Step 6: Test auth flow**

**Step 7: Commit**

```bash
git add frontend/src/lib/supabase.ts frontend/src/contexts/AuthContext.tsx frontend/src/components/AuthForm.tsx frontend/src/App.tsx
git commit -m "PLAN 4: feat: add Supabase authentication"
```

---

## Task 11: Add Backend Auth Middleware (Optional)

**Files:**
- Modify: `backend/main.py`
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add Supabase JWT verification middleware**

**Step 2: Update frontend to send auth token in requests**

**Step 3: Test protected routes**

**Step 4: Commit**

```bash
git add backend/main.py frontend/src/lib/api.ts
git commit -m "PLAN 4: feat: add backend auth middleware"
```

---

## Summary

| Task | Focus | Output |
|------|-------|--------|
| 1 | Switch streaming model | Smooth streaming with grok-4.1-fast |
| 2 | Investigate multi-turn | Research doc on current state |
| 3 | Update LLM prompt | Blockquotes for primary rules, [N] for refs |
| 4 | Filter citations | Only [N] references go to sidebar |
| 5 | Install react-markdown | Dependency for rendering |
| 6 | InlineCitation component | Hover preview + click to expand |
| 7 | Update Message component | Render markdown blockquotes |
| 8 | Update sidebar | "Supporting References" header |
| 9 | Rule explorer modal | Browse surrounding rules |
| 10 | Supabase Auth | Email/password + OAuth |
| 11 | Backend auth | Protected API routes (optional) |

**After completion:** Run full test suite, verify all features work together, then merge to main.

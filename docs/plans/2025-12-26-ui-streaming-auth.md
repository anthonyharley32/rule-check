# UI, Streaming & Auth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix choppy streaming, add authentication, and improve citation UX so users see only relevant sources with full context.

**Architecture:** Switch to `x-ai/grok-4.1-fast` for smooth streaming. Add Supabase Auth for user management. Refactor citations to show only what the AI actually used, with inline expandable blocks and a modal for exploring surrounding rules.

**Tech Stack:** FastAPI, Supabase Auth, React, OpenRouter, x-ai/grok-4.1-fast

---

## Task 1: Switch Streaming Model

**Files:**
- Modify: `backend/functions/chat.py:59` (model parameter)
- Modify: `.env` (ensure OPENROUTER_API_KEY is set)

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
git commit -m "PLAN 4/5: feat: switch to grok-4.1-fast for smooth streaming"
```

---

## Task 2: Investigate Multi-Turn Context

**Files:**
- Read: `backend/main.py`
- Read: `frontend/src/hooks/useChat.ts`
- Create: `docs/research/2025-12-26-multi-turn-investigation.md`

**Step 1: Analyze backend endpoint**

Check if `/chat/stream` accepts conversation history or just a single question.

Current state in `backend/main.py`:
```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    # Does it use request.messages or just request.question?
```

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
git commit -m "PLAN 4/5: docs: investigate multi-turn context state"
```

---

## Task 3: Filter Citations to Only Used Sources

**Files:**
- Modify: `backend/functions/chat.py`
- Modify: `backend/main.py`

**Step 1: Add citation extraction after streaming completes**

In `backend/functions/chat.py`, modify `chat_stream` to track which citations were actually used:

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
            "content_preview": source.content,  # Full content, not truncated
            "book": source.book,
            "penalty_text": source.penalty_text
        }
        for i, source in enumerate(sources, 1)
    ]

    # Accumulate full response to extract used citations
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

    # Extract which citations were actually used
    import re
    used_refs = set(int(m) for m in re.findall(r'\[(\d+)\]', full_response))

    # Filter to only used citations
    used_citations = [c for c in all_citations if c["ref_num"] in used_refs]

    yield {"type": "citations", "citations": used_citations}
    yield {"type": "done"}
```

**Step 2: Update frontend to handle citations-at-end**

In `frontend/src/hooks/useChat.ts`, citations now arrive after text:

```typescript
for await (const event of chatStream(question)) {
  if (event.type === 'text') {
    content += event.content || '';
  } else if (event.type === 'citations') {
    citations = event.citations || [];
  } else if (event.type === 'error') {
    throw new Error(event.message);
  }

  // Update message (citations may not be available yet)
  setMessages((prev) =>
    prev.map((msg) =>
      msg.id === assistantId
        ? { ...msg, content, citations, isStreaming: event.type !== 'done' }
        : msg
    )
  );
}
```

**Step 3: Test the change**

```bash
# Backend test
cd backend
python -c "
from functions.chat import ChatService
cs = ChatService()
for chunk in cs.chat_stream('What is a travel?'):
    print(chunk)
"
```

Expected: `citations` event only contains refs that appear in the response text.

**Step 4: Commit**

```bash
git add backend/functions/chat.py frontend/src/hooks/useChat.ts
git commit -m "PLAN 4/5: feat: filter citations to only used sources"
```

---

## Task 4: Show Full Rule Text in Sidebar

**Files:**
- Modify: `frontend/src/components/CitationSidebar.tsx`

**Step 1: Remove content truncation**

The backend now sends full `content_preview`. Update sidebar to display it with proper scrolling:

```tsx
{/* Content - full text with scroll */}
<div className="text-sm text-gray-700 mt-3 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">
  {citation.content_preview}
</div>
```

**Step 2: Add section context header**

Show the hierarchical location (Rule → Section → Article):

```tsx
<div className="flex-1 min-w-0">
  {/* Book type label */}
  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
    {bookLabels[citation.book || 'rules'] || citation.book}
  </span>
  {/* Source reference with hierarchy */}
  <h3 className="font-semibold text-gray-900 mt-0.5">
    {citation.source_ref}
  </h3>
</div>
```

**Step 3: Test sidebar**

```bash
cd frontend && npm run dev
# Ask a question, click a citation, verify full text shows with scroll
```

**Step 4: Commit**

```bash
git add frontend/src/components/CitationSidebar.tsx
git commit -m "PLAN 4/5: feat: show full rule text in sidebar with scroll"
```

---

## Task 5: Add Inline Citation Blocks

**Files:**
- Create: `frontend/src/components/InlineCitation.tsx`
- Modify: `frontend/src/components/Message.tsx`

**Step 1: Create InlineCitation component**

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

**Step 2: Update Message to use InlineCitation**

In `frontend/src/components/Message.tsx`:

```tsx
import { InlineCitation } from './InlineCitation';

// In the renderedContent useMemo, replace CitationButton:
if (citation) {
  return (
    <InlineCitation
      key={`${index}-${btnIndex}`}
      citation={citation}
      onExpand={onCitationClick}
    />
  );
}
```

**Step 3: Test inline citations**

```bash
cd frontend && npm run dev
# Ask a question, hover over citation number, verify preview appears
# Click citation, verify it expands in sidebar
```

**Step 4: Commit**

```bash
git add frontend/src/components/InlineCitation.tsx frontend/src/components/Message.tsx
git commit -m "PLAN 4/5: feat: add inline citation blocks with hover preview"
```

---

## Task 6: Add Modal for Exploring Surrounding Rules

**Files:**
- Create: `frontend/src/components/RuleExplorerModal.tsx`
- Modify: `frontend/src/components/CitationSidebar.tsx`
- Modify: `backend/functions/search.py` (add endpoint for surrounding rules)
- Modify: `backend/main.py`

**Step 1: Add backend endpoint for surrounding rules**

In `backend/functions/search.py`, add function to get surrounding chunks:

```python
def get_surrounding_chunks(source_ref: str, window: int = 2) -> list[SearchResult]:
    """
    Get chunks before and after a given source reference.

    Args:
        source_ref: The source reference (e.g., "Rule 4-15-1")
        window: Number of chunks before/after to retrieve

    Returns:
        List of surrounding chunks in order
    """
    # Parse source_ref to find adjacent sections
    # This depends on your chunk storage structure
    # Placeholder implementation - adjust based on actual schema
    pass
```

In `backend/main.py`, add endpoint:

```python
@app.get("/rules/context/{source_ref}")
async def get_rule_context(source_ref: str, window: int = 2):
    """Get surrounding rules for context exploration."""
    from functions.search import get_surrounding_chunks
    chunks = get_surrounding_chunks(source_ref, window)
    return {"chunks": [
        {
            "source_ref": c.source_ref,
            "content": c.content,
            "book": c.book,
            "penalty_text": c.penalty_text
        }
        for c in chunks
    ]}
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

interface ContextChunk {
  source_ref: string;
  content: string;
  book?: string;
  penalty_text?: string;
}

export function RuleExplorerModal({ citation, isOpen, onClose }: RuleExplorerModalProps) {
  const [chunks, setChunks] = useState<ContextChunk[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!citation || !isOpen) return;

    setLoading(true);
    fetch(`${import.meta.env.VITE_API_URL}/rules/context/${encodeURIComponent(citation.source_ref)}`)
      .then(res => res.json())
      .then(data => setChunks(data.chunks))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [citation, isOpen]);

  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Explore: {citation.source_ref}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-4">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : (
            chunks.map((chunk, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg ${
                  chunk.source_ref === citation.source_ref
                    ? 'bg-blue-50 border-2 border-blue-300'
                    : 'bg-gray-50'
                }`}
              >
                <div className="font-semibold text-gray-900 mb-2">
                  {chunk.source_ref}
                </div>
                <div className="text-sm text-gray-700 whitespace-pre-wrap">
                  {chunk.content}
                </div>
                {chunk.penalty_text && (
                  <div className="mt-2 p-2 bg-amber-50 rounded text-sm text-amber-700">
                    <strong>Penalty:</strong> {chunk.penalty_text}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Add "Explore" button to CitationSidebar**

In `CitationSidebar.tsx`, add button to each citation:

```tsx
<button
  onClick={() => onExplore?.(citation)}
  className="mt-2 text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
>
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
  Explore surrounding rules
</button>
```

**Step 4: Wire up modal in Chat component**

In `frontend/src/components/Chat.tsx`:

```tsx
import { RuleExplorerModal } from './RuleExplorerModal';

// Add state
const [explorerCitation, setExplorerCitation] = useState<Citation | null>(null);

// Add modal
<RuleExplorerModal
  citation={explorerCitation}
  isOpen={explorerCitation !== null}
  onClose={() => setExplorerCitation(null)}
/>
```

**Step 5: Test modal**

```bash
cd frontend && npm run dev
# Ask a question, click citation in sidebar, click "Explore surrounding rules"
# Verify modal shows surrounding context with current rule highlighted
```

**Step 6: Commit**

```bash
git add frontend/src/components/RuleExplorerModal.tsx frontend/src/components/CitationSidebar.tsx frontend/src/components/Chat.tsx backend/functions/search.py backend/main.py
git commit -m "PLAN 4/5: feat: add modal for exploring surrounding rules"
```

---

## Task 7: Implement Supabase Auth

**Files:**
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/components/AuthForm.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `backend/main.py` (add auth middleware)

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

**Step 3: Create AuthContext**

```tsx
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({ provider: 'google' });
    if (error) throw error;
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, signIn, signUp, signOut, signInWithGoogle }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**Step 4: Create AuthForm component**

```tsx
// frontend/src/components/AuthForm.tsx
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function AuthForm() {
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isSignUp) {
        await signUp(email, password);
      } else {
        await signIn(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            NFHS Basketball Rules
          </h2>
          <p className="mt-2 text-gray-600">
            {isSignUp ? 'Create your account' : 'Sign in to continue'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={6}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">Or continue with</span>
            </div>
          </div>

          <button
            type="button"
            onClick={signInWithGoogle}
            className="w-full py-3 px-4 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Google
          </button>

          <div className="text-center text-sm">
            <button
              type="button"
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-blue-600 hover:text-blue-800"
            >
              {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 5: Update App.tsx to require auth**

```tsx
// frontend/src/App.tsx
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AuthForm } from './components/AuthForm';
import { Chat } from './components/Chat';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!user) {
    return <AuthForm />;
  }

  return <Chat />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
```

**Step 6: Add environment variables**

Create/update `.env`:

```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

**Step 7: Test auth flow**

```bash
cd frontend && npm run dev
# Verify:
# 1. Login form appears
# 2. Can sign up with email/password
# 3. Can sign in with email/password
# 4. Google OAuth works
# 5. After login, chat appears
# 6. Sign out works
```

**Step 8: Commit**

```bash
git add frontend/src/lib/supabase.ts frontend/src/contexts/AuthContext.tsx frontend/src/components/AuthForm.tsx frontend/src/App.tsx
git commit -m "PLAN 4/5: feat: add Supabase authentication"
```

---

## Task 8: Add Backend Auth Middleware (Optional)

**Files:**
- Modify: `backend/main.py`

**Step 1: Add Supabase JWT verification**

```python
# backend/main.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Supabase JWT token."""
    token = credentials.credentials
    supabase_url = os.getenv("SUPABASE_URL")

    # Verify with Supabase
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return response.json()

# Add to protected routes
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: dict = Depends(verify_token)):
    # ... existing code
```

**Step 2: Update frontend to send auth token**

In `frontend/src/lib/api.ts`:

```typescript
import { supabase } from './supabase';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    return { 'Authorization': `Bearer ${session.access_token}` };
  }
  return {};
}

export async function* chatStream(question: string, topK = 5): AsyncGenerator<StreamEvent> {
  const authHeaders = await getAuthHeaders();

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders
    },
    body: JSON.stringify({ question, top_k: topK }),
  });
  // ... rest of function
}
```

**Step 3: Test protected routes**

```bash
# Without token - should fail
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a travel?"}'
# Expected: 401 Unauthorized

# With token - should work
# (Get token from Supabase session in browser devtools)
```

**Step 4: Commit**

```bash
git add backend/main.py frontend/src/lib/api.ts
git commit -m "PLAN 4/5: feat: add backend auth middleware"
```

---

## Summary

| Task | Focus | Output |
|------|-------|--------|
| 1 | Switch streaming model | Smooth streaming with grok-4.1-fast |
| 2 | Investigate multi-turn | Research doc on current state |
| 3 | Filter citations | Only show used sources |
| 4 | Full rule text | Scrollable sidebar content |
| 5 | Inline citations | Hover preview + expand |
| 6 | Rule explorer modal | Browse surrounding rules |
| 7 | Supabase Auth | Email/password + OAuth |
| 8 | Backend auth | Protected API routes |

**After completion:** Run full test suite, verify all features work together, then merge to main.

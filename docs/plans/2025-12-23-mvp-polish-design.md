# MVP Polish Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address MVP feedback - visual polish, citation sidebar UX, fix multi-citation parsing, and enable LangSmith tracing.

---

## 1. Visual Polish

### 1.1 Browser Tab Title
- Update `frontend/index.html` to set `<title>NFHS Rules Chat</title>`

### 1.2 Cursor Pointers
- Add `cursor-pointer` class to all buttons and interactive elements:
  - CitationButton
  - Send button
  - Clear chat button
  - Sidebar close button

### 1.3 Modern Styling Updates
- **Header**: Subtle bottom shadow, slightly more padding
- **Message bubbles**: Softer border radius, subtle shadows on assistant messages
- **Input area**: Larger input, more prominent send button, focus ring
- **Overall**: Better spacing, font-weight adjustments, color refinements

---

## 2. Citation Sidebar

### 2.1 Behavior
- Sidebar hidden by default
- Clicking citation `[N]` in message opens sidebar and scrolls to that citation
- Sidebar shows ALL citations for the current message (or conversation)
- Close button (X) hides sidebar
- Clicking outside sidebar does NOT close it (user must explicitly close)

### 2.2 Layout
```
+------------------+-------------+
|                  |  SIDEBAR    |
|    CHAT AREA     |  (when open)|
|                  |             |
|                  | [1] Rule... |
|                  | [2] Case... |
|                  | [3] Manual..|
|                  |             |
+------------------+-------------+
|     INPUT BAR                  |
+--------------------------------+
```

### 2.3 Sidebar Content
Each citation card shows:
- Number badge (1, 2, 3...)
- Source type label (Rules Book / Casebook / Officials Manual)
- Source reference (e.g., "Rule 4-6-1")
- Content preview (full text, scrollable within card if long)
- Penalty text in amber box (if applicable)

### 2.4 Scroll Behavior
- When clicking `[N]`, sidebar opens
- The Nth citation smoothly scrolls into view
- Brief highlight animation on the target citation

---

## 3. Fix Multi-Citation Parsing

### 3.1 Problem
Current regex: `/(\[\d+\])/g`
Only matches: `[1]`, `[2]`, etc.
Does NOT match: `[3, 5]`, `[1, 2, 3]`

### 3.2 Solution
Update `Message.tsx` to:
1. Match both `[N]` and `[N, M, ...]` patterns
2. For multi-citation matches, split and render as separate adjacent buttons

New regex: `/(\[\d+(?:,\s*\d+)*\])/g`

Parsing logic:
```typescript
// "[3, 5]" -> render as <CitationButton 3 /> <CitationButton 5 />
const nums = match.replace(/[\[\]\s]/g, '').split(',');
return nums.map(n => <CitationButton refNum={parseInt(n)} ... />);
```

---

## 4. LangSmith Tracing

### 4.1 Problem
Current implementation uses raw `OpenAI` client, which doesn't integrate with LangSmith.

### 4.2 Solution
Wrap the chat call with LangChain's tracing:

Option A: Use `langchain` ChatOpenAI with callbacks
Option B: Use `langsmith` `traceable` decorator on functions

**Recommended: Option B** - minimal changes, just decorate existing functions.

### 4.3 Implementation
```python
from langsmith import traceable

@traceable(name="search_chunks")
def search_chunks(query: str, ...):
    ...

@traceable(name="chat")
def chat(self, question: str, ...):
    ...
```

Ensure environment variables are set:
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT=nfhs-rules-chat`

---

## Implementation Tasks

### Phase 1: Visual Polish
- [ ] Task 1.1: Update browser tab title in index.html
- [ ] Task 1.2: Add cursor-pointer to all interactive elements
- [ ] Task 1.3: Modernize header styling
- [ ] Task 1.4: Modernize message bubble styling
- [ ] Task 1.5: Modernize input area styling

### Phase 2: Citation Sidebar
- [ ] Task 2.1: Create CitationSidebar component
- [ ] Task 2.2: Update Chat component layout for sidebar
- [ ] Task 2.3: Add sidebar open/close state management
- [ ] Task 2.4: Implement scroll-to-citation behavior
- [ ] Task 2.5: Remove old CitationPanel component

### Phase 3: Multi-Citation Parsing
- [ ] Task 3.1: Update regex in Message.tsx
- [ ] Task 3.2: Handle multi-citation rendering
- [ ] Task 3.3: Test with various citation formats

### Phase 4: LangSmith Tracing
- [ ] Task 4.1: Install langsmith package
- [ ] Task 4.2: Add @traceable decorators to search and chat functions
- [ ] Task 4.3: Verify tracing appears in LangSmith dashboard

---

## Files to Modify

**Frontend:**
- `frontend/index.html` - tab title
- `frontend/src/components/CitationButton.tsx` - cursor pointer
- `frontend/src/components/Message.tsx` - multi-citation parsing
- `frontend/src/components/Chat.tsx` - sidebar integration, layout
- `frontend/src/components/CitationSidebar.tsx` - NEW FILE

**Backend:**
- `backend/requirements.txt` - add langsmith
- `backend/functions/search.py` - add @traceable
- `backend/functions/chat.py` - add @traceable

**Delete:**
- `frontend/src/components/CitationPanel.tsx` - replaced by sidebar

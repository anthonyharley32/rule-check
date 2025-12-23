# Citation Implementation Guide

## Overview

This document outlines different approaches to implementing Perplexity-like citation systems in AI chat applications, analyzing the current implementation and recommending best practices.

## Current Implementation

### How It Works

The current system uses inline citation markers that the AI inserts into the response text:

1. **Backend**: AI generates text with `{ref:N}` markers (e.g., "TypeScript{ref:1} and React{ref:2}")
2. **Frontend**: Regex parsing converts markers to clickable `[1]`, `[2]` buttons
3. **Display**: Citations shown in a grid below the message

### Code Structure

#### Backend (Python)
```python
# System prompt instructs AI to use {ref:N} format
system_message = f"""You are {avatar_name}, respond from their point of view.

You have access to previous messages as numbered references. You should actively use these references to support your responses. 
When you mention ANY information from the references, you MUST cite them using the {{ref:N}} format where N is the reference number.

Guidelines for citations:
1. Place the citation immediately after the information it supports with no space before it (e.g., "word{{ref:1}}" not "word {{ref:1}}")
2. Be specific about what information you're citing
3. Use multiple citations if you're combining information from different references
4. If a reference contains relevant information, make sure to incorporate and cite it
"""
```

#### Frontend (TypeScript/React)
```typescript
// Parses {ref:N} markers and converts to clickable buttons
function formatMessageWithCitations(
  content: string, 
  references: CitationReference[], 
  onCitationClick: (citationId: string) => void
) {
  const parts = content.split(/(\{ref:\d+\})/);
  
  return (
    <div className="whitespace-pre-wrap">
      {parts.map((part, index) => {
        const match = part.match(/\{ref:(\d+)\}/);
        if (match) {
          const refNumber = match[1];
          const citationId = refToCitationMap.get(refNumber);
          const displayNumber = displayNumberMap.get(refNumber);
          
          return (
            <button
              onClick={() => onCitationClick(citationId)}
              className="inline-flex items-center px-1.5 py-0.5 mx-0.5 bg-blue-100..."
            >
              [{displayNumber}]
            </button>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </div>
  );
}
```

### Pros and Cons

**Pros:**
- ✅ Simple to implement
- ✅ Works with any LLM (no special features needed)
- ✅ Easy to understand and debug
- ✅ No additional API requirements

**Cons:**
- ❌ Brittle: Relies on AI following format exactly
- ❌ No validation: Can't verify citations match references
- ❌ Regex parsing can break on edge cases
- ❌ Hard to stream: Citations only appear after full response
- ❌ No position tracking: Can't highlight exact cited text
- ❌ Markers visible in raw text (could confuse AI in some contexts)

---

## Alternative Approaches

### 1. Structured Output (JSON Mode)

Use LLM's structured output capabilities to get validated JSON responses.

#### Implementation

**Backend:**
```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {
            "role": "system",
            "content": """You must respond in JSON format:
            {
                "content": "your response text with citation markers",
                "citations": [
                    {
                        "ref_id": 1,
                        "start_pos": 45,
                        "end_pos": 67,
                        "text": "TypeScript"
                    }
                ]
            }
            
            Use [1], [2], etc. as citation markers in the content."""
        },
        {"role": "user", "content": user_message}
    ]
)

data = json.loads(response.choices[0].message.content)
return {
    "content": data["content"],
    "citations": data["citations"]
}
```

**Frontend:**
```typescript
interface StructuredCitation {
  ref_id: number;
  start_pos: number;
  end_pos: number;
  text: string;
}

function renderWithStructuredCitations(
  content: string,
  citations: StructuredCitation[]
) {
  const parts = [];
  let lastIndex = 0;
  
  // Sort citations by position
  const sortedCitations = [...citations].sort((a, b) => a.start_pos - b.start_pos);
  
  sortedCitations.forEach((citation, idx) => {
    // Text before citation
    parts.push(content.slice(lastIndex, citation.start_pos));
    
    // Cited text with button
    parts.push(
      <span key={idx}>
        <span className="highlight">{citation.text}</span>
        <CitationButton citationId={citation.ref_id}>
          [{idx + 1}]
        </CitationButton>
      </span>
    );
    
    lastIndex = citation.end_pos;
  });
  
  // Remaining text
  parts.push(content.slice(lastIndex));
  
  return <div>{parts}</div>;
}
```

**Pros:**
- ✅ Type-safe and validated
- ✅ No regex parsing needed
- ✅ Can track exact text positions
- ✅ Works with streaming (can parse partial JSON)
- ✅ More reliable than text markers

**Cons:**
- ❌ Requires LLM with JSON mode support
- ❌ Slightly more complex setup
- ❌ JSON parsing overhead

---

### 2. Citation Metadata with Positions

Return citations separately with character positions instead of inline markers.

#### Implementation

**Backend:**
```python
async def generate_response(self, message: str) -> Dict[str, Any]:
    # ... get similar messages ...
    
    response_text = await llm.agenerate(message)
    
    # Parse response to find citation references
    citations = []
    import re
    
    # Find all [N] markers in response
    citation_pattern = r'\[(\d+)\]'
    matches = list(re.finditer(citation_pattern, response_text))
    
    for match in matches:
        ref_num = int(match.group(1))
        citation = {
            "ref_id": ref_num,
            "start_pos": match.start(),
            "end_pos": match.end(),
            "citation_id": f"cite_{ref_num}"
        }
        citations.append(citation)
    
    # Remove markers from text (optional, or keep them)
    clean_text = response_text  # or remove markers
    
    return {
        "content": clean_text,
        "citations": citations,
        "citation_metadata": citation_metadata_list
    }
```

**Frontend:**
```typescript
interface PositionCitation {
  ref_id: number;
  start_pos: number;
  end_pos: number;
  citation_id: string;
}

function renderWithPositionCitations(
  text: string,
  citations: PositionCitation[]
) {
  const parts = [];
  let lastIndex = 0;
  
  citations
    .sort((a, b) => a.start_pos - b.start_pos)
    .forEach((citation, idx) => {
      // Add text before citation
      if (citation.start_pos > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {text.slice(lastIndex, citation.start_pos)}
          </span>
        );
      }
      
      // Add citation button
      parts.push(
        <CitationButton 
          key={`cite-${idx}`}
          citationId={citation.citation_id}
          position={citation.start_pos}
        >
          [{idx + 1}]
        </CitationButton>
      );
      
      lastIndex = citation.end_pos;
    });
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(
      <span key={`text-${lastIndex}`}>
        {text.slice(lastIndex)}
      </span>
    );
  }
  
  return <div className="whitespace-pre-wrap">{parts}</div>;
}
```

**Pros:**
- ✅ Clean separation of content and citations
- ✅ Can highlight exact cited text
- ✅ No markers in text
- ✅ Easier to validate

**Cons:**
- ❌ Still requires parsing (though simpler)
- ❌ Position tracking can be tricky with streaming
- ❌ Need to handle text updates carefully

---

### 3. Streaming with Citation Events

Stream both text and citation events separately for real-time UX.

#### Implementation

**Backend:**
```python
from fastapi.responses import StreamingResponse
import json

async def stream_response_with_citations(message: str):
    async def generate():
        async for chunk in llm.astream(message):
            # Stream text chunks
            if chunk.type == "text_delta":
                yield f"data: {json.dumps({
                    'type': 'text',
                    'content': chunk.delta,
                    'cumulative_length': chunk.cumulative_length
                })}\n\n"
            
            # Stream citation events when found
            elif chunk.type == "citation":
                yield f"data: {json.dumps({
                    'type': 'citation',
                    'citation': {
                        'id': chunk.citation_id,
                        'ref_id': chunk.ref_id,
                        'start_pos': chunk.start_pos,
                        'end_pos': chunk.end_pos,
                        'metadata': chunk.metadata
                    }
                })}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Frontend:**
```typescript
function useStreamingCitations() {
  const [text, setText] = useState('');
  const [citations, setCitations] = useState<Map<number, Citation>>(new Map());
  const [isStreaming, setIsStreaming] = useState(false);
  
  const streamResponse = async (message: string) => {
    setIsStreaming(true);
    setText('');
    setCitations(new Map());
    
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message }),
      headers: { 'Content-Type': 'application/json' }
    });
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) return;
    
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          
          if (data.type === 'text') {
            setText(prev => prev + data.content);
          } else if (data.type === 'citation') {
            setCitations(prev => {
              const next = new Map(prev);
              next.set(data.citation.start_pos, data.citation);
              return next;
            });
          } else if (data === '[DONE]') {
            setIsStreaming(false);
          }
        }
      }
    }
  };
  
  return { text, citations, streamResponse, isStreaming };
}

// Rendering component
function StreamingCitationView({ text, citations }: Props) {
  const parts = [];
  let lastIndex = 0;
  
  const sortedCitations = Array.from(citations.values())
    .sort((a, b) => a.start_pos - b.start_pos);
  
  sortedCitations.forEach((citation, idx) => {
    if (citation.start_pos > lastIndex) {
      parts.push(text.slice(lastIndex, citation.start_pos));
    }
    
    parts.push(
      <CitationButton key={idx} citationId={citation.id}>
        [{idx + 1}]
      </CitationButton>
    );
    
    lastIndex = citation.end_pos;
  });
  
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  
  return <div>{parts}</div>;
}
```

**Pros:**
- ✅ Real-time UX: Citations appear as they're found
- ✅ Feels responsive and modern
- ✅ Progressive enhancement
- ✅ Better perceived performance

**Cons:**
- ❌ More complex state management
- ❌ Citations might arrive before referenced text
- ❌ Harder to validate completeness
- ❌ Error handling for partial failures is tricky
- ❌ Requires careful ordering logic

---

### 4. Hybrid Approach (Recommended)

Combine streaming text with structured citation events for the best of both worlds.

#### Implementation

**Backend:**
```python
from typing import AsyncGenerator
import json

async def stream_hybrid_response(
    message: str,
    context_messages: List[Dict]
) -> AsyncGenerator[str, None]:
    """
    Stream both text and structured citation events.
    Uses structured output for citations, streaming for text.
    """
    
    # Prepare system message with citation instructions
    system_prompt = """You are a helpful assistant with access to context.

When referencing information from the context, you must:
1. Include citation markers [1], [2], etc. in your response
2. Citations should appear immediately after the information they support
3. Be specific and accurate with citations

Available context:
{context}
""".format(context=format_context(context_messages))
    
    # Stream response
    async for chunk in llm.astream(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    ):
        # Stream text delta
        if hasattr(chunk, 'delta') and chunk.delta.get('content'):
            yield json.dumps({
                "type": "text",
                "content": chunk.delta["content"],
                "position": chunk.cumulative_length
            }) + "\n"
        
        # Detect citation markers and emit structured events
        # (This would require custom parsing logic)
        if hasattr(chunk, 'citations'):
            for citation in chunk.citations:
                yield json.dumps({
                    "type": "citation",
                    "citation": {
                        "id": citation.id,
                        "ref_id": citation.ref_id,
                        "start_pos": citation.start_pos,
                        "end_pos": citation.end_pos,
                        "metadata": citation.metadata
                    }
                }) + "\n"
    
    # Final event
    yield json.dumps({"type": "done"}) + "\n"
```

**Frontend with React:**
```typescript
import { useState, useEffect, useCallback } from 'react';

interface StreamingState {
  text: string;
  citations: Map<number, Citation>;
  isComplete: boolean;
}

interface Citation {
  id: string;
  ref_id: number;
  start_pos: number;
  end_pos: number;
  metadata: CitationMetadata;
}

export function useHybridStreaming() {
  const [state, setState] = useState<StreamingState>({
    text: '',
    citations: new Map(),
    isComplete: false
  });
  
  const streamMessage = useCallback(async (message: string) => {
    setState({
      text: '',
      citations: new Map(),
      isComplete: false
    });
    
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) return;
    
    let buffer = '';
    let cumulativeText = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (!line.trim()) continue;
        
        try {
          const event = JSON.parse(line);
          
          if (event.type === 'text') {
            cumulativeText += event.content;
            setState(prev => ({
              ...prev,
              text: cumulativeText
            }));
          } else if (event.type === 'citation') {
            setState(prev => {
              const next = new Map(prev.citations);
              next.set(event.citation.start_pos, event.citation);
              return {
                ...prev,
                citations: next
              };
            });
          } else if (event.type === 'done') {
            setState(prev => ({ ...prev, isComplete: true }));
          }
        } catch (e) {
          console.error('Failed to parse event:', e, line);
        }
      }
    }
  }, []);
  
  return { ...state, streamMessage };
}

// Rendering component
export function HybridCitationRenderer({ 
  text, 
  citations 
}: { 
  text: string; 
  citations: Map<number, Citation> 
}) {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  
  // Sort citations by position
  const sortedCitations = Array.from(citations.values())
    .sort((a, b) => a.start_pos - b.start_pos);
  
  sortedCitations.forEach((citation, idx) => {
    // Text before citation
    if (citation.start_pos > lastIndex) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {text.slice(lastIndex, citation.start_pos)}
        </span>
      );
    }
    
    // Citation button
    parts.push(
      <CitationButton
        key={`cite-${citation.id}`}
        citationId={citation.id}
        refId={citation.ref_id}
      >
        [{idx + 1}]
      </CitationButton>
    );
    
    lastIndex = Math.max(lastIndex, citation.end_pos);
  });
  
  // Remaining text
  if (lastIndex < text.length) {
    parts.push(
      <span key={`text-${lastIndex}`}>
        {text.slice(lastIndex)}
      </span>
    );
  }
  
  return (
    <div className="whitespace-pre-wrap citation-container">
      {parts}
    </div>
  );
}
```

**Pros:**
- ✅ Real-time responsiveness (streaming)
- ✅ Type-safe, validated citations (structured)
- ✅ Exact position tracking
- ✅ Progressive enhancement
- ✅ Best user experience
- ✅ Reliable and maintainable

**Cons:**
- ❌ More complex implementation
- ❌ Requires careful state management
- ❌ Need to handle edge cases (citations before text, etc.)

---

## Comparison Table

| Approach | UX | Reliability | Complexity | Streaming | Best For |
|----------|----|-------------|------------|-----------|----------|
| **Inline Markers** (`{ref:N}`) | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | Quick prototypes |
| **Structured Output** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Partial | Production apps |
| **Position Metadata** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ Complex | Medium complexity |
| **Streaming Events** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ✅ Full | Real-time apps |
| **Hybrid (Recommended)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Full | Best overall |

---

## Recommendations

### For New Projects

**Use the Hybrid Approach:**
1. Stream text chunks for real-time UX
2. Stream structured citation events with position data
3. Combine on frontend with position-based rendering
4. Validate citations as they arrive

### For Existing Projects

**If you have the current inline marker system:**
- Consider migrating to structured output first (easier transition)
- Then add streaming capabilities incrementally
- Keep backward compatibility during migration

### Implementation Priority

1. **Phase 1**: Implement structured output (reliability)
2. **Phase 2**: Add streaming text (UX improvement)
3. **Phase 3**: Add streaming citations (full hybrid)

---

## Key Considerations

### Error Handling

Always handle:
- Partial citations (citation arrives but text doesn't)
- Out-of-order events
- Invalid positions
- Missing citation metadata

### Performance

- Debounce citation updates during rapid streaming
- Use React.memo for citation components
- Virtualize long citation lists
- Lazy load citation metadata

### Accessibility

- Ensure citation buttons are keyboard accessible
- Provide ARIA labels
- Support screen readers
- Maintain focus management

### Testing

Test scenarios:
- Citations before text arrives
- Multiple citations in rapid succession
- Very long responses
- Network interruptions
- Invalid citation data

---

## Example: Complete Hybrid Implementation

See `examples/hybrid-citation-system/` for a full working implementation.

### File Structure
```
hybrid-citation-system/
├── backend/
│   ├── stream_service.py      # Streaming logic
│   └── citation_parser.py     # Citation extraction
├── frontend/
│   ├── useStreamingCitations.ts
│   ├── CitationRenderer.tsx
│   └── CitationButton.tsx
└── README.md
```

---

## Conclusion

While streaming with citation events provides excellent UX, the **hybrid approach** (streaming + structured output) offers the best balance of:
- User experience (real-time, responsive)
- Reliability (type-safe, validated)
- Maintainability (clear structure, testable)

For most production applications, the hybrid approach is recommended.


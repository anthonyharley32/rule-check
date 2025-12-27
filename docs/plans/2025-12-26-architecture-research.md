# AI Architecture Research Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this research plan task-by-task.

**Goal:** Research agent orchestration, tool calling, and agentic RAG patterns to identify the best approach for improving NFHS rules Q&A quality while maintaining <5 second latency.

**Output:** A research document (`docs/research/2025-12-26-ai-architecture-findings.md`) with findings, comparisons, and 2-3 recommended approaches for implementation.

**Context:** Current system uses basic RAG (embed question → vector search → pass chunks to LLM). Failure modes include: wrong source cited, incomplete retrieval, total misses. Target latency is ~5 seconds.

---

## Task 1: Document Current System Baseline

**Files:**
- Read: `backend/functions/chat.py`
- Read: `backend/functions/search.py`
- Create: `docs/research/2025-12-26-ai-architecture-findings.md`

**Step 1: Analyze current implementation**

Read the chat and search files to understand:
- How queries are processed
- How retrieval works (embedding model, vector store, top_k)
- How context is passed to the LLM
- Current latency characteristics

**Step 2: Create research document with baseline section**

```markdown
# AI Architecture Research Findings

## 1. Current System Baseline

### How It Works
[Document the current RAG flow]

### Strengths
- [List what works well]

### Weaknesses
- [List failure modes observed]

### Latency Profile
- Embedding: ~Xms
- Vector search: ~Xms
- LLM generation: ~Xs
- Total: ~Xs
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add current system baseline"
```

---

## Task 2: Research Agent Orchestration Frameworks

**Goal:** Understand how modern agent frameworks structure multi-step workflows.

**Step 1: Research the following frameworks**

Search and read documentation for:
- **LangGraph** - Graph-based agent orchestration (LangChain)
- **CrewAI** - Multi-agent collaboration framework
- **AutoGen** - Microsoft's multi-agent conversation framework
- **LlamaIndex Workflows** - Event-driven agent orchestration

For each, document:
- Core concepts (nodes, edges, agents, tools)
- How state is managed between steps
- How decisions/routing are handled
- Typical latency overhead
- Complexity to implement

**Step 2: Add to research document**

```markdown
## 2. Agent Orchestration Frameworks

### LangGraph
- **Concept:** [How it works]
- **Strengths:** [What it's good at]
- **Weaknesses:** [Limitations]
- **Latency:** [Overhead estimate]
- **Complexity:** [Low/Medium/High]
- **Fit for NFHS:** [Assessment]

### CrewAI
[Same structure]

### AutoGen
[Same structure]

### LlamaIndex Workflows
[Same structure]

### Summary Table
| Framework | Latency Overhead | Complexity | Best For |
|-----------|------------------|------------|----------|
| LangGraph | | | |
| CrewAI | | | |
| AutoGen | | | |
| LlamaIndex | | | |
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add agent orchestration framework comparison"
```

---

## Task 3: Research Tool Calling Patterns

**Goal:** Understand when and how to use LLM tool calling vs. automatic retrieval.

**Step 1: Research tool calling approaches**

Search for information on:
- **Function calling** - LLM decides which tool to call and with what parameters
- **ReAct pattern** - Reasoning + Acting loop (think → act → observe → repeat)
- **Tool-augmented retrieval** - LLM has retrieval as one of several tools
- **Forced vs. optional tools** - When to let LLM choose vs. always retrieve

For each, understand:
- How the LLM decides what to do
- Latency implications (extra LLM calls)
- Reliability (does it make good decisions?)
- When it's better than automatic retrieval

**Step 2: Add to research document**

```markdown
## 3. Tool Calling Patterns

### Function Calling Basics
- How it works with OpenRouter/various models
- Reliability across different LLMs
- Latency cost of tool-calling loop

### ReAct Pattern
- When to use
- Typical number of iterations
- Latency profile

### Tool-Augmented Retrieval
- Retrieval as a tool vs. automatic
- Examples of effective implementations

### Key Decision: When Tool Calling Beats Automatic RAG
| Scenario | Tool Calling Better? | Why |
|----------|---------------------|-----|
| Simple factual lookup | | |
| Multi-step reasoning | | |
| Cross-document synthesis | | |
| Ambiguous query | | |
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add tool calling patterns analysis"
```

---

## Task 4: Research Agentic RAG Patterns

**Goal:** Understand specific patterns for improving RAG with agentic capabilities.

**Step 1: Research these specific patterns**

Deep dive into:
- **Query Routing** - Classify query to pick retrieval source/strategy
- **Query Decomposition** - Break complex queries into sub-queries
- **Query Rewriting/Expansion** - Improve query before retrieval
- **Document Grading** - Evaluate retrieved docs for relevance
- **Self-Correction/Retry** - Detect failures and retry with different approach
- **Hybrid Retrieval** - Dense + sparse + reranking
- **Multi-hop Retrieval** - Follow references across documents

For each pattern:
- How it works
- When to use it
- Latency cost
- Implementation complexity
- Real-world examples

**Step 2: Add to research document**

```markdown
## 4. Agentic RAG Patterns

### Query Routing
- **How it works:** [Description]
- **When to use:** [Scenarios]
- **Latency cost:** [Estimate]
- **NFHS application:** [How it would help]

### Query Decomposition
[Same structure]

### Query Rewriting
[Same structure]

### Document Grading
[Same structure]

### Self-Correction
[Same structure]

### Hybrid Retrieval
[Same structure]

### Multi-hop Retrieval
[Same structure]

### Pattern Combinations
Which patterns work well together? Which conflict?
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add agentic RAG patterns analysis"
```

---

## Task 5: Research Domain-Specific Examples

**Goal:** Find examples of similar systems (Q&A over rulebooks, legal docs, reference materials).

**Step 1: Search for relevant case studies**

Look for:
- Legal document Q&A systems
- Compliance/regulatory Q&A
- Technical documentation assistants
- Multi-document reference systems

Document:
- What architecture they used
- What challenges they faced
- What worked well
- Latency they achieved

**Step 2: Add to research document**

```markdown
## 5. Domain-Specific Case Studies

### Legal Document RAG Systems
- [Examples and learnings]

### Regulatory/Compliance Q&A
- [Examples and learnings]

### Technical Documentation Assistants
- [Examples and learnings]

### Key Learnings for NFHS
- [Patterns that apply to our use case]
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add domain-specific case studies"
```

---

## Task 6: Latency Analysis & Constraints

**Goal:** Map out what's achievable within the 5-second target.

**Step 1: Research latency benchmarks**

Find data on:
- LLM inference times (various models via OpenRouter)
- Embedding latency
- Vector search latency (Supabase/pgvector)
- Network overhead

**Step 2: Model different architectures**

Calculate estimated latency for:
- Current basic RAG
- RAG + Query Routing (1 extra LLM call)
- RAG + Document Grading (1 extra LLM call)
- RAG + Query Decomposition (N sub-queries)
- Full agentic loop (multiple iterations)

**Step 3: Add to research document**

```markdown
## 6. Latency Analysis

### Component Latency Benchmarks
| Component | Typical Latency | Notes |
|-----------|-----------------|-------|
| Embedding (OpenAI) | ~100-200ms | |
| Vector search (pgvector) | ~50-100ms | |
| LLM call (Gemini Flash) | ~1-3s | |
| LLM call (GPT-4o) | ~2-5s | |

### Architecture Latency Estimates
| Architecture | Estimated Total | Feasible (<5s)? |
|--------------|-----------------|-----------------|
| Basic RAG | ~2-4s | Yes |
| + Query Routing | ~3-5s | Maybe |
| + Document Grading | ~4-7s | Borderline |
| + Query Decomposition | ~6-10s | No (without optimization) |
| Full Agentic | ~10-20s | No |

### Optimization Strategies
- Parallel retrieval
- Streaming
- Smaller/faster models for routing
- Caching
```

**Step 3: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add latency analysis"
```

---

## Task 7: Synthesize Findings & Recommendations

**Goal:** Distill research into actionable recommendations.

**Step 1: Map patterns to failure modes**

| Failure Mode | Patterns That Help | Latency Impact |
|--------------|-------------------|----------------|
| Wrong source cited | Query Routing | Low |
| Incomplete retrieval | Hybrid Retrieval, Query Expansion | Low |
| Total miss | Document Grading + Retry | Medium |
| Complex cross-ref questions | Query Decomposition | High |

**Step 2: Define 2-3 candidate architectures**

For each candidate:
- Which patterns it uses
- Expected latency
- Implementation complexity
- Which failure modes it addresses

**Step 3: Write recommendations section**

```markdown
## 7. Recommendations

### Failure Mode → Pattern Mapping
[Table from Step 1]

### Candidate Architecture 1: [Name]
- **Patterns:** [List]
- **Flow:** [Diagram or description]
- **Expected latency:** [Estimate]
- **Complexity:** [Low/Medium/High]
- **Addresses:** [Which failure modes]
- **Tradeoffs:** [Pros/cons]

### Candidate Architecture 2: [Name]
[Same structure]

### Candidate Architecture 3: [Name]
[Same structure]

### Comparison Matrix
| Criteria | Candidate 1 | Candidate 2 | Candidate 3 |
|----------|-------------|-------------|-------------|
| Latency | | | |
| Complexity | | | |
| Failure modes addressed | | | |
| Risk | | | |

### Recommendation
[Which candidate to pursue and why]
```

**Step 4: Commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): add synthesis and recommendations"
```

---

## Task 8: Review & Finalize

**Step 1: Review full document for completeness**

Ensure all sections are filled out with substantive findings.

**Step 2: Add executive summary at top**

```markdown
## Executive Summary

**Problem:** Current basic RAG system has retrieval quality issues - wrong sources, incomplete retrieval, total misses.

**Research Scope:** Agent orchestration frameworks, tool calling patterns, agentic RAG patterns, domain-specific examples, latency constraints.

**Key Finding:** [One sentence]

**Recommendation:** [One sentence describing recommended approach]

**Next Step:** Create implementation plan for [recommended architecture].
```

**Step 3: Final commit**

```bash
git add docs/research/2025-12-26-ai-architecture-findings.md
git commit -m "docs(research): finalize AI architecture research"
```

---

## Summary

| Task | Focus | Output |
|------|-------|--------|
| 1 | Current system baseline | Understanding of what exists |
| 2 | Agent orchestration frameworks | Framework comparison |
| 3 | Tool calling patterns | When to use tool calling |
| 4 | Agentic RAG patterns | Specific improvement patterns |
| 5 | Domain examples | Real-world learnings |
| 6 | Latency analysis | What's feasible in 5s |
| 7 | Synthesis | 2-3 candidate architectures |
| 8 | Finalize | Executive summary + recommendation |

**After completion:** Review findings together, pick an architecture, then create Plan 3 (Implementation).

# NFHS Benchmark System

A LangSmith-based benchmark system for evaluating the NFHS Rules Chat API quality.

## Overview

This benchmark tests the chat API against 50 verified questions covering:
- **Pure Rules** (20 questions): Direct rule definitions and explanations
- **Mechanics** (8 questions): Official mechanics and signals
- **Scenarios** (19 questions): Game situation applications
- **Challenge** (3 questions): Edge cases and trick questions

## Scoring

Each question is evaluated on three dimensions (max 5 points per question):

| Evaluator | Score Range | Description |
|-----------|-------------|-------------|
| Correctness | 0-2 | Is the answer factually correct? |
| Source Precision | 0-2 | Are the right sources cited without wrong ones? |
| Completeness | 0-1 | Does the answer cover all required aspects? |

**Max Score: 250 points** (50 questions x 5 points each)

## Setup

### Prerequisites

1. LangSmith account with API key
2. OpenRouter API key (for LLM-based evaluation)
3. Running NFHS Chat API

### Environment Variables

```bash
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=nfhs-benchmark
OPENROUTER_API_KEY=your_openrouter_api_key
API_BASE_URL=http://localhost:8000  # or production URL
```

## Usage

### 1. Create/Update Dataset

Upload questions from `questions.json` to LangSmith:

```bash
cd backend/benchmark
python run_benchmark.py --create-dataset
```

This creates the dataset `nfhs-benchmark-v1` in LangSmith.

### 2. Run Benchmark

Execute the benchmark against the chat API:

```bash
# Run against local API
python run_benchmark.py --run

# Run against production
python run_benchmark.py --run --api-url https://api.production.com

# Custom experiment name
python run_benchmark.py --run --prefix "post-fix-v2"
```

### 3. View Results

Results are available in the LangSmith dashboard:
1. Go to https://smith.langchain.com
2. Navigate to your project
3. Find the experiment by name (e.g., `nfhs-benchmark-20241226-143022`)

## File Structure

```
backend/benchmark/
  __init__.py           # Module init
  evaluators.py         # LangSmith evaluator functions
  run_benchmark.py      # CLI runner
  questions.json        # Source of truth for benchmark questions
  README.md             # This file
```

## Question Format

Each question in `questions.json` follows this structure:

```json
{
  "id": "q001",
  "question": "What is a double dribble?",
  "expected_answer": "A double dribble violation occurs when...",
  "required_sources": ["Rule 4-15"],
  "acceptable_sources": ["Case 4.15.1 SITUATION A"],
  "category": "pure_rules",
  "difficulty": "easy"
}
```

- **required_sources**: Must be cited for full source precision score
- **acceptable_sources**: Valid but not required citations
- **category**: pure_rules | mechanics | scenarios | challenge
- **difficulty**: easy | medium | hard

## Evaluators

### Correctness (LLM-graded)
Uses Gemini 2.0 Flash to compare actual answer against expected answer.
- 0 = Wrong answer
- 1 = Partially correct
- 2 = Fully correct

### Source Precision (Rule-based)
Checks citation accuracy:
- 0 = No sources or all wrong sources
- 1 = Has required sources OR has some valid sources
- 2 = All required sources, no wrong sources

### Completeness (LLM-graded)
Only scored if correctness = 2. Checks if all aspects are covered.
- 0 = Missing aspects
- 1 = Complete

## Adding Questions

1. Add questions to `questions.json`
2. Run `python run_benchmark.py --create-dataset` to upload
3. Note: LangSmith will add to existing dataset (duplicates possible)

## Maintenance

The `questions.json` file is the source of truth. After verification:
- All 50 questions have been verified against NFHS rulebook and casebook
- Case references use specific format: `Case X.Y.Z SITUATION A`
- Answers reflect current 2024-25 rules

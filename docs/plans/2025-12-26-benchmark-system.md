# NFHS Benchmark System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an automated benchmark using LangSmith to measure and track AI response quality for NFHS basketball officiating questions.

**Architecture:** LangSmith Dataset holds 50 questions with ground truth. Three Python evaluators score responses on Correctness (0-2), Source Precision (0-2), and Completeness (0-1, conditional). Experiments run questions through the existing `/chat` endpoint and auto-grade results.

**Tech Stack:** LangSmith SDK, Python, existing FastAPI backend

---

## Scoring Rubric Reference

**Correctness (0-2):**
| Score | Criteria |
|-------|----------|
| 0 | Wrong answer |
| 1 | Partially correct |
| 2 | Fully correct |

**Source Precision (0-2):**
| Score | Criteria |
|-------|----------|
| 0 | Wrong sources, or no sources cited |
| 1 | Partial - missing required sources, OR has all required but includes wrong sources |
| 2 | All required sources cited, no incorrect sources |

**Completeness (0-1) - only evaluated if Correctness = 2:**
| Score | Criteria |
|-------|----------|
| 0 | Correct but missing aspects (e.g., lists 2 of 3 ways to travel) |
| 1 | Covers everything needed |
| N/A | If Correctness < 2, Completeness = 0 automatically |

**Max score: 5 points per question, 250 total**

---

## Task 1: Set Up Benchmark Directory Structure

**Files:**
- Create: `backend/benchmark/__init__.py`
- Create: `backend/benchmark/evaluators.py`
- Create: `backend/benchmark/run_benchmark.py`
- Create: `backend/benchmark/questions.json`

**Step 1: Create benchmark directory**

```bash
mkdir -p backend/benchmark
```

**Step 2: Create __init__.py**

```python
"""Benchmark system for NFHS Rules Chat."""
```

**Step 3: Commit**

```bash
git add backend/benchmark/__init__.py
git commit -m "chore: add benchmark directory structure"
```

---

## Task 2: Create Evaluator Functions

**Files:**
- Create: `backend/benchmark/evaluators.py`

**Step 1: Write the evaluators file**

```python
"""LangSmith evaluators for NFHS benchmark."""

import re
from langsmith.schemas import Example, Run
from openai import OpenAI
import os


def get_llm_client():
    """Get OpenAI client for LLM-based evaluation."""
    return OpenAI(
        api_key=os.getenv('OPENROUTER_API_KEY'),
        base_url="https://openrouter.ai/api/v1"
    )


def extract_citations(text: str) -> set[str]:
    """
    Extract citation references from response text.
    Looks for patterns like [1], [2], etc. and maps to source_refs.
    """
    # Find all [N] patterns
    matches = re.findall(r'\[(\d+)\]', text)
    return set(matches)


def correctness_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluate correctness of the answer.

    Returns:
        {"key": "correctness", "score": 0|1|2}
        0 = Wrong answer
        1 = Partially correct
        2 = Fully correct
    """
    actual_answer = run.outputs.get("answer", "")
    expected_answer = example.outputs.get("expected_answer", "")

    client = get_llm_client()

    prompt = f"""You are evaluating an AI's answer about NFHS basketball rules.

EXPECTED ANSWER (ground truth):
{expected_answer}

ACTUAL ANSWER (to evaluate):
{actual_answer}

Score the actual answer's correctness:
- 0 = Wrong answer (factually incorrect or completely misses the point)
- 1 = Partially correct (some correct information but has errors or significant gaps)
- 2 = Fully correct (factually accurate, addresses the question properly)

Respond with ONLY a JSON object:
{{"score": <0|1|2>, "reasoning": "<brief explanation>"}}"""

    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result_text = response.choices[0].message.content

    # Parse JSON from response
    import json
    try:
        # Handle potential markdown code blocks
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text.strip())
        score = result.get("score", 0)
    except (json.JSONDecodeError, IndexError):
        score = 0

    return {"key": "correctness", "score": score}


def source_precision_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluate source citation precision.

    Returns:
        {"key": "source_precision", "score": 0|1|2}
        0 = Wrong sources or no sources cited
        1 = Partial - missing required OR has extra wrong sources
        2 = All required sources, no incorrect sources
    """
    actual_answer = run.outputs.get("answer", "")
    citations_used = run.outputs.get("citations", [])

    required_sources = set(example.outputs.get("required_sources", []))
    acceptable_sources = set(example.outputs.get("acceptable_sources", []))
    all_valid_sources = required_sources | acceptable_sources

    # Extract which citation numbers were used in the text
    cited_numbers = extract_citations(actual_answer)

    # Map citation numbers to source_refs
    cited_sources = set()
    for citation in citations_used:
        ref_num = str(citation.get("ref_num", ""))
        if ref_num in cited_numbers:
            source_ref = citation.get("source_ref", "")
            cited_sources.add(source_ref)

    # Check if no sources cited
    if not cited_sources:
        return {"key": "source_precision", "score": 0}

    # Check for wrong sources (not in valid set)
    # Note: This is approximate - source_ref format may vary
    has_wrong_sources = False
    has_required = False

    for cited in cited_sources:
        # Check if this cited source matches any required/acceptable
        matches_valid = any(
            valid.lower() in cited.lower() or cited.lower() in valid.lower()
            for valid in all_valid_sources
        )
        if not matches_valid:
            has_wrong_sources = True

        matches_required = any(
            req.lower() in cited.lower() or cited.lower() in req.lower()
            for req in required_sources
        )
        if matches_required:
            has_required = True

    # Score logic
    if has_required and not has_wrong_sources:
        return {"key": "source_precision", "score": 2}
    elif has_required or (cited_sources and not has_wrong_sources):
        return {"key": "source_precision", "score": 1}
    else:
        return {"key": "source_precision", "score": 0}


def completeness_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluate completeness of the answer.
    Only scored if correctness = 2, otherwise returns 0.

    Returns:
        {"key": "completeness", "score": 0|1}
        0 = Missing aspects OR correctness < 2
        1 = Covers everything needed
    """
    actual_answer = run.outputs.get("answer", "")
    expected_answer = example.outputs.get("expected_answer", "")

    # First check correctness - if not fully correct, completeness is 0
    correctness_result = correctness_evaluator(run, example)
    if correctness_result["score"] < 2:
        return {"key": "completeness", "score": 0}

    client = get_llm_client()

    prompt = f"""You are evaluating whether an AI's answer is COMPLETE.

The answer has already been verified as CORRECT. Now check if it covers ALL aspects.

EXPECTED ANSWER (contains all required aspects):
{expected_answer}

ACTUAL ANSWER (to evaluate for completeness):
{actual_answer}

Does the actual answer cover ALL key aspects from the expected answer?
- 0 = Missing aspects (e.g., if expected lists 3 scenarios but actual only mentions 2)
- 1 = Complete (covers everything needed)

Respond with ONLY a JSON object:
{{"score": <0|1>, "reasoning": "<brief explanation>"}}"""

    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result_text = response.choices[0].message.content

    import json
    try:
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text.strip())
        score = result.get("score", 0)
    except (json.JSONDecodeError, IndexError):
        score = 0

    return {"key": "completeness", "score": score}
```

**Step 2: Commit**

```bash
git add backend/benchmark/evaluators.py
git commit -m "feat(benchmark): add LangSmith evaluators for correctness, source precision, completeness"
```

---

## Task 3: Create Benchmark Runner Script

**Files:**
- Create: `backend/benchmark/run_benchmark.py`

**Step 1: Write the benchmark runner**

```python
"""Run benchmark experiments against the NFHS chat API."""

import os
import json
import requests
from datetime import datetime
from langsmith import Client
from langsmith.evaluation import evaluate
from dotenv import load_dotenv

load_dotenv()

from evaluators import (
    correctness_evaluator,
    source_precision_evaluator,
    completeness_evaluator
)

# Configuration
LANGSMITH_DATASET_NAME = "nfhs-benchmark-v1"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def target_function(inputs: dict) -> dict:
    """
    Call the chat API with the question and return the response.
    This is what LangSmith will evaluate.
    """
    question = inputs["question"]

    response = requests.post(
        f"{API_BASE_URL}/chat",
        json={"question": question, "top_k": 5},
        timeout=30
    )

    if response.status_code != 200:
        return {"answer": f"Error: {response.status_code}", "citations": []}

    data = response.json()
    return {
        "answer": data.get("answer", ""),
        "citations": data.get("citations", [])
    }


def run_benchmark(experiment_prefix: str = None):
    """
    Run the full benchmark and return results.

    Args:
        experiment_prefix: Optional prefix for experiment name.
                          Defaults to timestamp.
    """
    if experiment_prefix is None:
        experiment_prefix = datetime.now().strftime("%Y%m%d-%H%M%S")

    experiment_name = f"nfhs-benchmark-{experiment_prefix}"

    print(f"Running benchmark experiment: {experiment_name}")
    print(f"Dataset: {LANGSMITH_DATASET_NAME}")
    print(f"API: {API_BASE_URL}")
    print("-" * 50)

    results = evaluate(
        target_function,
        data=LANGSMITH_DATASET_NAME,
        evaluators=[
            correctness_evaluator,
            source_precision_evaluator,
            completeness_evaluator
        ],
        experiment_prefix=experiment_name,
    )

    print("-" * 50)
    print(f"Benchmark complete! View results in LangSmith dashboard.")
    print(f"Experiment: {experiment_name}")

    return results


def create_dataset_from_json(json_path: str = "questions.json"):
    """
    Create or update the LangSmith dataset from local JSON file.
    """
    client = Client()

    with open(json_path, "r") as f:
        data = json.load(f)

    questions = data["questions"]

    # Create dataset if it doesn't exist
    try:
        dataset = client.create_dataset(
            dataset_name=LANGSMITH_DATASET_NAME,
            description="NFHS Basketball Rules benchmark - 50 questions across rules, mechanics, scenarios"
        )
        print(f"Created dataset: {LANGSMITH_DATASET_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower():
            dataset = client.read_dataset(dataset_name=LANGSMITH_DATASET_NAME)
            print(f"Using existing dataset: {LANGSMITH_DATASET_NAME}")
        else:
            raise

    # Add examples
    for q in questions:
        client.create_example(
            inputs={"question": q["question"]},
            outputs={
                "expected_answer": q["expected_answer"],
                "required_sources": q["required_sources"],
                "acceptable_sources": q.get("acceptable_sources", []),
                "category": q["category"],
                "difficulty": q["difficulty"]
            },
            dataset_id=dataset.id,
            metadata={
                "id": q["id"],
                "category": q["category"],
                "difficulty": q["difficulty"],
                "tags": q.get("tags", [])
            }
        )

    print(f"Added {len(questions)} examples to dataset")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NFHS Benchmark Runner")
    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create/update LangSmith dataset from questions.json"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run benchmark experiment"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Experiment name prefix"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Override API base URL"
    )

    args = parser.parse_args()

    if args.api_url:
        API_BASE_URL = args.api_url

    if args.create_dataset:
        create_dataset_from_json()

    if args.run:
        run_benchmark(experiment_prefix=args.prefix)

    if not args.create_dataset and not args.run:
        parser.print_help()
```

**Step 2: Commit**

```bash
git add backend/benchmark/run_benchmark.py
git commit -m "feat(benchmark): add benchmark runner script with LangSmith integration"
```

---

## Task 4: Create Initial Questions File (Seed Questions)

**Files:**
- Create: `backend/benchmark/questions.json`

**Step 1: Create questions file with user's seed questions**

```json
{
  "questions": [
    {
      "id": "q001",
      "question": "What is a double dribble?",
      "expected_answer": "A double dribble violation occurs when a player dribbles the ball, allows it to come to rest in one or both hands, and then dribbles again. It also occurs when a player dribbles the ball with both hands simultaneously.",
      "required_sources": ["Rule 4-15"],
      "acceptable_sources": ["Case 4.15"],
      "category": "pure_rules",
      "difficulty": "easy",
      "tags": ["violations", "dribbling"]
    },
    {
      "id": "q002",
      "question": "What is a goaltend?",
      "expected_answer": "Goaltending occurs when a player touches the ball during a field goal try or tap while the ball is in its downward flight entirely above the basket ring level, or touches the ball while it is on or within the basket, or touches the basket or net while the ball is on or within the basket.",
      "required_sources": ["Rule 4-22"],
      "acceptable_sources": ["Case 4.22"],
      "category": "pure_rules",
      "difficulty": "easy",
      "tags": ["violations", "goaltending"]
    },
    {
      "id": "q003",
      "question": "Where does it say anything about landing space of the shooter in the rule book?",
      "expected_answer": "Rule 4-7-2 defines the airborne shooter and their protection. The defender must provide the shooter with a safe landing area. If a defender causes contact with an airborne shooter that is not incidental, it is a foul.",
      "required_sources": ["Rule 4-7-2", "Rule 10-6-1"],
      "acceptable_sources": ["Case 4.7.2"],
      "category": "pure_rules",
      "difficulty": "medium",
      "tags": ["fouls", "airborne shooter", "landing space"]
    },
    {
      "id": "q004",
      "question": "In three man mechanics, if the lead is table side and makes a foul call, what does the center do?",
      "expected_answer": "When the tableside Lead makes a foul call in three-person mechanics, the Center rotates to become the new Lead on the opposite side of the court. The Trail remains as Trail.",
      "required_sources": ["Manual 7"],
      "acceptable_sources": [],
      "category": "mechanics",
      "difficulty": "medium",
      "tags": ["three-person mechanics", "rotations", "foul coverage"]
    },
    {
      "id": "q005",
      "question": "In 2 man mechanics and 3 man mechanics, do the T/L and the C/L watch the same lane players or is it different?",
      "expected_answer": "The coverage differs between 2-person and 3-person mechanics. In 2-person mechanics, the Lead watches the three players on their side of the lane. In 3-person mechanics, with a Center official added, the responsibilities are distributed differently with the Center covering the middle area.",
      "required_sources": ["Manual"],
      "acceptable_sources": [],
      "category": "mechanics",
      "difficulty": "hard",
      "tags": ["mechanics comparison", "lane coverage", "free throws"]
    },
    {
      "id": "q006",
      "question": "Can the thrower run the end line after an offensive free throw violation?",
      "expected_answer": "No. The thrower may only run the end line after a made basket (goal) or awarded goal. A free throw violation results in a throw-in from the designated spot, not a running end line situation.",
      "required_sources": ["Rule 7-5-7"],
      "acceptable_sources": ["Case 7.5.7"],
      "category": "scenarios",
      "difficulty": "hard",
      "tags": ["throw-in", "end line", "free throw violations"]
    },
    {
      "id": "q007",
      "question": "Does getting a team technical (slapping ball on throw-in) eat up the delay of game warning?",
      "expected_answer": "No. A team technical foul for slapping the ball on a throw-in is a separate penalty from the delay of game warning system. The delay of game warning is specifically for delay violations, and a technical foul is assessed independently.",
      "required_sources": ["Rule 10-1", "Rule 10-2"],
      "acceptable_sources": ["Case 10.1", "Case 10.2"],
      "category": "scenarios",
      "difficulty": "hard",
      "tags": ["technical fouls", "delay of game", "warnings"]
    },
    {
      "id": "q008",
      "question": "Where does it say that dribble-fumble-dribble = violation?",
      "expected_answer": "A fumble is the accidental loss of player control. Rule 4-15-4 states that after a player has ended their dribble, they may not dribble again. However, recovering a fumble is not considered starting a new dribble. The sequence dribble-fumble-dribble is NOT a violation if the fumble was accidental.",
      "required_sources": ["Rule 4-15", "Rule 4-25"],
      "acceptable_sources": ["Case 4.15", "Case 4.25"],
      "category": "challenge",
      "difficulty": "hard",
      "tags": ["violations", "dribbling", "fumble", "trick question"]
    },
    {
      "id": "q009",
      "question": "What do you do in a block/charge situation?",
      "expected_answer": "In a block/charge situation, officials must determine: (1) Did the defender establish legal guarding position before the opponent started their upward motion to shoot or pass? (2) Was the defender stationary or moving? (3) Did the defender give the airborne shooter room to land? If the defender was not in legal position, it's a blocking foul. If they were, it's a player control foul (charge).",
      "required_sources": ["Rule 4-7", "Rule 4-23", "Rule 10-6"],
      "acceptable_sources": ["Case 4.7", "Case 10.6"],
      "category": "scenarios",
      "difficulty": "medium",
      "tags": ["fouls", "block charge", "legal guarding position"]
    },
    {
      "id": "q010",
      "question": "What does 'false' mean in terms of a double or multiple foul?",
      "expected_answer": "A false double foul or false multiple foul occurs when there are fouls by both teams, but the fouls are not committed at approximately the same time, or when one of the fouls is not a personal foul. In a false double foul situation, the penalties are administered in the order they occurred rather than offsetting.",
      "required_sources": ["Rule 4-19-8", "Rule 4-19-9"],
      "acceptable_sources": ["Case 4.19"],
      "category": "pure_rules",
      "difficulty": "medium",
      "tags": ["fouls", "double foul", "false double foul"]
    },
    {
      "id": "q011",
      "question": "Is the ball live during technical free throws?",
      "expected_answer": "No. The ball becomes live when it is at the disposal of the free thrower. During technical foul free throws, no players line up on the lane, and the ball does not become live in the same way as during personal foul free throws.",
      "required_sources": ["Rule 6-1"],
      "acceptable_sources": ["Case 6.1"],
      "category": "pure_rules",
      "difficulty": "medium",
      "tags": ["free throws", "live ball", "technical fouls"]
    },
    {
      "id": "q012",
      "question": "Is it a delay of game for not filling both bottom lane spaces? Technical?",
      "expected_answer": "Teams are required to fill the first marked lane spaces on each side during free throws when entitled to do so. Failure to properly fill the lane spaces can result in a delay of game warning for the first offense, and a technical foul for subsequent offenses.",
      "required_sources": ["Rule 10-1-5", "Rule 9-1-3"],
      "acceptable_sources": ["Case 10.1"],
      "category": "scenarios",
      "difficulty": "hard",
      "tags": ["delay of game", "free throws", "lane spaces"]
    }
  ]
}
```

**Step 2: Commit**

```bash
git add backend/benchmark/questions.json
git commit -m "feat(benchmark): add seed questions from user input"
```

---

## Task 5: Add Remaining Questions from Casebook

**Files:**
- Modify: `backend/benchmark/questions.json`

**Step 1: Read the casebook to extract ~20 good scenario questions**

Read: `books/nfhs_basketball_casebook_2025-26.md`

Look for well-defined situations with clear rulings. Add them to questions.json following the same format.

**Step 2: Add ~10 harder rulebook questions**

Examples to add:
- "When does the ball become live on a free throw?"
- "What are the restrictions on the thrower during a throw-in?"
- "When can a player re-enter the game after being disqualified?"
- "What constitutes a held ball?"

**Step 3: Add ~8 mechanics questions from officials manual**

Read: `books/nfhs_basketball_officials_manual_2025-27.md`

Examples:
- "Where does the Lead position themselves during a throw-in on the end line?"
- "What is the proper signal sequence for a traveling violation?"

**Step 4: Verify distribution**

Ensure final count:
- ~15 pure_rules
- ~10 mechanics
- ~15 scenarios
- ~10 challenge

And difficulty:
- ~15 easy (30%)
- ~25 medium (50%)
- ~10 hard (20%)

**Step 5: Commit**

```bash
git add backend/benchmark/questions.json
git commit -m "feat(benchmark): complete 50-question benchmark set"
```

---

## Task 6: Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add langsmith to requirements**

Add to `backend/requirements.txt`:
```
langsmith>=0.1.0
```

**Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add langsmith dependency for benchmark"
```

---

## Task 7: Create Usage Documentation

**Files:**
- Create: `backend/benchmark/README.md`

**Step 1: Write documentation**

```markdown
# NFHS Benchmark System

Automated benchmark for measuring AI response quality on NFHS basketball rules questions.

## Setup

1. Ensure you have LangSmith API key in your environment:
   ```bash
   export LANGSMITH_API_KEY=your_key_here
   ```

2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Create the LangSmith dataset (first time only):
   ```bash
   cd backend/benchmark
   python run_benchmark.py --create-dataset
   ```

## Running Benchmarks

### Run against local server

```bash
# Start your server first
cd backend
python main.py

# In another terminal, run benchmark
cd backend/benchmark
python run_benchmark.py --run
```

### Run against production

```bash
python run_benchmark.py --run --api-url https://your-production-url.com
```

### Name your experiment

```bash
python run_benchmark.py --run --prefix "after-rag-improvement"
```

## Viewing Results

1. Go to [LangSmith Dashboard](https://smith.langchain.com)
2. Navigate to your project
3. Click on "Datasets & Experiments"
4. Select `nfhs-benchmark-v1`
5. View experiment results, compare runs

## Scoring

Each question is scored on 3 criteria (max 5 points):

| Metric | Range | Description |
|--------|-------|-------------|
| Correctness | 0-2 | Is the answer factually accurate? |
| Source Precision | 0-2 | Did it cite the right sources? |
| Completeness | 0-1 | Did it cover everything? (only if Correctness=2) |

**Total: 250 points possible (50 questions x 5 points)**

## Adding Questions

Edit `questions.json` and re-run:
```bash
python run_benchmark.py --create-dataset
```

## Question Categories

- `pure_rules` - Direct rule lookups
- `mechanics` - Officials manual positioning/signals
- `scenarios` - Game situations requiring rule application
- `challenge` - Edge cases, cross-book synthesis
```

**Step 2: Commit**

```bash
git add backend/benchmark/README.md
git commit -m "docs(benchmark): add usage documentation"
```

---

## Task 8: Test the Benchmark System

**Step 1: Start local server**

```bash
cd backend
source venv/bin/activate
python main.py
```

**Step 2: Create dataset in LangSmith**

```bash
cd backend/benchmark
python run_benchmark.py --create-dataset
```

Expected: "Created dataset: nfhs-benchmark-v1" and "Added 12 examples to dataset"

**Step 3: Run benchmark with seed questions**

```bash
python run_benchmark.py --run --prefix "initial-test"
```

Expected: Benchmark runs, results visible in LangSmith dashboard

**Step 4: Verify in LangSmith dashboard**

- Go to LangSmith
- Check dataset exists with examples
- Check experiment ran with scores
- Verify evaluators produced 0/1/2 scores

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix(benchmark): adjustments from initial test run"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Directory structure | `backend/benchmark/__init__.py` |
| 2 | Evaluator functions | `backend/benchmark/evaluators.py` |
| 3 | Benchmark runner | `backend/benchmark/run_benchmark.py` |
| 4 | Seed questions (12) | `backend/benchmark/questions.json` |
| 5 | Complete questions (50) | `backend/benchmark/questions.json` |
| 6 | Dependencies | `backend/requirements.txt` |
| 7 | Documentation | `backend/benchmark/README.md` |
| 8 | End-to-end test | - |

**After completion:** Run benchmark before any AI/RAG changes to establish baseline scores.

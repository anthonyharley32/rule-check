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

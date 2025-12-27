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

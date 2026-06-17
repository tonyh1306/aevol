"""
Seed the platform with demo data: a dataset, two experiments, and synthetic metrics.
Run: python scripts/seed_demo_data.py
"""
import asyncio
import json
import os
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import httpx

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        print("Seeding demo data...")

        # 1. Create dataset
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=["question", "context", "expected_answer"])
        writer.writeheader()
        qa_pairs = [
            ("What is the capital of France?", "France is a country in Western Europe.", "Paris"),
            ("What is 2 + 2?", "Basic arithmetic.", "4"),
            ("Who wrote Romeo and Juliet?", "It is a famous tragedy.", "William Shakespeare"),
            ("What is the boiling point of water?", "At sea level.", "100 degrees Celsius"),
            ("What planet is closest to the Sun?", "In our solar system.", "Mercury"),
            ("What year did World War II end?", "The war involved many nations.", "1945"),
            ("What is the chemical symbol for gold?", "From the periodic table.", "Au"),
            ("How many continents are there?", "On Earth.", "7"),
            ("What is the largest ocean?", "On Earth.", "Pacific Ocean"),
            ("Who invented the telephone?", "In the 19th century.", "Alexander Graham Bell"),
        ]
        for q, ctx, ans in qa_pairs * 5:  # 50 rows
            writer.writerow({
                "question": q,
                "context": ctx,
                "expected_answer": ans,
            })

        files = {"file": ("demo_qa.csv", csv_content.getvalue().encode(), "text/csv")}
        data = {"name": "Demo QA Dataset", "description": "50 question-answer pairs for demo purposes"}
        r = await client.post("/api/v1/datasets/upload", files=files, data=data)
        r.raise_for_status()
        dataset = r.json()
        dataset_id = dataset["id"]
        print(f"  Dataset created: {dataset_id} ({dataset['row_count']} rows)")

        # 2. Create baseline experiment
        r = await client.post("/api/v1/experiments", json={
            "name": "Baseline — exact_match",
            "description": "Baseline evaluation using exact string matching",
            "dataset_id": dataset_id,
            "model_name": "claude-haiku-4-5-20251001",
            "tags": ["baseline", "demo"],
            "config": {"evaluator_type": "exact_match", "normalize": True},
        })
        r.raise_for_status()
        baseline = r.json()
        baseline_id = baseline["id"]
        print(f"  Baseline experiment: {baseline_id}")

        # 3. Create candidate experiment
        r = await client.post("/api/v1/experiments", json={
            "name": "Candidate — embedding_similarity",
            "description": "Candidate using embedding similarity scoring",
            "dataset_id": dataset_id,
            "model_name": "claude-haiku-4-5-20251001",
            "tags": ["candidate", "demo"],
            "config": {"evaluator_type": "embedding_similarity", "threshold": 0.6},
        })
        r.raise_for_status()
        candidate = r.json()
        candidate_id = candidate["id"]
        print(f"  Candidate experiment: {candidate_id}")

        print("\nDemo data seeded successfully!")
        print(f"  Dataset ID:   {dataset_id}")
        print(f"  Baseline ID:  {baseline_id}")
        print(f"  Candidate ID: {candidate_id}")
        print(f"\nVisit http://localhost to see the dashboard.")
        print(f"Run each experiment via the UI or:")
        print(f"  POST /api/v1/experiments/{baseline_id}/run")
        print(f"  POST /api/v1/experiments/{candidate_id}/run")


if __name__ == "__main__":
    asyncio.run(main())

"""
Benchmark worker throughput by submitting N tasks and timing completion.
Run: python scripts/benchmark_workers.py --tasks 100 --workers 5
"""
import asyncio
import argparse
import time
import httpx
import os

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def run_benchmark(n_tasks: int):
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        # Create a small dataset
        import csv, io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["question", "expected_answer"])
        writer.writeheader()
        for i in range(n_tasks):
            writer.writerow({"question": f"What is {i} + {i}?", "expected_answer": str(i * 2)})
        files = {"file": ("bench.csv", buf.getvalue().encode(), "text/csv")}
        data = {"name": f"Benchmark {n_tasks} tasks"}
        r = await client.post("/api/v1/datasets/upload", files=files, data=data)
        dataset_id = r.json()["id"]

        r = await client.post("/api/v1/experiments", json={
            "name": f"Benchmark Run {time.time():.0f}",
            "dataset_id": dataset_id,
            "config": {"evaluator_type": "exact_match"},
        })
        exp_id = r.json()["id"]

        start = time.monotonic()
        await client.post(f"/api/v1/experiments/{exp_id}/run")

        # Poll until complete
        while True:
            r = await client.get(f"/api/v1/experiments/{exp_id}")
            exp = r.json()
            done = exp["completed_tasks"] + exp["failed_tasks"]
            total = exp["total_tasks"]
            if total > 0:
                print(f"\r  {done}/{total} tasks ({100*done//total}%)", end="", flush=True)
            if exp["status"] in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(1)

        elapsed = time.monotonic() - start
        exp = r.json()
        print(f"\n\nBenchmark complete:")
        print(f"  Tasks: {exp['completed_tasks']} completed, {exp['failed_tasks']} failed")
        print(f"  Time:  {elapsed:.1f}s")
        print(f"  Throughput: {n_tasks / elapsed:.1f} tasks/sec")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.tasks))

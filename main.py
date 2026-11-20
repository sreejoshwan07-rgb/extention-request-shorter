#!/usr/bin/env python3
"""
CIT AI-Native Engineering Programme · Semester 1 · Assessment 5
Main Console Entrypoint: Extension Request Sorter

Usage:
    python main.py
    python main.py --courses courses.csv --requests requests.csv --out .
"""

import sys
import argparse
from sorter import (
    load_courses,
    load_requests,
    classify,
    is_valid,
    recommend,
    write_reports,
    process_all_requests
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="CIT Extension Request Sorter: Triage student assignment extension requests using LLM extraction and deterministic Python policy."
    )
    parser.add_argument(
        "--courses",
        default="courses.csv",
        help="Path to courses CSV file (default: courses.csv)"
    )
    parser.add_argument(
        "--requests",
        default="requests.csv",
        help="Path to student requests CSV file (default: requests.csv)"
    )
    parser.add_argument(
        "--out",
        default=".",
        help="Directory to write output reports (default: current directory)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        results = process_all_requests(
            courses_file=args.courses,
            requests_file=args.requests,
            output_dir=args.out
        )
        print("Summary of Results Preview:")
        print(f"{'ID':<6} | {'Course':<8} | {'Days':<5} | {'Reason':<10} | {'Recommendation':<22}")
        print("-" * 62)
        for r in results[:10]:
            c = r['course'] if r['course'] else "NONE"
            d = str(r['days']) if r['days'] is not None else "NONE"
            print(f"{r['id']:<6} | {c:<8} | {d:<5} | {r['reason']:<10} | {r['recommendation']:<22}")
        if len(results) > 10:
            print(f"... and {len(results) - 10} more records in output CSV files.")
        print("\nAll files successfully created: results.csv, review_queue.csv, summary.txt")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR]: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

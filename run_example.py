"""
Simplest way to run the framework.
    python run_example.py
Edit the parameters below as needed.
"""
import sys
from swing_research.framework import main

if __name__ == "__main__":
    # equivalent to: python -m swing_research.framework --start 2005-01-01 ...
    sys.argv = [
        "framework",
        "--start", "2005-01-01",
        "--capital", "1000000",
        "--topk", "10",
        # "--strategies", "A1,D1,H1",   # uncomment to run a subset
    ]
    main()

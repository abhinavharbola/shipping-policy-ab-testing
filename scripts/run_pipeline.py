"""
Runs the full experiment pipeline in order:
    calibrate -> power analysis -> simulate -> randomize -> analyze -> report

PREREGISTRATION.md is intentionally not touched by this script; it is a
locked document, written and committed before any of these steps
existed, and stays that way (see README.md "build-order proof").

Usage: python3 scripts/run_pipeline.py

Works with or without 'pip install -e .' first: it puts src/ on
sys.path itself, and runs correctly from any working directory.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pipeline import analyze, calibration, power_analysis, randomize, reporting, simulate

STEPS = [
    ("[1/6] Calibrating simulation parameters from real Olist data", calibration.main),
    ("[2/6] Computing required sample size (power analysis)", power_analysis.main),
    ("[3/6] Simulating the seller population", simulate.main),
    ("[4/6] Randomizing sellers into arms", randomize.main),
    ("[5/6] Running the preregistered analysis", analyze.main),
    ("[6/6] Generating the stakeholder memo", reporting.main),
]


def main():
    for label, step in STEPS:
        print(f"==> {label}")
        step()
        print()

    print("Pipeline complete. Now run: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()

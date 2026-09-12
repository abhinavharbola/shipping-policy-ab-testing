"""
Runs the full experiment pipeline in order:
    calibrate -> power analysis -> simulate -> randomize -> analyze -> report

docs/PREREGISTRATION.md is intentionally not touched by this script; it is a
locked document, written and committed before any of these steps
existed, and stays that way (see README.md "build-order proof").

Usage: python3 scripts/run_pipeline.py [--recalibrate]

No package install needed (there is no pyproject.toml): it puts src/
on sys.path itself, and runs correctly from any working directory.

Calibration is skipped by default when data/calibration/calibration_params.json
already exists, since that file is committed to the repo and the README
states the raw Olist CSVs are not required to run the pipeline. Pass
--recalibrate to force recalibration from data/raw/ (requires the Olist
CSVs to be present there).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from design import calibration, power_analysis
from experiment import analyze, randomize, reporting, simulate

CALIB_PARAMS_PATH = ROOT / "data" / "calibration" / "calibration_params.json"

STEPS = [
    ("Computing required sample size (power analysis)", power_analysis.main),
    ("Simulating the seller population", simulate.main),
    ("Randomizing sellers into arms", randomize.main),
    ("Running the preregistered analysis", analyze.main),
    ("Generating the stakeholder memo", reporting.main),
]


def main():
    force_recalibrate = "--recalibrate" in sys.argv
    steps = list(STEPS)

    if force_recalibrate or not CALIB_PARAMS_PATH.is_file():
        steps.insert(
            0,
            ("Calibrating simulation parameters from real Olist data", calibration.main),
        )
    else:
        print(
            f"==> Skipping calibration: {CALIB_PARAMS_PATH} already exists. "
            "Pass --recalibrate to rebuild it from data/raw/."
        )
        print()

    total = len(steps)
    for i, (label, step) in enumerate(steps, start=1):
        print(f"==> [{i}/{total}] {label}")
        step()
        print()

    print("Pipeline complete. Now run: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()




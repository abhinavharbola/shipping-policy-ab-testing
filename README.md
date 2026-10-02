# Experiment Design & Power Analysis for a Shipping Policy Change

A preregistered, simulated A/B testing pipeline that evaluates whether offering free shipping increases average order value without meaningfully increasing complaint rates. The metric, minimum lift, sample size, and statistical tests are fixed in a preregistration written before the simulation code, and every later correction is logged openly in that document.

Built as a portfolio project calibrated from the real public Olist Brazilian E-Commerce dataset. The experiment itself is entirely simulated: no hypothesis test in this project runs against real, unrandomized orders.

## Preview

<p align="center">
  <img src="assets/landing_view.png" width="720" alt="Streamlit dashboard showing the masthead, the verdict panel, and the four section tabs">
  <br>
  <sub>Main landing view: final verdict and all four tabs.</sub>
</p>

> Additional screenshots are in [`assets/`](assets/). The current stakeholder memo is generated to [`results/memo.md`](results/memo.md).

## What this is

Given a business question, "does free shipping raise AOV without hurting satisfaction?", the project:

1. Calibrates realistic simulation parameters from real Olist order data using descriptive statistics only.
2. Computes the required sample size and records the metric, minimum lift, and test choice in `docs/PREREGISTRATION.md`, with the numeric constants frozen in `src/design/preregistered.py`.
3. Simulates a population with a known injected effect using potential outcomes, matching the calibrated seller-level AOV spread that sized the study.
4. Randomizes sellers into treatment and control arms, revealing exactly one potential outcome per seller and discarding the counterfactual.
5. Runs the preregistered tests once, at the preregistered sample size.
6. Separately checks the analysis against the effect actually realized in the simulated population, and against the injected parameter.
7. Generates a stakeholder memo and a live dashboard from the pipeline's saved output files.

The project deliberately separates **design** from **experiment**. Everything under `design/` establishes the experimental design, including the frozen constants in `preregistered.py`. Everything under `experiment/` executes that design and reads those constants without modifying them.

## Architecture

```mermaid
flowchart TD
    raw[(data/raw\nOlist CSVs)] --> calib[calibration.py\ndescriptive stats only]
    calib --> power[power_analysis.py\nrequired N per arm,\nchecked against frozen N]
    power --> prereg[[docs/PREREGISTRATION.md\n+ preregistered.py]]
    prereg --> sim[simulate.py\npotential outcomes,\nknown injected effect]
    sim --> rand[randomize.py\nreveals one arm per seller]
    rand --> analyze[analyze.py\npreregistered tests only]
    analyze --> recovery[ground-truth\nrecovery check]
    analyze --> memo[reporting.py\nstakeholder memo]
    recovery --> dash([Streamlit dashboard])
    memo --> dash
```

Full section-by-section design rationale, including the post-hoc amendment log, is in [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md).

## Design decisions

| Decision             | Choice                                    | Why                                                         |
| -------------------- | ----------------------------------------- | ----------------------------------------------------------- |
| Primary metric       | Mean per-seller AOV                       | Matches the unit of randomization                           |
| Primary MDE          | BRL 25 absolute lift, also the minimum lift for a GO | Set near an approximate BRL 23 freight cost per order (external figure, see limitations) |
| Guardrail metric     | Complaint rate, review score of 2 or below | Prevents an AOV win from masking a satisfaction loss; a proxy, not delivery-specific |
| Guardrail margin     | 2.0pp non-inferiority                     | Approximately a 15.7% relative increase on the order-level baseline of 12.76% |
| Randomization unit   | Seller, not order                         | Avoids violating SUTVA within a seller's order stream       |
| Primary test         | Welch's t-test, two-sided                 | Allows for unequal variance between arms                    |
| Guardrail test       | One-sided, margin-shifted z-test on the order-weighted rate, seller-clustered standard errors | Matches the order-level baseline and margin, tests non-inferiority directly, respects clustering |
| Guardrail outcomes   | Passed, breached, inconclusive            | Separates a measured problem from a precision problem       |
| GO rule              | Significant, positive, at least BRL 25, and guardrail passed | The minimum lift drives the decision, not only the sample size |
| Required sample size | 2,503 sellers/arm, 5,006 total            | The primary metric is the binding constraint                |

## Guardrails

* **Fixed horizon.** `analyze()` has no sample-size argument. It takes the expected N from the constants in `src/design/preregistered.py` and raises `PartialDatasetError` unless it receives exactly that many sellers per arm. It also rejects a dataset where a seller appears in both arms.
* **Design drift check.** `power_analysis.py` raises `DesignDriftError` and writes nothing if the recomputed sample size differs from the frozen one, for example after `--recalibrate` changes the inputs.
* **One analysis per dataset.** `analyze.main()` refuses to overwrite an existing result that was computed on different data (`ReanalysisError`). Reruns on identical data are allowed and reproduce the same output.
* **Dataset-role enforcement.** `analyze.py` and `reporting.py` cannot read raw Olist data, and only `check_ground_truth_recovery()` may read the injected-effect file, after the main analysis has returned. AST-level tests verify both.
* **Zero-leakage randomization.** `randomize.py` reveals exactly one potential outcome per seller and raises if any counterfactual column would reach the analysis dataset.
* **Balanced assignment enforced.** `randomize()` raises a `ValueError` on an odd seller count instead of silently giving control one extra seller.

These are guards against accidental drift, not tamper-proofing. Anyone with write access can edit the frozen constants; the git history is the real lock.

## Data

* **`data/raw/`** contains the real Olist CSVs. They are user-supplied and gitignored. They are used only by `calibration.py` for descriptive statistics.
* **`data/calibration/`** contains the committed `calibration_params.json`, the only bridge between the real dataset and the simulation. It holds per-category AOV and complaint parameters, the baseline complaint rate, the seller-level AOV standard deviation, the orders-per-seller distribution, and two category-weight fields: `category_weights` (share of orders) and `category_weights_seller_level` (share of sellers). `simulate.py` requires the seller-level weights to draw a simulated seller's category, because the unit being drawn is a seller, not an order. It matches the seller-level AOV standard deviation in the simulated population. `calibration.py` also computes mean freight per order and counts the orders it drops; the committed file predates those two additions.
* **`data/simulated/`** contains the synthetic population and randomized assignment. These files are regenerable from the fixed seeds and are gitignored, except for the committed `true_effects.json`, which records both the injected parameters and the effects realized in the simulated population.
* **`results/`** contains the power analysis, analysis results, recovery check, and stakeholder memo.

The Olist dataset is reused from other portfolio projects, but its role here is strictly limited to simulation calibration. No hypothesis test is performed against it.

## Project structure

```text
.
├── README.md
├── requirements.txt
├── .gitignore
│
├── docs/
│   └── PREREGISTRATION.md       # experimental design and amendment log
│
├── .streamlit/
│   └── config.toml              # dashboard theme
│
├── assets/
├── data/
│   ├── raw/                     # Olist CSVs, user supplied, gitignored
│   ├── calibration/             # committed calibration_params.json
│   └── simulated/               # regenerable simulation data, true_effects.json committed
│
├── src/
│   ├── design/
│   │   ├── calibration.py       # descriptive calibration
│   │   ├── preregistered.py     # frozen design constants
│   │   └── power_analysis.py    # sample-size calculation and drift check
│   │
│   └── experiment/
│       ├── simulate.py          # potential outcomes
│       ├── randomize.py         # treatment assignment
│       ├── analyze.py           # preregistered analysis
│       └── reporting.py         # verdict, memo content, memo
│
├── dashboard/
│   └── app.py                   # Streamlit results dashboard
│
├── results/
│   ├── power_analysis.json
│   ├── analysis_results.json
│   ├── recovery_check.json
│   └── memo.md
│
├── scripts/
│   └── run_pipeline.py
│
└── tests/
```

The separation between `design/` and `experiment/` is intentional. `design/` establishes what the experiment is allowed to do; `experiment/` executes that design afterward.

## Getting started

### 1. Data

The committed `data/calibration/calibration_params.json` is sufficient to run the experiment pipeline, so the raw Olist CSVs are not required unless you want to regenerate the calibration.

To recalibrate from the original dataset, download the Olist Brazilian E-Commerce dataset and place these files in `data/raw/`:

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
product_category_name_translation.csv
```

Recalibration can change the required sample size. If it does, `power_analysis.py` stops the pipeline with a `DesignDriftError` until the preregistration and `preregistered.py` are amended deliberately.

### 2. Install

Developed on Python 3.11.9. Dependencies carry lower and upper version bounds in `requirements.txt`. The dashboard needs a Streamlit release that supports `width="stretch"` on buttons and charts.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No package installation step is required for the project itself. `scripts/run_pipeline.py`, `dashboard/app.py`, and the test suite add `src/` to `sys.path`.

To run a single module directly, from the repository root (`src` is a relative path):

```bash
PYTHONPATH=src python -m design.calibration
```

### 3. Run

```bash
python scripts/run_pipeline.py
streamlit run dashboard/app.py
pytest tests/ -v
```

By default, the pipeline reuses the committed calibration parameters. To rebuild them from `data/raw/`:

```bash
python scripts/run_pipeline.py --recalibrate
```

The pipeline executes:

```text
power → simulate → randomize → analyze → report
```

The committed results come from fixed seeds. If a different NumPy version produces a different random stream, `analyze.main()` raises `ReanalysisError` on the first run against the committed `results/analysis_results.json`; delete that file and rerun.

The pipeline never regenerates or modifies `docs/PREREGISTRATION.md`. If the recomputed sample size ever differs from the frozen one, the pipeline stops at the first step. The committed `results/` let the dashboard run immediately; rerun the pipeline to regenerate them. If `results/` is missing, the dashboard shows a prompt instead of results.

## Evaluation

The test suite is the project's core evidence: 71 tests. `test_repo_hygiene.py` checks for unused imports and locals with an AST pass, and also enforces the repository's no-comments and no-em-dash conventions.

| Test file                             | What it protects                                                                                     |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `test_power_analysis.py`              | Power maths matches a textbook case, the committed calibration reproduces the frozen N of 2,503, the preregistration text states the frozen constants, and a changed calibration raises `DesignDriftError` |
| `test_simulation_calibration.py`      | The simulated seller-level AOV standard deviation matches the calibration that sized the study, means stay near the category mix, and realized effects are recorded correctly |
| `test_randomization_balance.py`       | Exact 1:1 splits, seed dependence, per-seller assignment frequency near one half, no counterfactual leakage, odd populations rejected |
| `test_stopping_rule.py`               | `analyze()` rejects partial, imbalanced and double-armed datasets, has no override argument, and refuses to overwrite results computed on different data |
| `test_recovery_check_catches_bugs.py` | Correct randomization recovers the truth for most seeds; a broken `randomize()` run through the real code path is caught; recovery is judged against the realized effect |
| `test_no_raw_data_leak.py`            | AST checks: raw Olist data and the injected effect cannot reach `analyze.py` or `reporting.py`, and the recovery check runs after the analysis |
| `test_guardrail_clustering_fix.py`    | The guardrail rate is order-weighted, clustering inflates the standard error, and the three outcomes are assigned correctly |
| `test_decision_rule.py`               | A GO needs every condition, including the minimum lift; breached and inconclusive are worded differently |
| `test_memo_rendering.py`              | Currency survives Streamlit markdown rendering, guardrail wording matches the outcome, and no delivery cause is asserted |
| `test_estimator_calibration.py`       | Over 100 alternative randomizations of the simulated population, both estimators are unbiased for the realized effects, the intervals cover them at least nominally, and a truth inside the margin mostly yields a passed guardrail |
| `test_calibration_category_weights.py`| Seller-level and order-level category weights differ, and freight per order is reported |
| `test_calibration_order_table.py`     | Freight is summed per order, dropped and multi-seller orders are counted, non-delivered orders are excluded |
| `test_repo_hygiene.py`                | No comments, no em dashes, no unused imports or locals, no unclosed `json.load(open(...))`, no deprecated Streamlit argument |

## Results

The committed simulation (simulation seed 20260904, randomization seed 71) injects a BRL 28.00 AOV lift and a 1.2 percentage point complaint-rate increase. Because the injected values are parameters of a random draw, the population also has realized effects: a seller-level AOV lift of BRL 30.84 and an order-level complaint difference of 1.35pp. A confidence interval from one randomized run targets the realized values, so recovery is judged against them. The simulated seller-level AOV standard deviation matches the calibrated 315.58 that sized the study.

| Metric                    | Point estimate | 95% CI                 | Realized  | Injected  | Recovered? |
| ------------------------- | -------------: | ---------------------- | --------: | --------: | ---------- |
| AOV lift                  |      BRL 38.07 | [BRL 21.32, BRL 54.82] | BRL 30.84 | BRL 28.00 | Yes        |
| Complaint rate difference |        +1.73pp | [+1.18pp, +2.27pp]     |   +1.35pp |   +1.20pp | Yes        |

The pipeline's verdict is **NO-GO**, and the reason is precision on the guardrail, not a measured breach. Free shipping raised mean seller AOV from BRL 134.02 to BRL 172.09 (p = 8.6e-06), and the estimated lift clears the BRL 25 minimum. Complaints rose from 12.18% to 13.90% of orders, a gap of 1.73pp. That is below the 2.0pp margin, but the margin-shifted test (z = -0.98, one-sided p = 0.163) did not establish non-inferiority, so the guardrail status is **inconclusive**. The rule requires positive evidence that the gap is below the margin, and the interval [+1.18pp, +2.27pp] straddles it.

Against ground truth the realized complaint gap (1.35pp) is inside the margin, so this NO-GO reflects a guardrail that could not be resolved at this sample size, not evidence of harm. The standard error is about 0.28pp. By back-of-envelope arithmetic that is roughly 89% power to establish non-inferiority at a true 1.2pp gap, and roughly 75% at the realized 1.35pp gap. Those are post hoc figures from one run, not a preregistered calculation.

Earlier versions of this repository reported a BRL 28.21 lift and a +2.02pp breach. Those came from a simulation whose seller-level AOV spread was half the calibrated value and from an unweighted seller-mean guardrail estimator. The changes and their reasons are logged in `docs/PREREGISTRATION.md` section 10. The committed randomization is one draw. Over 100 alternative randomizations of the same population (the draws in `test_estimator_calibration.py`), the mean estimates were BRL 30.36 and +1.33pp against realized values of BRL 30.84 and +1.35pp, and the 95% intervals covered the realized effects in 99% (AOV) and 95% (complaints) of draws. The guardrail passed in 84% of draws, was inconclusive in 16% and was never breached, and the full rule returned GO in 66%. The committed NO-GO is therefore a less favorable draw, not the typical outcome for this population. It is still one seeded run, not evidence that the method generalizes to every real-world effect.

## Known limitations

* **Recovery is a smoke test.** One seeded 95% interval misses the truth about once in twenty runs even when the method is correct, so passing or failing it proves little alone.
* **The guardrail power is not preregistered.** The sizing uses a pooled, order-level, two-sided calculation (142 sellers-equivalent per arm), so the primary metric binds at 2,503. That ignores within-seller correlation and answers a different question from the non-inferiority test that runs. A matched seller-clustered calculation needs per-seller complaint variance, which calibration does not compute. The dashboard's 80% power figure applies to the order value test only.
* **The guardrail metric is a proxy.** A review score of 2 or below is not specific to delivery, and the simulation generates complaints independently of delivery, so the trial cannot attribute a change to delivery.
* **The BRL 23 freight figure is unverified here.** `calibration.py` now computes mean freight per order, but the committed calibration file predates that field and the raw Olist files are not in the repository. Treat the figure as an external approximation until you recalibrate.
* **Multi-seller orders are credited to one seller.** Calibration attributes a whole order to the seller of its lowest `order_item_id`, which can inflate that seller's AOV. The share of such orders is recorded in the calibration file's data quality notes. Orders with a missing category or seller are dropped, and recalibration now reports how many.
* **The simulation matches calibration on a few moments only.** Seller-level AOV standard deviation and category mix are matched. Order volume is drawn independently of category and of complaint propensity, and the seller-level AOV mean is not stored in calibration, so the simulated mean is checked against the category mix instead.
* **No cross-seller interference is assumed.** Competition for the same customers could leak effects between arms.
* **Calibration is marketplace-specific.** Baselines reflect Olist's category mix and the Brazilian market.

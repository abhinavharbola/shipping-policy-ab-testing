# Experiment Design & Power Analysis for a Shipping Policy Change

This is a **simulated experiment, not a live test on real users.** Real
Olist e-commerce data is used only to calibrate realistic simulation
parameters — category-level order-value distributions and baseline
delivery-complaint rates. No hypothesis test anywhere in this project
runs against real, unrandomized Olist orders; every p-value and
confidence interval here comes from a synthetic, randomly assigned
population with a known, injected effect. This is a companion to a
separate observational-data project (propensity matching, Rosenbaum
bounds) and deliberately does not overlap with it: this project is
about running an A/B test correctly, not about salvaging causal claims
from data that was never randomized.

The Olist dataset also appears in other, unrelated projects in this
portfolio. That reuse is deliberate — it's a convenient, realistic,
public e-commerce dataset — not an oversight, and here its role is
strictly limited to calibration.

## The point of this project

Most "A/B test" write-ups skip straight to the analysis. The actual
discipline of experimentation is in what happens *before* you see any
data: picking a metric, committing to a minimum effect worth acting on,
sizing the sample, and writing down which test you'll run — all before
a single row of experimental data exists. This project enforces that
order literally, through git history, not just prose:

```
7ba1f90 Preregister design: metric, MDE, power analysis, before any
        simulation code exists
70722c0 Simulate population, randomize, and run preregistered analysis
```

`PREREGISTRATION.md` and the power analysis were committed in isolation,
*before* the simulation, randomization, or analysis code existed (at that
point in history they were flat scripts named `generate_population.py`,
`randomize.py`, `analyze.py`; later commits reorganized them, first into
`src/shipping_experiment/`, then into `src/pipeline/simulate.py`,
`randomize.py`, `analyze.py`, both times via `git mv`, so
`git log --follow <path>` still shows the full history through both
renames). Nothing in the design could have been fit to a result, because
no result existed yet. Run `git log --oneline` for the full history: the
commits after `70722c0` are documentation, a bug fix to the simulation's
orders-per-seller calibration, and two repo restructurings into a standard
`src` package layout — all made after the design was already locked, and
none of them touch `PREREGISTRATION.md` or change any number it quotes,
which `git show 7ba1f90:PREREGISTRATION.md` confirms.

## Project layout

```
.
├── PREREGISTRATION.md          # locked design doc, see build-order proof above
├── pyproject.toml              # package metadata, dependencies, console scripts
├── requirements.txt            # plain pip install if you don't want the package
├── data/
│   └── raw/                    # you supply the Olist CSVs here, gitignored
├── src/
│   ├── data/
│   │   ├── calibration/        # calibration_params.json, committed
│   │   └── simulated/          # regenerable from the seed, gitignored
│   └── pipeline/                # the pipeline code, as an installable package
│       ├── calibration.py       # step 0.5
│       ├── power_analysis.py    # step 1-2
│       ├── simulate.py          # step 4
│       ├── randomize.py         # step 5
│       ├── analyze.py           # step 6
│       └── reporting.py         # step 7
├── dashboard/app.py            # step 8, Streamlit
├── results/                    # power analysis, analysis results, memo, committed
├── scripts/run_pipeline.py     # runs steps 1-7 in order
└── tests/                      # step 9
```

Raw input data lives at the project root (`data/raw/`) since it's an
external input, not an artifact of the code. Everything the pipeline
itself generates or consumes as a side effect of running (`calibration/`,
`simulated/`) lives under `src/data/`, next to the code that produces and
reads it.

## Pipeline

```
calibration.py     -> src/data/calibration/calibration_params.json
        (real data, descriptive stats only, no hypothesis test)
power_analysis.py  -> results/power_analysis.json
        (reads calibration only; computes required N per arm)
PREREGISTRATION.md  [committed to git here, alone]
simulate.py         -> src/data/simulated/population_potential_outcomes.csv
        (synthetic sellers; each order gets a control AND a
        treatment potential outcome, with a known effect on the
        treatment side)
randomize.py        -> src/data/simulated/assigned_experiment.csv
        (assigns each seller to one arm, reveals only that arm's
        outcome, physically drops the counterfactual columns)
analyze.py          -> results/analysis_results.json,
                        results/recovery_check.json
        (runs exactly the preregistered tests; separately checks
        the result against the known injected effect)
reporting.py        -> results/memo.md
dashboard/app.py    (streamlit)
```

## Setup

```bash
pip install -e ".[dashboard,dev]"
```

This installs the `pipeline` package plus six console commands
(`shipping-calibrate`, `shipping-power`, `shipping-simulate`,
`shipping-randomize`, `shipping-analyze`, `shipping-report`), the
dashboard's dependencies, and pytest. If you'd rather not install it as a
package, `pip install -r requirements.txt` and call each module directly
instead (`python3 -m pipeline.calibration`, etc.) — both approaches run
the exact same code.

## Run in order

```bash
shipping-calibrate
shipping-power
# PREREGISTRATION.md is already written and committed in this repo's history
shipping-simulate
shipping-randomize
shipping-analyze
shipping-report
streamlit run dashboard/app.py
```

Or, to run the first six steps in one go instead of typing them out:

```bash
python3 scripts/run_pipeline.py
```

It doesn't require `pip install -e .` first (it puts `src/` on
`sys.path` itself), runs the six steps in order, and finishes by
telling you to run the dashboard.

## Design summary

- **Business question:** does free shipping raise average order value
  (AOV) without meaningfully increasing the delivery-complaint rate.
- **Unit of randomization:** seller, not order — see PREREGISTRATION.md
  section 2 for the SUTVA/interference argument.
- **Primary metric / MDE:** mean per-seller AOV; MDE = R$25, grounded in
  the ~R$23 average freight cost a seller absorbs (see PREREGISTRATION.md
  section 3 for the full argument).
- **Guardrail metric / margin:** delivery-complaint rate (review score
  ≤ 2); non-inferiority margin of +2.0 percentage points on a 13.11%
  baseline.
- **Required sample size:** 2,499 sellers per arm (4,998 total), set by
  the primary metric (the binding constraint over the guardrail).
- **Tests:** Welch's t-test on seller-level mean AOV (primary);
  one-sided two-proportion z-test on pooled order-level complaint counts
  (guardrail), documented in PREREGISTRATION.md as a deliberate
  simplification of the ideal seller-clustered version.

## Ground-truth recovery, with the actual numbers

The simulated population has a true injected AOV lift of R$28.00 and a
true injected complaint-rate increase of 1.2 percentage points. The
preregistered analysis, run once on the full sample, recovered:

| | Point estimate | 95% CI | True value | Recovered? |
|---|---|---|---|---|
| AOV lift | R$31.59 | [R$24.10, R$39.09] | R$28.00 | Yes |
| Complaint rate diff | +1.06pp | [+0.73pp, +1.40pp] | +1.20pp | Yes |

Both intervals contain their true injected value, and the guardrail
correctly did not breach the 2.0-point margin. This is one seeded run,
not proof the method generalizes to every possible effect — see
limitations below.

## Why fixed-horizon, no-peeking matters

If you check a running experiment repeatedly and stop the first time
p < 0.05, your true false-positive rate is much higher than 5%, because
you gave chance many independent opportunities to produce a fluky
"significant" result and only needed one. This project commits to a
single look, at a pre-specified sample size, computed before any data
existed (see PREREGISTRATION.md section 6). `src/pipeline/analyze.py`'s
`analyze()` function enforces this in code: it raises `PartialDatasetError` if the
dataset it's given doesn't contain exactly the preregistered number of
sellers per arm (`tests/test_stopping_rule.py`).

## Known limitations

- **Recovery is necessary, not sufficient.** A single seeded run whose
  CI happens to contain the true effect is expected roughly 95% of the
  time by construction, even for a correctly-built method — this run
  passing is a smoke test that the pipeline isn't obviously broken, not
  a proof the method generalizes to every real, unknown effect size.
- **Seller-level randomization assumes no cross-seller interference.**
  If sellers compete for the same limited customer pool, or if Olist's
  own marketing shifts customers toward whichever sellers currently
  offer free shipping, that would leak treatment effect across arms and
  bias the estimate. Real deployment would need to check for this.
- **Guardrail test clustering simplification.** The guardrail test pools
  order-level complaint counts by arm rather than using a seller-clustered
  or cluster-robust estimator, understating the true standard error. This
  is anti-conservative (slightly more likely to flag a guardrail breach
  than a fully rigorous version would), documented in PREREGISTRATION.md
  section 8, and left as a known simplification rather than fixed, since
  it does not change this run's conclusion.
- **Calibration reflects Olist's category mix and Brazil's market.**
  Baseline AOV distributions and complaint rates may not generalize to a
  different marketplace, region, or time period.

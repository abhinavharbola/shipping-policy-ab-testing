# Preregistration: Free Shipping and Average Order Value

Written before any simulated data exists. The only inputs used below are
descriptive statistics computed from real, historical Olist orders
(`data/calibration/calibration_params.json`, produced by
`calibration.py`). No hypothesis test has been run on that data
and none ever will be; it is used solely to calibrate realistic
simulation parameters. This document is committed to git before
`simulate.py`, `randomize.py`, or `analyze.py` are written.

## 1. Hypothesis

Offering free shipping increases a seller's average order value (AOV)
without meaningfully increasing the seller's delivery-complaint rate.

Directional hypothesis, stated before seeing any experimental data:
mean AOV under free shipping > mean AOV under standard shipping.

## 2. Metrics

**Primary metric:** average order value (AOV) per seller-order. For a
given seller, this is the mean of that seller's own order values
(sum of item prices per order). Currency: BRL.

**Guardrail metric:** delivery-complaint rate, defined as the share of a
seller's orders with a customer review score of 2 or below. This exists
so that an AOV lift is not declared a win while satisfaction quietly
erodes underneath it.

**Unit of randomization: seller, not order.** Sellers choose a shipping
policy; individual orders do not. Randomizing at the order level within
a seller would violate SUTVA/no-interference: a seller offering free
shipping on some orders and not others would likely change customer
behavior and seller operations in ways that leak across their own order
stream (e.g. batching shipments, adjusting prices site-wide), so orders
from the same seller are not independent units. Randomizing whole
sellers avoids that contamination.

## 3. Minimum detectable effect and business justification

**Primary MDE: BRL 25.00 absolute lift in mean per-seller AOV.**
In the calibration data, the average freight value absorbed per order is
approximately BRL 23. A shipping-policy change that does not lift AOV by
at least that much cannot be covering its own direct cost, before even
accounting for margin. The MDE is set a little above that break-even
point so the trial is not powered to detect a lift that would be a wash
on paper. A stricter, margin-adjusted threshold would raise this bar
further; BRL 25 is treated as a floor, not an ideal target.

**Guardrail non-inferiority margin: 2.0 percentage points absolute**,
against a calibrated baseline complaint rate of 12.76%. That is roughly
a 16% relative increase, picked as the threshold past which the
seller-satisfaction cost plausibly outweighs the AOV gain, independent
of what the AOV result shows.

## 4. Power analysis and required sample size

Computed by `power_analysis.py` from calibration parameters only. Full
output: `results/power_analysis.json`.

| | Primary (AOV) | Guardrail (complaint rate) |
|---|---|---|
| Test used to size the study | Welch's t-test → `TTestIndPower` | Two-proportion z-test → `NormalIndPower` (conservative stand-in; planned analysis test is one-sided, see §6) |
| Baseline variability | seller-level AOV std = 315.58 | baseline rate = 12.76% |
| Effect size | Cohen's d = 0.0792 | h = 0.0581 |
| alpha | 0.05 | 0.05 |
| power | 0.80 | 0.80 |
| Required N per arm | 2,503 sellers | 4,652 orders → 142 sellers-equivalent (at 32.83 orders/seller) |

**Binding constraint: the primary AOV test.** It requires more sellers
per arm than the guardrail does, so the experiment is powered to
**2,503 sellers per arm (5,006 total)**. This is compared, not capped,
against the 2,831 sellers present in the Olist calibration data: the
simulated population is sized to what the design requires, not to a
historical dataset's incidental scale. Nearly the entire real Olist
seller base is smaller than what full power would need, which is a
real-world feasibility note worth surfacing to stakeholders were this
run live, but it does not change the statistical requirement.

## 5. Randomization

Simple random assignment by seller, 1:1 to free-shipping vs. standard
shipping, **not stratified**. Stratifying by category was considered,
since category is a real source of baseline AOV variance (see
calibration data), but with 2,499 sellers per arm, simple randomization
already balances category mix well in expectation, and stratification
adds analysis complexity (needing a blocked estimator) for a balance
problem that a sample of this size does not have. `randomize.py` seeds
its RNG for reproducibility; the seed is an implementation detail, not
a design decision, and is not tuned to produce a favorable split.

## 6. Stopping rule

**Fixed horizon. No peeking.** The full pre-specified sample
(2,499 sellers per arm) is generated and assigned once; the analysis
runs exactly once, on the complete dataset. `analyze.py` enforces this
by refusing to run on a partial dataset (see `tests/`). Repeated peeking
at results as data accrues, without a sequential-testing correction,
inflates the false-positive rate above the nominal 5% with every look;
the more often an experimenter checks and stops at the first "significant"
result, the more that result is an artifact of the stopping behavior
rather than a real effect. Fixed-horizon testing avoids this by making
exactly one inferential claim, at a pre-committed sample size.

## 7. Planned primary analysis: Welch's t-test on AOV

Welch's t-test (unequal-variance t-test), not Student's t-test, chosen
**before seeing data** because a shipping-cost change plausibly creates
unequal variance between arms: free shipping may change who converts
and how much they buy in ways that widen or narrow the spread of order
values differently in each arm. Welch's test does not assume equal
variances, so it stays valid under that scenario at a negligible power
cost if variances happen to be equal after all.

Unit of analysis: one observation per seller (that seller's mean AOV
across their orders in the study window), matching the unit of
randomization.

## 8. Planned guardrail analysis: one-sided proportions test

The business question is "does the complaint rate get meaningfully
worse", which is a non-inferiority question, not a two-sided one. The
planned test is a **one-sided two-proportion z-test** (treatment rate
vs. control rate, alternative: treatment is higher by more than the
0 percentage points needed to raise a two-sided flag — practically,
the test asks whether treatment's complaint rate exceeds control's,
one-sided), with the pre-specified 2.0-point margin used to interpret
the result. Expected event counts (thousands of orders per arm) are
large enough for the normal approximation to be appropriate; Fisher's
exact test is not needed at this scale.

**Documented simplification:** because randomization is at the seller
level, the statistically ideal version of this test would operate on
seller-level aggregates or use a cluster-robust variance estimator. For
this project, the guardrail test instead pools order-level complaint
counts within each arm. This treats orders as independent within a
seller, which understates the true standard error and is
**anti-conservative**: it makes the guardrail test somewhat more likely
to flag a breach than a fully clustered analysis would, i.e. it errs
toward caution on user harm at the cost of a slightly inflated
false-positive rate on the guardrail specifically. This is flagged here
rather than hidden, and is out of scope to fix for this project (see
README limitations).

## 9. Commit discipline

This file is committed to git as its own commit before
`simulate.py`, `randomize.py`, or `analyze.py` are written.
The git log is the literal proof the design was fixed before the
simulated data existed to fit it to.




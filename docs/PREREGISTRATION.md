# Preregistration: Free Shipping and Average Order Value

Originally written before any simulated data existed. Post-hoc amendments
are recorded in section 10 and marked in the sections they touch; the
original reasoning is kept, not erased. The only inputs used below are
descriptive statistics computed from real, historical Olist orders
(`data/calibration/calibration_params.json`, produced by
`calibration.py`). No hypothesis test has been run on that data
and none ever will be; it is used solely to calibrate realistic
simulation parameters. This document is committed to git before
`simulate.py`, `randomize.py`, or `analyze.py` are written.

## 1. Hypothesis

Offering free shipping increases a seller's average order value (AOV)
without meaningfully increasing the complaint rate.

Directional hypothesis, stated before seeing any experimental data:
mean AOV under free shipping > mean AOV under standard shipping.

Clarification (see section 10): the primary test is two-sided, which is
what the sample size in section 4 was computed for and is the more
conservative choice. The direction enters the decision rule instead: a GO
requires the estimated lift to be positive and to reach the minimum lift
in section 3.

## 2. Metrics

**Primary metric:** average order value (AOV) per seller. For a given
seller, this is the mean of that seller's own order values (sum of item
prices per order). Currency: BRL.

**Guardrail metric:** complaint rate, defined as the share of orders with
a customer review score of 2 or below, estimated per arm as total
complaints divided by total reviewed orders (order-weighted), with the
seller as the cluster for the variance. This exists so that an AOV lift
is not declared a win while satisfaction quietly erodes underneath it. A
review score of 2 or below is a proxy for a bad experience; it is not
specific to delivery and the trial cannot attribute a change to delivery.

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
The average freight value absorbed per order is approximately BRL 23
(an external approximation from public Olist data; it is not stored in
the committed calibration file, and `calibration.py` now computes it as
`overall.freight_mean_per_order` the next time it is run). A
shipping-policy change that does not lift AOV by at least that much
cannot be covering its own direct cost, before even accounting for
margin. The MDE is set a little above that break-even point so the trial
is not powered to detect a lift that would be a wash on paper. A
stricter, margin-adjusted threshold would raise this bar further; BRL 25
is treated as a floor, not an ideal target. It is also the smallest lift
worth acting on, so the decision rule requires the estimated lift to
reach it.

**Guardrail non-inferiority margin: 2.0 percentage points absolute**,
against a calibrated order-level baseline complaint rate of 12.76%. That
is roughly a 15.7% relative increase, picked as the threshold past which
the seller-satisfaction cost plausibly outweighs the AOV gain,
independent of what the AOV result shows. The baseline is an order-level
rate, which is why the guardrail is estimated order-weighted (section 8).

## 4. Power analysis and required sample size

Computed by `power_analysis.py` from calibration parameters only. Full
output: `results/power_analysis.json`. The resulting sample size is frozen
as a constant in `src/design/preregistered.py` and must equal the value
below.

| | Primary (AOV) | Guardrail (complaint rate) |
|---|---|---|
| Test used to size the study | Student's t power (`TTestIndPower`, equal n and variance planning assumption); the test that runs is Welch's | Two-proportion z-test (`NormalIndPower`), an order-level planning approximation; the planned analysis test is one-sided and seller-clustered, see §8 |
| Baseline variability | seller-level AOV std = 315.58 | baseline rate = 12.76% |
| Effect size | Cohen's d = 0.0792 | h = 0.0581 |
| alpha | 0.05 | 0.05 |
| power | 0.80 | 0.80 |
| Required N per arm | 2,503 sellers | 4,652 orders → 142 sellers-equivalent (at 32.83 orders/seller) |

**Binding constraint: the primary AOV test.** It requires more sellers
per arm than the guardrail does, so the experiment is powered to
**2,503 sellers per arm (5,006 total)** for the order value test. This is
compared, not capped, against the 2,831 sellers present in the Olist
calibration data: the simulated population is sized to what the design
requires, not to a historical dataset's incidental scale. Nearly the
entire real Olist seller base is smaller than what full power would need,
which is a real-world feasibility note worth surfacing to stakeholders
were this run live, but it does not change the statistical requirement.
The 80% power figure applies to the primary test only; the guardrail's
power is not preregistered (see the amendment below).

**Amendment (post-analysis, wording only).** After the first complete
run, the guardrail sizing described above was found to be mischaracterized
in two ways. First, it is not conservative. It sizes for detecting a
margin-sized difference against zero using pooled order-level counts,
which ignores within-seller correlation and answers a different question
from the one-sided, seller-clustered non-inferiority test that section 8
specifies. In the original committed run, which used a seller-mean
estimator, that test had a standard error of about 0.54 percentage
points, which implied roughly 43% power to establish non-inferiority when
the true gap is 1.2 percentage points (a back-of-envelope figure from one
run, not a preregistered calculation). Second, the table's reference to
"see §6" for the planned guardrail test should read §8. This amendment
changes no sample size, metric, margin, test, or decision rule: 2,503
sellers per arm remains the preregistered N. It was written after results
were observed and is recorded so the correction is auditable, not to
alter the design. A seller-level guardrail power calculation, which needs
per-seller complaint-rate variance from calibration, is left as future
work. The estimator change in section 10 lowered the observed standard
error to about 0.28 percentage points, which by the same back-of-envelope
arithmetic is roughly 89% power at a 1.2 point gap; that figure is also
post hoc and unregistered.

## 5. Randomization

Simple random assignment by seller, 1:1 to free-shipping vs. standard
shipping, **not stratified**. Stratifying by category was considered,
since category is a real source of baseline AOV variance (see
calibration data), but with 2,503 sellers per arm, simple randomization
already balances category mix well in expectation, and stratification
adds analysis complexity (needing a blocked estimator) for a balance
problem that a sample of this size does not have. `randomize.py` seeds
its RNG for reproducibility; the seed is an implementation detail, not
a design decision, and is not tuned to produce a favorable split.

## 6. Stopping rule

**Fixed horizon. No peeking.** The full pre-specified sample
(2,503 sellers per arm) is generated and assigned once; the analysis
runs exactly once, on the complete dataset. Repeated peeking at results
as data accrues, without a sequential-testing correction, inflates the
false-positive rate above the nominal 5% with every look; the more often
an experimenter checks and stops at the first "significant" result, the
more that result is an artifact of the stopping behavior rather than a
real effect. Fixed-horizon testing avoids this by making exactly one
inferential claim, at a pre-committed sample size.

Enforcement in code, with its limits. The constants of this design
(alpha = 0.05, power target 0.80, the BRL 25.00 minimum lift, the 2.0
percentage point margin, and 2,503 sellers per arm) are frozen in
`src/design/preregistered.py`. `analyze.py` takes its expected sample size
from that file, has no override argument, and refuses to run on a partial
or over-accrued dataset. `power_analysis.py` refuses to write results if
the recomputed sample size differs from the frozen one. `analyze.py`
also refuses to overwrite an existing result that was computed on
different data. These are guards against accidental drift, not tamper
proofing: anyone with write access can edit the constants. The git
history of this file and of `preregistered.py` is the actual lock.

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
randomization. The test is two-sided at alpha = 0.05.

Decision rule for the primary metric: a GO requires a statistically
significant lift, a positive point estimate, and a point estimate at or
above the BRL 25.00 minimum lift of section 3, together with a passed
guardrail (section 8).

## 8. Planned guardrail analysis: order-weighted, seller-clustered non-inferiority test

The business question is "does the complaint rate get meaningfully
worse", which is a non-inferiority question, not a two-sided one. The
planned test is a **one-sided, margin-shifted z-test on the order-weighted
complaint-rate difference, with standard errors clustered by seller**.
Each arm's rate is its total complaints divided by its total reviewed
orders, matching the order-level baseline the margin was set against. The
variance is the seller-clustered ratio-estimator variance, so orders from
the same seller are not treated as independent, matching the unit of
randomization. The null hypothesis is shifted to the preregistered margin
itself, H0: (p_treatment − p_control) ≥ margin, H1: (p_treatment −
p_control) < margin, and non-inferiority is concluded only when H0 is
rejected at alpha, i.e. only when the data give positive evidence the true
gap sits below the margin.

The guardrail has three outcomes, not two. **Passed:** non-inferiority is
established. **Breached:** it is not established and the point estimate is
at or above the margin. **Inconclusive:** it is not established but the
point estimate is below the margin, which means the data are too noisy to
rule out a gap at or above the margin. Passed is required for a GO;
breached and inconclusive are both NO-GO, and they are reported
differently because one is a measured problem and the other is a
precision problem.

**Amendment (methodology only, made after a first analysis of the same
seeded dataset).** The original version of this section specified a
pooled, order-level two-proportion z-test against a zero-difference null,
with the margin applied only as a separate check on the point estimate
afterward. That version was superseded by a seller-clustered,
margin-shifted test, for two reasons: pooling order-level counts treats
orders from the same seller as independent, which they are not,
understating the true standard error (anti-conservative); and testing
against a zero-difference null rather than the margin itself does not
actually test the non-inferiority question the guardrail exists to
answer, at this project's sample size a from-zero test is significant for
almost any nonzero difference, so it does little real discriminating work
beyond the separate point-estimate check. An earlier version of this
amendment called it pre-analysis. That was inaccurate: the simulation is
seeded, so the dataset the amended test analyzed was identical to the one
the original test had already analyzed, and the amendment cannot be
called independent of having seen that result. The original
simplification and its consequences are kept below for the record, since
a real trial's amendment history should be auditable, not erased.

**Original documented simplification (superseded above):** because
randomization is at the seller level, the statistically ideal version
of this test would operate on seller-level aggregates or use a
cluster-robust variance estimator. The original version of this project
instead pooled order-level complaint counts within each arm, treating
orders as independent within a seller, which understated the true
standard error and was anti-conservative: it made the guardrail test
somewhat more likely to flag a breach than a fully clustered analysis
would, i.e. it erred toward caution on user harm at the cost of a
slightly inflated false-positive rate on the guardrail specifically.
That tradeoff is no longer necessary now that the guardrail test is
seller-clustered directly.

**Second amendment (post hoc, see section 10).** The seller-clustered
version above first used an unweighted mean of each seller's own complaint
rate. That estimand did not match the order-level baseline and margin,
and it was dominated by sellers with very few orders. It was replaced by
the order-weighted, seller-clustered estimator described at the start of
this section.

## 9. Commit discipline

The original version of this file was committed to git as its own commit
before `simulate.py`, `randomize.py`, or `analyze.py` were written. The git
log is the literal proof the design was fixed before the simulated data
existed to fit it to. Every later change to this file is an amendment and
is logged in section 10; none of them is covered by that proof.

## 10. Amendment log (post hoc, 2026-09-30)

All items below were made after the first complete run and its results
had been seen. None changes the preregistered sample size of 2,503
sellers per arm, the BRL 25.00 minimum lift, the 2.0 percentage point
margin, alpha, or the power target. After these changes the pipeline was
rerun and its outputs changed; the README states the current results.

1. **Simulation variance.** The simulated population had a seller-level
   AOV standard deviation of about 157, against the 315.58 from
   calibration that sized the study, and about 12.6% of simulated sellers
   had their mean clipped at 5. The observed standard error was therefore
   roughly half the planned one and the run was close to 100% powered,
   not 80%. The simulation now calibrates a seller-dispersion parameter so
   the simulated seller-level standard deviation matches calibration, and
   a test checks it.
2. **Ground truth for the recovery check.** The recovery check compared
   intervals only with the injected parameters. It now also records the
   effect actually realized in the simulated population and judges
   recovery against that, because a confidence interval from one
   randomized run targets the realized effect. In the original run the
   realized seller-level complaint difference (2.12 percentage points)
   exceeded the margin even though the injected parameter (1.2) did not,
   so the earlier statement that the NO-GO was a false alarm held only
   against the parameter.
3. **Guardrail estimator.** Replaced the unweighted mean of seller
   complaint rates with the order-weighted, seller-clustered estimator of
   section 8, to match the order-level baseline and margin and to stop
   sellers with one to three orders dominating the estimate.
4. **Decision rule.** A GO now also requires the estimated lift to reach
   the BRL 25.00 minimum lift. Previously the minimum lift only sized the
   study, so a significant lift of BRL 1 would have been a GO. The primary
   test stays two-sided; direction enters through the decision rule.
5. **Guardrail outcomes.** The single "breached" flag conflated "not
   shown to be safe" with "measured to be unsafe". It is replaced by the
   passed, breached and inconclusive outcomes of section 8. Memo wording
   no longer asserts a delivery cause, and percentage points are shown to
   two decimals so a difference of 2.02 against a margin of 2.00 is not
   displayed as equal.
6. **Enforcement.** The frozen constants, the removal of the sample-size
   override, the drift check and the re-analysis guard of section 6 were
   added. The earlier check read the expected sample size from the same
   file the simulation used, so it could not fail.
7. **Freight figure.** The approximate BRL 23 freight figure was cited as
   coming from calibration, but `calibration.py` never read freight. The
   code now computes it on the next recalibration. The committed
   calibration file predates this and does not contain it, so the figure
   is unverified in this repository.
8. **Wording.** The power table no longer calls the `TTestIndPower`
   calculation Welch's test, prose currency is written as BRL to avoid
   dollar signs being read as math by markdown renderers, and the
   complaint metric is described as a review-score proxy, not a delivery
   measure.

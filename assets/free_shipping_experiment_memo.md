# Free Shipping Experiment: Stakeholder Memo

## Recommendation: NO-GO

Hold off. The complaint rate rose more than the agreed threshold, regardless of the AOV result. Fix delivery experience before revisiting free shipping.

## What we tested

We randomly split 5006 sellers into two groups: half kept
standard shipping, half switched to free shipping. We measured whether
free shipping changed average order value, and separately checked
whether it made delivery complaints worse.

## Order value result

Sellers offering free shipping had an average order value of
`R$ 173.42`, versus `R$ 144.41` for sellers on standard
shipping. That's a lift of **`R$ 29.02`** (95% confidence interval: `R$ 21.12` to
`R$ 36.91`). This interval does not include zero, so the lift is unlikely to be due to chance.

## Complaint rate check (guardrail)

Delivery complaints ran at 14.5% under free shipping versus 12.2%
under standard shipping, a difference of 2.3 percentage points. We had
pre-agreed that anything under 2.0 points was acceptable. This crossed that line.

## Bottom line

Fix delivery capacity or expectations before re-testing. Rerunning the same experiment without addressing what's driving complaints will likely breach the guardrail again.

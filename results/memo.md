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
`R$ 176.87`, versus `R$ 148.67` for sellers on standard
shipping. That's a lift of **`R$ 28.21`** (95% confidence interval: `R$ 19.42` to
`R$ 36.99`). This interval does not include zero, so the lift is unlikely to be due to chance.

## Complaint rate check (guardrail)

Delivery complaints ran at 14.0% under free shipping versus 12.0%
under standard shipping, a difference of 2.0 percentage points. We had
pre-agreed that anything under 2.0 points was acceptable. This crossed that line.

## Bottom line

Fix delivery capacity or expectations before re-testing. Rerunning the same experiment without addressing what's driving complaints will likely breach the guardrail again.

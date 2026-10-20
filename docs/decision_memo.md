# Decision memo, Hillstrom email test

This is an analysis of a public randomized experiment (MineThatData, 2008). About 64,000 customers who bought in the last 12 months were split evenly into a Mens email, a Womens email, and no email, and tracked for two weeks after the send. The analysis plan was committed before any outcome was compared across arms, see [experiment_design.md](experiment_design.md).

## Decision

**Send the Mens email to every customer in this population. Do not send the Womens email broadly.**

| | Mens vs No E-Mail | Womens vs No E-Mail | Mens vs Womens |
|---|---|---|---|
| Conversion lift | +0.68pp (1.25% vs 0.57%) | +0.31pp (0.88% vs 0.57%) | +0.37pp |
| Holm p, conversion | 4.4e-13 | 3.1e-04 | 3.1e-04 |
| Spend lift per customer | +$0.77 ($0.44 to $1.13) | +$0.42 ($0.14 to $0.72) | +$0.35 ($0.03 to $0.66) |
| Holm p, spend | 3.5e-07 | 2.3e-03 | 3.0e-02 |

Spend intervals are BCa bootstrap intervals with 50,000 resamples, at the level Holm uses for each comparison (98.33%, 97.5%, 95%).

## Why Mens

Mens is the only email whose conversion lift is both significant after Holm correction and above the 0.5 percentage point minimum set in advance. Womens is significant but below that minimum, so spend decides between the two, and Mens beats Womens by $0.35 per customer. The call holds under every version of the spend rule, at 5,000 and 50,000 resamples, and across all bootstrap seeds checked.

## Who gets which email

**Everyone in this population gets the Mens email.** Mens raised conversion significantly in 10 of the 11 pre-registered segments. The exception is Rural (+0.53pp), which was too small to tell (9 to 40% power), so it reads as inconclusive, not as no effect. No segment showed a negative effect for either email.

## Who gets none

**No one, based on this test.** A small no-email holdout on future sends would let the longer-run effect be measured, which this test cannot do.

## Expected incremental revenue

| | Per customer | Per 10,000 customers | 64,000 customers |
|---|---|---|---|
| Mens vs No E-Mail | $0.77 | $7,698 | **$49,269 ($27,869 to $72,101)** |
| Mens over Womens | $0.35 | $3,454 | $22,107 ($2,101 to $42,245) |

This is revenue from one send over two weeks. It is not profit, since the data has no margin or email cost, and it is not annualized, since short-window effects can fade or grow with repeat sends.

## Risks and caveats

- **The Mens lift could be below the practical bar.** Its 98.33% interval runs from 0.46pp to 0.90pp, so a true lift under 0.5pp cannot be ruled out.
- **The Mens over Womens margin is thin, and part of the rule came late.** The spend interval starts at $0.03. The spend bar, the Holm-matched interval levels, and the 50,000 resamples were set after conversion or spend results were known. Each is tagged in the design doc, and under the rule as first written Mens still ships through the fallback.
- **Guardrails were not measured.** The data has no unsubscribe or repeat-send outcomes, so list fatigue is untested.
- **Data limits.** The test ran in 2008 at one retailer, spend appears capped at $499 (12 customers sit at that value), and the dataset's rough results are widely known. The pre-registration shows the analysis choices came first, not that the answer was unknown.
- **Segment patterns are hypotheses.** Womens lifted conversion among new customers (+0.53pp) but barely among existing ones (+0.09pp). No interaction test was planned, so this is a lead for a future test, not a finding.

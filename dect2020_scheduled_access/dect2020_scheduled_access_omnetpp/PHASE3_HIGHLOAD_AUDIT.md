# Phase 3 OMNeT++ High-Load Audit

Status: **PASS**

GitHub Actions verification: run #38  
https://github.com/LisaGaydamaka/coworking/actions/runs/36572228829

## Scope

The audit checks the finite-buffer high-load theorem and the saturated comparative statics using only the independent OMNeT++ implementation.

Physical DECT grid:

- (D\in\{6,10,20\});
- (r\in\{5,30,50\});
- normalized load (ho/ho_{\rm sat}\in\{5,10,20,50\});
- 3 independent repetitions per point;
- 20,000 completed type-1 requests for warm-up;
- 50,000 measured type-1 completions per repetition.

This gives 36 physical parameter groups and 108 physical-grid OMNeT++ runs. Additional Corollary 1 checks bring the total to 46 groups and 138 runs.

The simulator records direct delay, mean type-1 population, blocking, effective throughput, type-1/type-2 service fractions, full-state occupation fractions, and phase-specific full-state fractions.

## Theorem 2: numerical convergence

For each physical-grid group the OMNeT++ estimate is compared with

[
\lambda_{\rm sat}=\frac{L}{Lm_B^{(1)}+m_F^{(1)}},
\qquad
\bar N_\infty=r+\rho_{\rm sat},
\qquad
\bar v_\infty=(r+1)m_B^{(1)}+\frac{r}{L}m_F^{(1)}.
]

| (ho/ho_{\rm sat}) | Mean abs. delay error | Max abs. delay error | Mean abs. (\bar N) error | Max abs. (\bar N) error | Mean abs. throughput error | Max abs. throughput error | Mean non-full fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5  | 2.208% | 6.513% | 2.253% | 6.619% | 0.103% | 0.215% | 0.20019 |
| 10 | 1.002% | 2.702% | 1.024% | 2.767% | 0.080% | 0.172% | 0.09989 |
| 20 | 0.467% | 1.195% | 0.472% | 1.192% | 0.062% | 0.111% | 0.04995 |
| 50 | 0.171% | 0.413% | 0.176% | 0.429% | 0.063% | 0.116% | 0.01999 |

The convergence is in the direction predicted by the theorem: the non-full occupation fraction decreases approximately as the reciprocal normalized load, while mean delay and mean population converge to their finite high-load limits.

At (ho/ho_{\rm sat}=50):

- mean absolute delay-limit error over the 9 physical ((D,r)) cases: **0.171%**;
- maximum absolute delay-limit error: **0.413%**;
- mean absolute mean-population error: **0.176%**;
- maximum absolute mean-population error: **0.429%**;
- mean absolute throughput-limit error: **0.063%**;
- maximum absolute throughput-limit error: **0.116%**;
- mean absolute error of the first-order blocking approximation
  (pi\approx1-\lambda_{\rm sat}/\lambda): **1.80e-5**;
- maximum absolute error of that approximation: **2.23e-5**.

The service-time fractions also agree with the cycle argument. At normalized load 50, the maximum absolute deviation of the measured type-1 service fraction from (ho_{\rm sat}) is about **1.44e-4**; the type-2 fraction has the same maximum absolute deviation from (1-ho_{\rm sat}).

The mean measured saturated-full-state fraction over the nine physical cases is:

- 0.79981 at factor 5;
- 0.90011 at factor 10;
- 0.95005 at factor 20;
- 0.98001 at factor 50.

Thus the continuous-time mass moves toward the full states as required by Theorem 2.

## Corollary 1: buffer-size increment

For fixed (D=10), (L=2), (m_F^{(1)}=9) ms and normalized load 50, the theorem gives

[
\bar v_\infty(r+1)-\bar v_\infty(r)
=
m_B^{(1)}+\frac{m_F^{(1)}}{L}
=
4.9166667\ {\rm ms}.
]

Using (r=5,10,20,30,40,50), the OMNeT++ finite-difference estimates per additional buffer place are:

| Buffer interval | OMNeT++ increment per place [ms] |
|---|---:|
| 5 -> 10 | 4.917392 |
| 10 -> 20 | 4.917378 |
| 20 -> 30 | 4.917374 |
| 30 -> 40 | 4.917392 |
| 40 -> 50 | 4.917358 |

These agree with the analytical increment to about (7.3\times10^{-4}) ms per buffer place.

## Corollary 1: service-limit comparison

To isolate the mathematical dependence on (L), this audit deliberately decouples (L) from the physical DECT mapping and holds (r=20), (m_B^{(1)}=10/24) ms, and (m_F^{(1)}=9) ms fixed. Each case uses normalized load 50.

The analytical delay changes are

[
\bar v_\infty(L+1)-\bar v_\infty(L)
=
-\frac{r m_F^{(1)}}{L(L+1)}.
]

| (L\to L+1) | Analytical change [ms] | OMNeT++ change [ms] |
|---|---:|---:|
| 1 -> 2 | -90.000 | -89.913 |
| 2 -> 3 | -30.000 | -29.969 |
| 3 -> 4 | -15.000 | -15.003 |

The measured saturated throughputs increase with (L), consistently with

[
\lambda_{\rm sat}(L+1)-\lambda_{\rm sat}(L)>0.
]

## Independent mathematical audit

The Phase-3 formulas were re-derived independently from the manuscript text.

1. A saturated cycle contains exactly (L) type-1 services and one type-2 service. Its mean duration is (Lm_B^{(1)}+m_F^{(1)}), yielding
   [
   \lambda_{\rm sat}=\frac{L}{Lm_B^{(1)}+m_F^{(1)}}.
   ]

2. For finite (r) and strictly positive service times, any finite number of free buffer positions is refilled before the next service completion with probability tending to one as (lambda\to\infty). Hence the stationary continuous-time mass concentrates on the full type-2 state and the (L) full type-1 phases.

3. Renewal reward over one saturated cycle yields the limiting occupation fractions
   [
   \frac{m_F^{(1)}}{Lm_B^{(1)}+m_F^{(1)}}
   quad\text{and}\quad
   \frac{m_B^{(1)}}{Lm_B^{(1)}+m_F^{(1)}}
   ]
   for the full type-2 state and for each full type-1 phase, respectively.

4. Exactly (L) type-1 requests complete per saturated cycle, so
   [
   \lambda(1-\pi)\to\lambda_{\rm sat}.
   ]
   Dividing by (lambda) gives
   [
   \pi=1-\frac{\lambda_{\rm sat}}{\lambda}+o(1/\lambda).
   ]

5. Cycle-average population gives
   [
   \bar N_\infty=r+\rho_{\rm sat},
   ]
   and Little's law for admitted traffic gives
   [
   \bar v_\infty=(r+1)m_B^{(1)}+\frac{r}{L}m_F^{(1)}.
   ]

6. The Corollary 1 signs and finite differences follow by direct subtraction/differentiation. No global finite-load monotonicity of blocking in (r) is asserted.

No mathematical inconsistency was found in Proposition 1, Theorem 2, Corollary 1, or their Appendix proof.

## Phase 3 conclusion

The mathematical re-derivation and the independent OMNeT++ audit support the Phase-3 saturation/high-load results. The numerical convergence is consistent across all three physical DECT mappings and across the separate comparative-statics checks.

Reproducible source data:

- `ci_results/phase3_highload_scalars.csv`;
- `ci_results/phase3_highload_metrics.csv`;
- `ci_results/phase3_highload_run.log`;
- `simulations/omnetpp.ini`;
- `run_phase3_highload.sh`.

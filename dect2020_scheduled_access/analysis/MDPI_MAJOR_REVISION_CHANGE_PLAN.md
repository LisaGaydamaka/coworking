# Sensors 4690467 — minimal complete manuscript-change plan
Status: **PLANNING ONLY; original LaTeX manuscript has NOT been modified.**
Source manuscript: editor-provided \`template.tex\` in MDPI Article Google Drive.
Reviewer sources: verbatim Round-1 reports by reviewers 1, 2, and 3.
Numeric sources: GitHub Actions' \`revision_output/\` and OMNeT++ \`ci_results/\`.

The current paper has Sections 1-8. Keep its title, eight-section architecture,
Theorem 1, Proposition 1, Theorem 2, and original supporting proofs.
Use original validation solely as *verification of the abstract vacation queue*.
Do not present that model's agreement as physical DECT-2020 compliance.

## 1. Compact minimum change matrix

| ID | Manuscript location | Minimal replacement/insert | Reviewer |
|---|---|---|---|
| 01 | Abstract, Sec 2.2, Conclusions | Replace nonstandard \`M,M\|G,D\|1\|<r,L>\` with finite-capacity M/G/1/(r+1) queue with L-limited service/multiple deterministic vacations; one external Poisson arrival stream; internally generated type-2 vacation intervals, not another Poisson stream | R1+R2 |
| 02 | Intro Sec 1.2,1.3 | Remove claim of fundamental originality for classical stability/vacation theory and bunker equivalence; identify novelty in DECT parameterization, explicit boundary treatment, quantitative fixed-slot validation, practical dimensioning and tails; compare Lee 1989, Gupta 2005 and ITTMM 2026 | R2 |
| 03 | Sec 1.2 literature | Replace omnibus 25-reference citation with selective synthesized topic-specific references; make links to classical polling/TDMA and limited-vacation queue work | R2+R3 |
| 04 | Sec 2.1/2.2 | Define the 10ms/24-slot single tagged PT, r waiting + at most 1 in service, fixed clock vs restart-on-empty distinction, full 24-slot optimistic PT-eligible budget vs FT overhead, and limitations of FT/coexistence/PHY | R1+R2+R3 |
| 05 | Sec 3 stability & high load | Keep exact proofs/formula, add saturated-cycle physical interpretation; note capacity threshold standard, and finite delay at unbounded offered load follows finite r and rejection, not artificial chain truncation | R1+R2 |
| 06 | Sec 4.1/4.2 existing verification | PRESERVE original Eq. 46-type \`F=10-10/D\`, three-case configuration table, 27-case statistics and high-load analytical work, explicitly labeled **original abstract model** | R2+R3 |
| 07 | Sec 4.2 confidence intervals | Add original 22/27 delay CIs covered, remaining 5 near saturation; 20x5M long-run tests cover all 5 with max 0.1453% absolute relative delay error. Cite five-case supplement | R2 |
| 08 | Sec 4 new subsection | Explain independent idealized fixed-slot OMNeT++ baseline: absolute repeated 10ms frame, 24 slots, one deterministic packet/slot, anchored opportunities, fixed position even when empty; 27-case physical grid; limitations. Insert physical-vs-analytic 27-case scatter | R2+R3 |
| 09 | Sec 4/5 corrected mapping | Distinguish original historical \`F_old=10-10/D\` from corrected frame-aligned \`F_new=10-L*10/24\`; \`lambda_sat=L/10\` packets/ms; e.g D10 0.2033898 -> 0.2. Keep identical input arrival rates in model comparisons | R2+R3 |
| 10 | Sec 5.1 replace Fig operating map | Replace legacy \`media/figure_B_operating_regime_map.pdf\` with \`revision_corrected_figure_B_operating_map.pdf\` and corrected deterministic analytical data. Critically change narrative: **D values with same L now have identical thresholds; NO within-band mF slope** | R2+R3 |
| 11 | Sec 5.1 replace Table 4 | Use \`revision_corrected_selected_table4.csv\` six D={2,6,10,13,20,24} and corrected deterministic rho at nominal pi=1,5,10%. Do not use old D10 .08335,.08895,.09414. Add separate empirical six-D table or figure with explicitly *exponential-analytic design rates*, because D2 at nominal 1% gives physical 0.6723% | R2+R3 |
| 12 | Sec 5.2 replace Fig trade-off | Replace \`media/figure_C_delay_loss_tradeoff.pdf\` with \`revision_corrected_figure_C_delay_loss.pdf\`; fixed D10 L2 r1..50, 0.8/1.0/1.2 corrected normalized load, deterministic B and F=9.166667ms. Replace ALL descriptive sample values from original Fig C; labels reduced to r=10 and r=40 | R2+R3 |
| 13 | Sec 5.3 add QoS example | Use illustrative access-layer \`pi<=1%\`, \`P99<=50ms\` (NOT standardized URLLC mandate). At nominal exponential-queue 1% design rates, D2 physical P99=24.706ms and pi=.6723%; D6 P99=73.811ms and pi=.9655%, so only D2 passes both among sampled D values. Reference application-specific limits responsibly | R2+R3 |
| 14 | Sec 6 replace original Fig D | Replace old vacation-queue tail graph with \`revision_fixed_slot_figure_D_tail_latency.pdf\`: physical fixed clock D10/r30 load .5..5 mean/P95/P99, 95% CIs and log x scale explicitly explained. Original legacy tail can be labeled supplemental, not silently compared at differing saturations | R2+R3 |
| 15 | Sec 6 or 4 exact high-load finite comparison | Original vacation queue simulation at original normalized load 5: 146.59ms mean vs exact finite-load analytical 146.5874ms, NOT vs its 147.9167ms infinite-lambda limit; mention asymptote separately if relevant | R2 |
| 16 | Sec 6 / Sec 7 service variability | Corrected 10ms-cycle deterministic/exponential/hyperexponential_SCv4 90-run experiment exists. Suggested supplemental P99 figure; include only if author approves. At load1.2 P99 150.22/152.96/158.63ms, explicitly **vacation queue**, not physical fixed-slot under random service | R2 |
| 17 | Sec 7 arrival sensitivity | Replace claim that correlated/periodic is wholly unstudied; give Poisson vs periodic vs bursty equal mean rate evidence: D10/r30 lambda .2, blocking Poisson 1.672%, randomized-phase periodic 0%, synchronized periodic 0%, geometric-burst compound Poisson 10.450%. Note model sensitivity/assumptions | R3 |
| 18 | Sec 7 FT/slot/coexistence | Cite S22 vs S24 and distributed-vs-consecutive physical sensitivity, e.g at D6 L4->L3, saturated capacity .4->.3 packet/ms; at D10 L2 unchanged; no physical FT-radio modeling or actual ETSI implementation claimed | R2+R3 |
| 19 | Sec 7 / Sec 8 scope | Clearly distinguish low-latency vs stringent URLLC, admitted-only delay vs rejection, fixed finite allocation validity, no PHY/ARQ interference/multihop. Note analytic admitted-delay CDF/P95/P99 not derived; simulated P95/P99, possible future extension; *not* claim reviewer requested analytical tail is done | R2+R3 |
| 20 | Intro, Abstract, Contributions, Conclusions | Harmonize notation, original vs corrected baselines, physical validation, figures, numbers, cautious novelty, and strongest conclusions across all four sections | R1+R2+R3 |
| 21 | References | Cite Lee (1989), Gupta et al. (2005), ITTMM 2026 in novelty position; add reviewer-suggested Milovanovic/Bojkovic 2023 verticals chapter, Famaey et al IEEE COMST 2026 DOI 10.1109/COMST.2026.3727751, Alhulayil et al IEEE Access 2025 DOI 10.1109/ACCESS.2025.3564136. Discuss or remove unaddressed original [1],[5],[6],[13],[20],[24],[25] | R2+R3 |
| 22 | Back matter and visual editorial | Resolve Figure 6 r labels (replaced corrected Fig C has only two); Figure 7 axis log justified (new physical Fig D); abbreviations add PASTA,CDF,MAC,QoS, keep existing IIoT/mMTC; consistent Yu.V.G.; update data-availability provenance for both original and revision repositories, pin source SHAs/releases | R3 / MDPI |
| 23 | Submission assets | Point-by-point response to every quote; identify manuscript page/line once revised; cite sources and repository; if requested produce marked-up copy, old/new figures and labeled supplementary tables. Confirm LaTeX compile, complete figure references, bibliography, and MDPI GenAI disclosure rules when applicable | Editor/MDPI |

## 2. Figure inventory

### Main paper (recommended minimum; 2 inserted, 3 replaced)

- **NEW in Sec 4**: \`revision_27case_mean_delay_comparison.pdf\` (physical vs original, corrected exp and corrected det).
- **NEW in Sec 5**: \`revision_final_sixD_blocking_validation.pdf\` (physical nominal-blocking contours, error bars).
- **REPLACE existing operating-map figure**: \`revision_corrected_figure_B_operating_map.pdf\`.
- **REPLACE existing delay-loss figure**: \`revision_corrected_figure_C_delay_loss.pdf\`.
- **REPLACE existing mean/P95/P99 Figure D**: \`revision_fixed_slot_figure_D_tail_latency.pdf\`.
- Keep earlier network, timing, queue schematic, and polling illustrations.
- PDFs vector; new alternative PNGs generated at 600 dpi. Do not number manually; LaTeX \`\label/\ref\` manages numbering.

### Supplementary / optional paper comparison plots

- \`revision_physical_vs_original_tail_p99.pdf\`: different model tail rates on a common physical-capacity scale.
- \`revision_final_saturation_convergence.pdf\`: 5 cases original vs 20x5M CI checks.
- \`revision_final_sixD_delay_approximation_error.pdf\`: corrected deterministic queue error.
- \`revision_traffic_sensitivity_blocking.pdf\`: four arrival processes.
- \`revision_slot_position_sensitivity_p99.pdf\`: contiguous vs distributed scheduled slots.
- \`revision_FT_slot_reservation_capacity.pdf\`: S24 vs S22 capacity.
- \`revision_corrected_service_variability_p99.pdf\`: corrected service variability; **optional, do not automatically include**.

## 3. Table inventory

- Keep original Section-4 three-D queue verification configurations (explicitly label legacy \`F_old\`).
- Keep original Section-4 27-case error summary and selected baseline table as historical model-verification evidence.
- Add (main or supplementary) \`revision_final_saturation_five_cases.csv\`, 5 saturation cases, with original vs long-run 95% CI.
- REPLACE Section-5 3-row dimensioning table with 6-row \`revision_corrected_selected_table4.csv\` (deterministic rho thresholds 1,5,10%). Exact D10 values: 0.0819852333, 0.0874712270, 0.0925755292.
- Add physical 18-point \`revision_final_sixD_dimensioning.csv\` as a companion comparison; do NOT call its exponential-based lambda-grid exactly the deterministic contour.
- Optional supplementary: \`revision_corrected_delay_loss_tradeoff.csv\`, \`revision_traffic_sensitivity_blocking.pdf\` and the 22-slot budget/geometry CSV.

## 4. Required numerical replacements outside the table

- Section 4 old D10 capacity: retain 0.2033898 packets/ms as *legacy model*.
- Section 5 corrected D10 capacity: 0.2000000 packets/ms and rho_sat 0.0833333.
- Section 5.2 corrected deterministic at D10 r30 physical factor1:
  analytical mean 75.7468 ms and blocking 1.67269%.
- Section 6 fixed-slot at D10 r30 factor0.9:
  mean 26.3449 ms, P95 74.1180 ms, P99 108.9520 ms.
- Section 6 fixed-slot at D10 r30 factor1:
  mean 75.7636 ms, P95 142.0230 ms, P99 148.4820 ms, blocking 1.67867%.
- Section 6 fixed-slot at D10 r30 factor1.2:
  mean 135.9716 ms, P95 149.4538 ms, P99 150.2201 ms.
- Section 6 fixed-slot at D10 r30 factor5:
  mean 149.0860 ms, P95 150.3404 ms, P99 150.4017 ms;
  blocking ~79.994%, so admitted-only tails must not suggest feasibility.
- On the new physical tail grid, largest 95% CI halfwidth is
  0.7738 ms for P95 and 1.0713 ms for P99; replace legacy
  interval-width claims in Section 6 if still present.
- Section 5.2 at D10 factor1 r50:
  corrected deterministic mean 125.7396ms and blocking 1.00217%
  (NOT legacy 123.65ms and ~1.01%).
- Original/analytical abstract load5 comparison: simulation ~146.59ms,
  exact finite-load ~146.5874ms, asymptote 147.9167ms.
- Exemplar at nominal physical one-percent design with r30:
  D2 ~0.6723% pi, P99 24.706ms; D6 ~0.9655%, P99 73.811ms.
- Saturation CI: 22/27 original cases cover; five revised long-run
  replications all cover, largest relative error 0.1453% among the five.
- Novelty: no claims of new classical vacation stability threshold,
  or exact DECT PHY performance/strict URLLC conformance.

## 5. Final scientific and MDPI audit

1. Verify all Section 5 curves/tables and its prose use corrected
   \`mF_new=10-L*10/24\`, NEVER mixture with old figures/values.
2. Verify Chapter 4 is explicitly old abstract simulator verification;
   new Chapter 4 subsection is idealized fixed-clock independent simulation.
3. Verify all absolute lambdas and normalized loads are matched correctly;
   physical and old models have different lambda_sat.
4. State quantile and CI method: replication-level empirical percentile,
   95% Student-t, P99 conditional on admission.
5. Keep supplementary figure/table numbering as Figure S1 / Table S1
   and explain source filenames and comparisons.
6. Update source code reproducibility with immutable commit, dataset release,
   distinct original v. revision Github locations and exact simulation settings.
7. Check MDPI figure captions, all labels, double symbols, references,
   bibliography DOIs, legend readability and English before submitting.
8. Review editorial disclosure for GenAI-assisted code/research analysis
   according to current Sensors Instructions for Authors.
9. Write complete three-reviewer point-by-point response letter.

No work on submitted/editor-provided LaTeX \`template.tex\` is performed by
this checklist or figure-generation workflow.

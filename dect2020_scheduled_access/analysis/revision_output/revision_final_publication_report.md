# Final pre-manuscript experiment audit (GitHub Actions)

## Experimental scope
- New physical-slot Table-4 checks: 3 D values x 3 rates x 10 replications = 90 runs.
- Extended original-simulator audit: 5 cases x 20 replications = 100 runs.
- Original model: 1 million warm-up and 5 million measured admitted completions/run.
- Source code: original vacation-queue C++ unchanged; physical model idealized 10-ms/24-slot MAC.

## Five exact finite-load original-queue checks
- Analytical mean within long-run 95% CI: 5/5 cases.
- Largest absolute long-run relative mean-delay error: D=10, r=50, 0.14529%.
- D=10, r=20: analytical 49.921313 ms; long-run 49.954920 +/- 0.067285 ms (95%); covered=True.
- D=10, r=50: analytical 123.654645 ms; long-run 123.834309 +/- 0.593516 ms (95%); covered=True.
- D=20, r=5: analytical 25.912900 ms; long-run 25.911759 +/- 0.008696 ms (95%); covered=True.
- D=20, r=20: analytical 100.303266 ms; long-run 100.367014 +/- 0.133892 ms (95%); covered=True.
- D=20, r=50: analytical 249.056259 ms; long-run 249.107134 +/- 1.141622 ms (95%); covered=True.

## Fixed-slot six-D dimensioning
- D=2, L=12; fixed-slot blocking at nominal 1%,5%,10%: 0.6723%, 4.7227%, 9.9223%.
- D=6, L=4; fixed-slot blocking at nominal 1%,5%,10%: 0.9655%, 4.9665%, 9.9682%.
- D=10, L=2; fixed-slot blocking at nominal 1%,5%,10%: 0.9926%, 4.9855%, 9.9765%.
- D=13, L=1; fixed-slot blocking at nominal 1%,5%,10%: 1.0010%, 4.9909%, 9.9801%.
- D=20, L=1; fixed-slot blocking at nominal 1%,5%,10%: 0.9993%, 4.9878%, 9.9749%.
- D=24, L=1; fixed-slot blocking at nominal 1%,5%,10%: 1.0010%, 4.9909%, 9.9801%.

## Manuscript-ready items
- Table: revision_final_saturation_five_cases.csv
- Table: revision_final_sixD_dimensioning.csv
- Figure: revision_final_saturation_convergence.pdf
- Figure: revision_final_sixD_blocking_validation.pdf
- Figure: revision_final_sixD_delay_approximation_error.pdf

Interpretation caveat: nominal 1/5/10% targets are analytical design points; empirical fixed-slot probabilities are separately shown.
Do not claim full ETSI PHY conformance or independent in-network multi-user scheduling based on the tagged-PT scheduler.

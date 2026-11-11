# Long-run original-queue saturation audit (GitHub Actions)
5 original mismatch cases, 20 repetitions each, 1,000,000 warm-up
and 5,000,000 measured completions per new replication.
Published C++ queue model and original Phase-2 CSV unchanged.
Ten old seeds are intentionally reused for a paired robustness check.
Analytical comparison is calculated in analysis/revision_final_analysis.py.

D=10 r=20: old 49.685241 +/- 0.190581 ms, long 49.954920 +/- 0.067285 ms (95%)
D=10 r=50: old 122.073566 +/- 1.155568 ms, long 123.834309 +/- 0.593516 ms (95%)
D=20 r=5: old 25.872347 +/- 0.019643 ms, long 25.911759 +/- 0.008696 ms (95%)
D=20 r=20: old 99.753053 +/- 0.307144 ms, long 100.367014 +/- 0.133892 ms (95%)
D=20 r=50: old 246.365045 +/- 1.649950 ms, long 249.107134 +/- 1.141622 ms (95%)

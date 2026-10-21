# Forecast four domains under stable conditions

Separate univariate models for D1, D2, D3, D4 on each interval PBS 0->16, PBS 16->24, LPS 16->24. No edits to prior experiments. Uses four EFA baseline-frozen domain scores and evaluates Ridge(alpha=1) via leave-one-mouse-out against persistence and training mean. All results written to results/ by GitHub Actions. Critical limitations: only living paired animals; EFA fit outside CV; very small n. Run with bash run.sh.

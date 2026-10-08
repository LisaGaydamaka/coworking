# PCA31 by group and week

Independent experiment. Existing PCA/EFA/eNRI files are not modified.

For each of the 12 combinations PBS/LPS/run/MCC × week 0/16/24, PCA is fit
separately on the same cleaned 31-feature processed matrix after the seven full
mouse×week state exclusions. No extra standardization is applied; sklearn PCA
only centers the variables within each subgroup.

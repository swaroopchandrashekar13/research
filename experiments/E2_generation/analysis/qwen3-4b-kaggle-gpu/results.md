# E2 Tier 2 generation — EXPLORATORY (Tier 2; pre-specified plan, not part of the frozen confirmatory hypotheses)

DiD = Δ(budget 1,024 words) − Δ(top-5), Δ = metric(A) − metric(B). E1 predicts DiD > 0 for both claims.

## Pooled (equal weight per dataset, stratified bootstrap, 2,000 resamples)

| Claim | Measure | DiD | 95% CI | n | MDE | Verdict |
|---|---|---:|---|---:|---:|---|
| P1 | f1 | -0.017 | [-0.065, +0.033] | 200 | 0.068 | inconclusive |
| P1 | em | -0.055 | [-0.100, -0.010] | 200 | 0.066 | opposite |
| P1 | coverage | +0.089 | [+0.050, +0.132] | 200 | 0.059 | carries over |
| S3-256 | f1 | +0.004 | [-0.024, +0.036] | 200 | 0.044 | inconclusive |
| S3-256 | em | -0.015 | [-0.050, +0.020] | 200 | 0.051 | inconclusive |
| S3-256 | coverage | +0.035 | [+0.015, +0.060] | 200 | 0.036 | carries over |

## Per dataset (answer F1)

| Dataset | Claim | Δ top-5 [CI] | Δ budget-1,024 [CI] | DiD [CI] | n |
|---|---|---|---|---|---:|
| squad2 | P1 | -0.018 [-0.140, +0.097] | -0.140 [-0.241, -0.052] | -0.122 [-0.245, +0.009] | 50 |
| squad2 | S3-256 | +0.011 [-0.082, +0.107] | -0.016 [-0.115, +0.083] | -0.027 [-0.104, +0.049] | 50 |
| covidqa | P1 | +0.012 [-0.076, +0.105] | +0.006 [-0.065, +0.074] | -0.006 [-0.101, +0.090] | 50 |
| covidqa | S3-256 | +0.030 [-0.060, +0.122] | +0.035 [-0.044, +0.121] | +0.005 [-0.050, +0.066] | 50 |
| cuad | P1 | +0.022 [-0.001, +0.046] | +0.021 [-0.004, +0.051] | -0.001 [-0.031, +0.033] | 50 |
| cuad | S3-256 | -0.007 [-0.027, +0.011] | -0.015 [-0.037, +0.006] | -0.008 [-0.027, +0.012] | 50 |
| qasper | P1 | -0.037 [-0.113, +0.034] | +0.023 [-0.029, +0.078] | +0.060 [-0.015, +0.158] | 50 |
| qasper | S3-256 | -0.015 [-0.077, +0.041] | +0.030 [-0.019, +0.087] | +0.045 [-0.017, +0.117] | 50 |

## Diagnostics

- **squad2**: 400 ok jobs, complete queries 50; status {'ok': 400}; finish {'stop': 400}; served {'Qwen/Qwen3-4B-GGUF@[revision removed]/Qwen3-4B-Q4_K_M.gguf': 400}; unanswerable rate 0.043
- **covidqa**: 400 ok jobs, complete queries 50; status {'ok': 400}; finish {'stop': 400}; served {'Qwen/Qwen3-4B-GGUF@[revision removed]/Qwen3-4B-Q4_K_M.gguf': 400}; unanswerable rate 0.058
- **cuad**: 400 ok jobs, complete queries 50; status {'ok': 400}; finish {'stop': 335, 'length': 65}; served {'Qwen/Qwen3-4B-GGUF@[revision removed]/Qwen3-4B-Q4_K_M.gguf': 400}; unanswerable rate 0.150
- **qasper**: 400 ok jobs, complete queries 50; status {'ok': 400}; finish {'stop': 398, 'length': 2}; served {'Qwen/Qwen3-4B-GGUF@[revision removed]/Qwen3-4B-Q4_K_M.gguf': 400}; unanswerable rate 0.158

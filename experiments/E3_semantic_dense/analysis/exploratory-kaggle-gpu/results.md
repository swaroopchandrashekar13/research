# Study 1b results — EXPLORATORY

Queries: squad2 1184, covidqa 248, cuad 248, qasper 460

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H4 | 42.7% | [33.0%, 49.2%] | 20.0% | supported |
| H4b | 45.1% | [35.1%, 51.6%] | 10.0% | supported |
| H5 | 8.3% | [6.2%, 22.9%] | 20.0% | inconclusive |
| H5b | 60.4% | [35.4%, 68.8%] | 20.0% | supported |

## H4 sensitivity (share supporting the shorter arm, budget − count)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 39.4% | — |
| b_without_squad2 | 36.6% | [24.1%, 44.1%] |
| d_cluster_bootstrap | 46.8% | [32.9%, 49.3%] |
| e_all_budgets | 47.4% | [36.3%, 50.4%] |
| f_bm25_only | 38.0% | [29.9%, 51.6%] |
| f_dense_only | 47.5% | [29.9%, 53.9%] |

## Mean chunk length (words) and the shorter arm

| Dataset | fixed-128 | fixed-256 | fixed-512 | semantic-bp | semantic-cl |
|---|---:|---:|---:|---:|---:|
| squad2 | 126 | 249 | 485 | 293 | 456 |
| covidqa | 126 | 247 | 483 | 287 | 455 |
| cuad | 127 | 252 | 495 | 320 | 458 |
| qasper | 126 | 247 | 477 | 278 | 452 |

## Semantic arm supported (descriptive, sensitivity g)

| Claim | Protocol | Universes | Supports semantic | Supports fixed | Inconclusive |
|---|---|---:|---:|---:|---:|
| S5-128 | count | 96 | 41.7% | 6.2% | 52.1% |
| S5-128 | budget | 72 | 8.3% | 66.7% | 25.0% |
| S5-256 | count | 96 | 28.1% | 2.1% | 69.8% |
| S5-256 | budget | 72 | 5.6% | 38.9% | 55.6% |
| S5-512 | count | 96 | 9.4% | 2.1% | 88.5% |
| S5-512 | budget | 72 | 40.3% | 0.0% | 59.7% |
| S6-128 | count | 96 | 43.8% | 3.1% | 53.1% |
| S6-128 | budget | 72 | 0.0% | 76.4% | 23.6% |
| S6-256 | count | 96 | 19.8% | 0.0% | 80.2% |
| S6-256 | budget | 72 | 0.0% | 51.4% | 48.6% |
| S6-512 | count | 96 | 15.6% | 8.3% | 76.0% |
| S6-512 | budget | 72 | 26.4% | 5.6% | 68.1% |

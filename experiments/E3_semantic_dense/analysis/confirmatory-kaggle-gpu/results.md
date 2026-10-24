# Study 1b results — CONFIRMATORY

Queries: squad2 4744, covidqa 1771, cuad 996, qasper 1742

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H4 | 55.4% | [50.8%, 63.1%] | 20.0% | supported |
| H4b | 64.4% | [56.5%, 68.3%] | 10.0% | supported |
| H5 | 19.4% | [16.7%, 41.7%] | 20.0% | inconclusive |
| H5b | 58.3% | [45.1%, 64.6%] | 20.0% | supported |

## H4 sensitivity (share supporting the shorter arm, budget − count)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 54.3% | — |
| b_without_squad2 | 48.0% | [42.7%, 58.3%] |
| d_cluster_bootstrap | 58.7% | [50.0%, 63.3%] |
| e_all_budgets | 53.7% | [49.7%, 60.9%] |
| f_bm25_only | 61.1% | [57.2%, 72.5%] |
| f_dense_only | 49.8% | [39.1%, 58.1%] |

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
| S5-128 | count | 96 | 60.4% | 16.7% | 22.9% |
| S5-128 | budget | 72 | 8.3% | 75.0% | 16.7% |
| S5-256 | count | 96 | 38.5% | 4.2% | 57.3% |
| S5-256 | budget | 72 | 1.4% | 51.4% | 47.2% |
| S5-512 | count | 96 | 7.3% | 24.0% | 68.8% |
| S5-512 | budget | 72 | 68.1% | 0.0% | 31.9% |
| S6-128 | count | 96 | 53.1% | 2.1% | 44.8% |
| S6-128 | budget | 72 | 0.0% | 97.2% | 2.8% |
| S6-256 | count | 96 | 46.9% | 0.0% | 53.1% |
| S6-256 | budget | 72 | 0.0% | 83.3% | 16.7% |
| S6-512 | count | 96 | 18.8% | 17.7% | 63.5% |
| S6-512 | budget | 72 | 33.3% | 11.1% | 55.6% |

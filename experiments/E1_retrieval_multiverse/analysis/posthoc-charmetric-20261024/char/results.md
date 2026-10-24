# Study 1 results — POSTHOC

> **POST-HOC SENSITIVITY ANALYSIS (2026-10-24) — not pre-registered.** Same pre-registered analysis code and thresholds applied to an alternative metric definition on re-executed retrieval selections; it does not replace or change any pre-registered result.

Datasets: squad2, covidqa, cuad, qasper; queries: squad2 4744, covidqa 1771, cuad 996, qasper 1742

Resampling: 2,000 paired percentile-bootstrap resamples per universe (seed 7); 1,000 joint query-bootstrap replicates for share CIs (seed 11; H2 seed 13).

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H1 | 70.4% | [63.9%, 80.3%] | 20.0% | supported |
| H1b | 24.2% | [13.5%, 30.7%] | 10.0% | supported |
| H2 | dataset η² largest in 100.0% of replicates | — | 95% | supported |
| H3 | 85.5% of universes need n > 500 (median n = 1275) | — | > 50% | supported |

H2 point estimates (η²): dataset 0.590, retriever 0.040, budget 0.057, metric 0.060

## H1 sensitivity analyses (P1: share supporting fixed-512, count − budget)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 67.1% | — |
| b_without_squad2 | 60.8% | [52.8%, 73.4%] |
| c_default_retriever | 70.8% | [64.6%, 83.3%] |
| d_cluster_bootstrap | 68.9% | [62.8%, 80.4%] |
| e_all_budgets | 73.8% | [67.8%, 83.9%] |

## Verdict shares per claim and protocol

| Claim | Role | A vs B | Protocol | Universes | Supports A | Supports B | Inconclusive |
|---|---|---|---|---:|---:|---:|---:|
| P1 | primary | fixed-128 vs fixed-512 | count | 768 | 0.0% | 78.9% | 21.1% |
| P1 | primary | fixed-128 vs fixed-512 | budget | 576 | 79.0% | 8.5% | 12.5% |
| S1-64 | secondary | fixed-64 vs fixed-128 | count | 768 | 0.0% | 84.1% | 15.9% |
| S1-64 | secondary | fixed-64 vs fixed-128 | budget | 960 | 19.5% | 42.6% | 37.9% |
| S1-128 | secondary | fixed-128 vs fixed-256 | count | 768 | 0.0% | 75.4% | 24.6% |
| S1-128 | secondary | fixed-128 vs fixed-256 | budget | 768 | 57.4% | 10.3% | 32.3% |
| S1-256 | secondary | fixed-256 vs fixed-512 | count | 768 | 0.0% | 64.2% | 35.8% |
| S1-256 | secondary | fixed-256 vs fixed-512 | budget | 576 | 77.4% | 8.0% | 14.6% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | count | 768 | 56.5% | 1.8% | 41.7% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | budget | 960 | 62.4% | 1.9% | 35.7% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | count | 768 | 56.4% | 1.8% | 41.8% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | budget | 960 | 59.2% | 1.5% | 39.4% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | count | 768 | 45.2% | 3.5% | 51.3% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | budget | 768 | 46.6% | 3.0% | 50.4% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | count | 768 | 12.4% | 8.2% | 79.4% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | budget | 576 | 13.7% | 6.6% | 79.7% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | count | 768 | 62.5% | 6.0% | 31.5% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | budget | 960 | 75.3% | 0.0% | 24.7% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | count | 768 | 60.8% | 1.3% | 37.9% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | budget | 960 | 79.9% | 0.0% | 20.1% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | count | 768 | 52.6% | 2.5% | 44.9% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | budget | 768 | 76.8% | 0.5% | 22.7% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | count | 768 | 21.5% | 1.7% | 76.8% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | budget | 576 | 62.7% | 1.6% | 35.8% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | count | 768 | 62.0% | 6.1% | 31.9% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | budget | 960 | 72.1% | 1.0% | 26.9% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | count | 768 | 53.1% | 0.9% | 46.0% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | budget | 960 | 61.3% | 0.0% | 38.8% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | count | 768 | 26.2% | 1.6% | 72.3% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | budget | 768 | 44.1% | 0.0% | 55.9% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | count | 768 | 10.4% | 0.3% | 89.3% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | budget | 576 | 23.1% | 0.3% | 76.6% |

## Legacy limitations of the input manifests (reported, not filled in)

- squad2: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- covidqa: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- cuad: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- qasper: manifest config has no 'study' field (historical Study 1 format); treated as '1'

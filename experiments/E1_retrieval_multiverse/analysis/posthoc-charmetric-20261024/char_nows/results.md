# Study 1 results — POSTHOC

> **POST-HOC SENSITIVITY ANALYSIS (2026-10-24) — not pre-registered.** Same pre-registered analysis code and thresholds applied to an alternative metric definition on re-executed retrieval selections; it does not replace or change any pre-registered result.

Datasets: squad2, covidqa, cuad, qasper; queries: squad2 4744, covidqa 1771, cuad 996, qasper 1742

Resampling: 2,000 paired percentile-bootstrap resamples per universe (seed 7); 1,000 joint query-bootstrap replicates for share CIs (seed 11; H2 seed 13).

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H1 | 71.1% | [64.9%, 81.9%] | 20.0% | supported |
| H1b | 26.2% | [15.0%, 33.2%] | 10.0% | supported |
| H2 | dataset η² largest in 100.0% of replicates | — | 95% | supported |
| H3 | 85.4% of universes need n > 500 (median n = 1263) | — | > 50% | supported |

H2 point estimates (η²): dataset 0.620, retriever 0.044, budget 0.096, metric 0.029

## H1 sensitivity analyses (P1: share supporting fixed-512, count − budget)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 68.3% | — |
| b_without_squad2 | 61.5% | [53.4%, 74.7%] |
| c_default_retriever | 70.8% | [64.6%, 85.4%] |
| d_cluster_bootstrap | 69.8% | [64.0%, 81.9%] |
| e_all_budgets | 74.2% | [68.4%, 84.9%] |

## Verdict shares per claim and protocol

| Claim | Role | A vs B | Protocol | Universes | Supports A | Supports B | Inconclusive |
|---|---|---|---|---:|---:|---:|---:|
| P1 | primary | fixed-128 vs fixed-512 | count | 768 | 0.0% | 78.8% | 21.2% |
| P1 | primary | fixed-128 vs fixed-512 | budget | 576 | 81.2% | 7.6% | 11.1% |
| S1-64 | secondary | fixed-64 vs fixed-128 | count | 768 | 0.0% | 84.1% | 15.9% |
| S1-64 | secondary | fixed-64 vs fixed-128 | budget | 960 | 20.2% | 41.5% | 38.3% |
| S1-128 | secondary | fixed-128 vs fixed-256 | count | 768 | 0.0% | 75.7% | 24.3% |
| S1-128 | secondary | fixed-128 vs fixed-256 | budget | 768 | 60.8% | 6.2% | 32.9% |
| S1-256 | secondary | fixed-256 vs fixed-512 | count | 768 | 0.0% | 63.3% | 36.7% |
| S1-256 | secondary | fixed-256 vs fixed-512 | budget | 576 | 78.0% | 2.1% | 20.0% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | count | 768 | 51.4% | 1.8% | 46.7% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | budget | 960 | 54.8% | 1.9% | 43.3% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | count | 768 | 51.6% | 1.8% | 46.6% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | budget | 960 | 54.8% | 1.9% | 43.3% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | count | 768 | 36.7% | 3.5% | 59.8% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | budget | 768 | 41.3% | 2.7% | 56.0% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | count | 768 | 9.6% | 8.5% | 81.9% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | budget | 576 | 12.0% | 6.9% | 81.1% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | count | 768 | 62.2% | 5.2% | 32.6% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | budget | 960 | 75.2% | 0.0% | 24.8% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | count | 768 | 60.4% | 1.3% | 38.3% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | budget | 960 | 79.8% | 0.0% | 20.2% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | count | 768 | 50.7% | 2.5% | 46.9% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | budget | 768 | 76.8% | 0.5% | 22.7% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | count | 768 | 14.1% | 1.7% | 84.2% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | budget | 576 | 60.9% | 1.6% | 37.5% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | count | 768 | 58.9% | 4.6% | 36.6% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | budget | 960 | 69.1% | 0.0% | 30.9% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | count | 768 | 51.4% | 0.8% | 47.8% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | budget | 960 | 57.3% | 0.0% | 42.7% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | count | 768 | 20.6% | 1.6% | 77.9% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | budget | 768 | 40.2% | 0.0% | 59.8% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | count | 768 | 6.2% | 0.3% | 93.5% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | budget | 576 | 21.9% | 0.3% | 77.8% |

## Legacy limitations of the input manifests (reported, not filled in)

- squad2: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- covidqa: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- cuad: manifest config has no 'study' field (historical Study 1 format); treated as '1'
- qasper: manifest config has no 'study' field (historical Study 1 format); treated as '1'

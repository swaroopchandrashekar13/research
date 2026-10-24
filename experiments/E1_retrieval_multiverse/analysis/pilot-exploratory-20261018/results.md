# Study 1 results — EXPLORATORY

Datasets: squad2, covidqa, cuad, qasper; queries: squad2 1184, covidqa 248, cuad 248, qasper 460

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H1 | 70.5% | [61.3%, 81.5%] | 20.0% | supported |
| H1b | 29.6% | [15.1%, 35.8%] | 10.0% | supported |
| H2 | dataset η² largest in 98.7% of replicates | — | 95% | supported |
| H3 | 84.9% of universes need n > 500 (median n = 1323) | — | > 50% | supported |

H2 point estimates (η²): dataset 0.581, retriever 0.006, budget 0.078, metric 0.038

## H1 sensitivity analyses (P1: share supporting fixed-512, count − budget)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 72.4% | — |
| b_without_squad2 | 62.4% | [51.0%, 76.3%] |
| c_default_retriever | 66.7% | [54.1%, 79.2%] |
| d_cluster_bootstrap | 71.1% | [62.3%, 81.0%] |
| e_all_budgets | 72.7% | [63.4%, 81.2%] |

## Verdict shares per claim and protocol

| Claim | Role | A vs B | Protocol | Universes | Supports A | Supports B | Inconclusive |
|---|---|---|---|---:|---:|---:|---:|
| P1 | primary | fixed-128 vs fixed-512 | count | 768 | 0.0% | 76.0% | 24.0% |
| P1 | primary | fixed-128 vs fixed-512 | budget | 576 | 64.8% | 5.6% | 29.7% |
| S1-64 | secondary | fixed-64 vs fixed-128 | count | 768 | 0.0% | 79.2% | 20.8% |
| S1-64 | secondary | fixed-64 vs fixed-128 | budget | 960 | 9.2% | 27.2% | 63.6% |
| S1-128 | secondary | fixed-128 vs fixed-256 | count | 768 | 0.0% | 57.8% | 42.2% |
| S1-128 | secondary | fixed-128 vs fixed-256 | budget | 768 | 34.2% | 0.5% | 65.2% |
| S1-256 | secondary | fixed-256 vs fixed-512 | count | 768 | 0.0% | 55.5% | 44.5% |
| S1-256 | secondary | fixed-256 vs fixed-512 | budget | 576 | 40.1% | 2.8% | 57.1% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | count | 768 | 49.2% | 1.0% | 49.7% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | budget | 960 | 49.0% | 0.0% | 51.0% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | count | 768 | 36.5% | 0.8% | 62.8% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | budget | 960 | 39.0% | 0.4% | 60.6% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | count | 768 | 20.1% | 1.0% | 78.9% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | budget | 768 | 18.9% | 3.4% | 77.7% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | count | 768 | 6.2% | 6.2% | 87.5% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | budget | 576 | 7.8% | 0.0% | 92.2% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | count | 768 | 55.1% | 0.9% | 44.0% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | budget | 960 | 64.4% | 0.0% | 35.6% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | count | 768 | 50.9% | 3.4% | 45.7% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | budget | 960 | 60.3% | 0.0% | 39.7% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | count | 768 | 29.6% | 0.3% | 70.2% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | budget | 768 | 59.1% | 0.0% | 40.9% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | count | 768 | 11.2% | 3.4% | 85.4% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | budget | 576 | 33.7% | 0.2% | 66.1% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | count | 768 | 50.0% | 4.7% | 45.3% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | budget | 960 | 56.2% | 2.3% | 41.5% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | count | 768 | 42.2% | 3.6% | 54.2% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | budget | 960 | 52.0% | 0.4% | 47.6% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | count | 768 | 14.1% | 1.8% | 84.1% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | budget | 768 | 26.2% | 0.3% | 73.6% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | count | 768 | 3.4% | 2.6% | 94.0% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | budget | 576 | 8.3% | 0.0% | 91.7% |

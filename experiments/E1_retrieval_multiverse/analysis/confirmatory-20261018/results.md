# Study 1 results — CONFIRMATORY

Datasets: squad2, covidqa, cuad, qasper; queries: squad2 4744, covidqa 1771, cuad 996, qasper 1742

## Hypotheses

| ID | Estimate | 95% CI | Threshold | Verdict |
|---|---:|---|---:|---|
| H1 | 71.1% | [64.8%, 81.9%] | 20.0% | supported |
| H1b | 26.7% | [15.4%, 33.9%] | 10.0% | supported |
| H2 | dataset η² largest in 100.0% of replicates | — | 95% | supported |
| H3 | 85.4% of universes need n > 500 (median n = 1256) | — | > 50% | supported |

H2 point estimates (η²): dataset 0.614, retriever 0.044, budget 0.096, metric 0.032

## H1 sensitivity analyses (P1: share supporting fixed-512, count − budget)

| Analysis | Estimate | 95% CI |
|---|---:|---|
| a_bh_fdr | 68.0% | — |
| b_without_squad2 | 61.5% | [53.2%, 74.8%] |
| c_default_retriever | 70.8% | [64.6%, 85.4%] |
| d_cluster_bootstrap | 69.7% | [63.8%, 82.0%] |
| e_all_budgets | 74.2% | [68.3%, 84.8%] |

## Verdict shares per claim and protocol

| Claim | Role | A vs B | Protocol | Universes | Supports A | Supports B | Inconclusive |
|---|---|---|---|---:|---:|---:|---:|
| P1 | primary | fixed-128 vs fixed-512 | count | 768 | 0.0% | 78.8% | 21.2% |
| P1 | primary | fixed-128 vs fixed-512 | budget | 576 | 81.2% | 7.6% | 11.1% |
| S1-64 | secondary | fixed-64 vs fixed-128 | count | 768 | 0.0% | 84.1% | 15.9% |
| S1-64 | secondary | fixed-64 vs fixed-128 | budget | 960 | 20.0% | 42.1% | 37.9% |
| S1-128 | secondary | fixed-128 vs fixed-256 | count | 768 | 0.0% | 74.1% | 25.9% |
| S1-128 | secondary | fixed-128 vs fixed-256 | budget | 768 | 60.5% | 6.2% | 33.2% |
| S1-256 | secondary | fixed-256 vs fixed-512 | count | 768 | 0.0% | 63.3% | 36.7% |
| S1-256 | secondary | fixed-256 vs fixed-512 | budget | 576 | 78.0% | 2.1% | 20.0% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | count | 768 | 52.5% | 1.7% | 45.8% |
| S2-64 | secondary | fixed-64-o25 vs fixed-64 | budget | 960 | 54.8% | 1.8% | 43.4% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | count | 768 | 51.6% | 1.8% | 46.6% |
| S2-128 | secondary | fixed-128-o25 vs fixed-128 | budget | 960 | 55.1% | 1.9% | 43.0% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | count | 768 | 36.1% | 3.5% | 60.4% |
| S2-256 | secondary | fixed-256-o25 vs fixed-256 | budget | 768 | 39.8% | 3.3% | 56.9% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | count | 768 | 9.5% | 9.0% | 81.5% |
| S2-512 | secondary | fixed-512-o25 vs fixed-512 | budget | 576 | 11.8% | 6.8% | 81.4% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | count | 768 | 62.2% | 5.7% | 32.0% |
| S3-64 | secondary | paragraph-64 vs fixed-64 | budget | 960 | 75.5% | 0.0% | 24.5% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | count | 768 | 59.8% | 1.2% | 39.1% |
| S3-128 | secondary | paragraph-128 vs fixed-128 | budget | 960 | 79.7% | 0.0% | 20.3% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | count | 768 | 50.1% | 2.5% | 47.4% |
| S3-256 | secondary | paragraph-256 vs fixed-256 | budget | 768 | 76.8% | 0.5% | 22.7% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | count | 768 | 13.7% | 1.7% | 84.6% |
| S3-512 | secondary | paragraph-512 vs fixed-512 | budget | 576 | 60.9% | 1.7% | 37.3% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | count | 768 | 58.9% | 6.1% | 35.0% |
| S4-64 | exploratory | sentence-64 vs fixed-64 | budget | 960 | 69.5% | 0.4% | 30.1% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | count | 768 | 50.1% | 0.8% | 49.1% |
| S4-128 | exploratory | sentence-128 vs fixed-128 | budget | 960 | 57.6% | 0.0% | 42.4% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | count | 768 | 19.0% | 1.6% | 79.4% |
| S4-256 | exploratory | sentence-256 vs fixed-256 | budget | 768 | 38.5% | 0.0% | 61.5% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | count | 768 | 6.1% | 0.5% | 93.4% |
| S4-512 | exploratory | sentence-512 vs fixed-512 | budget | 576 | 20.8% | 0.3% | 78.8% |

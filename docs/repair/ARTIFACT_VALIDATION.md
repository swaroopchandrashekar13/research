# Stored-artefact validation

Generated 2026-10-24T19:13:45Z by `python -I tools/validate_artifacts.py --data-root <verified datasets>` (exit 0). Without `--data-root` the data-dependent rows are not run.

| Status | Check | Detail |
|---|---|---|
| PASS | E1 pilot: run validation (EXPLORATORY) | 4 datasets, 64 NPZ files; legacy: 4 note(s) |
| NOTE | E1 pilot: legacy limitation | covidqa: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 pilot: legacy limitation | cuad: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 pilot: legacy limitation | qasper: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 pilot: legacy limitation | squad2: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| PASS | E1 confirmatory: run validation (CONFIRMATORY) | 4 datasets, 64 NPZ files; legacy: 4 note(s) |
| NOTE | E1 confirmatory: legacy limitation | covidqa: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 confirmatory: legacy limitation | cuad: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 confirmatory: legacy limitation | qasper: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| NOTE | E1 confirmatory: legacy limitation | squad2: manifest config has no 'study' field (historical Study 1 format); treated as '1' |
| PASS | E3 pilot: run validation (EXPLORATORY) | 4 datasets, 20 NPZ files; legacy: 4 note(s) |
| NOTE | E3 pilot: legacy limitation | covidqa: manifest has no 'error' field |
| NOTE | E3 pilot: legacy limitation | cuad: manifest has no 'error' field |
| NOTE | E3 pilot: legacy limitation | qasper: manifest has no 'error' field |
| NOTE | E3 pilot: legacy limitation | squad2: manifest has no 'error' field |
| PASS | E3 pilot: squad2/chunks_semantic-bp.json.gz | 521 chunks (manifest 521); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: squad2/chunks_semantic-cl.json.gz | 334 chunks (manifest 334); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: covidqa/chunks_semantic-bp.json.gz | 2060 chunks (manifest 2060); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: covidqa/chunks_semantic-cl.json.gz | 1299 chunks (manifest 1299); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: cuad/chunks_semantic-bp.json.gz | 2274 chunks (manifest 2274); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: cuad/chunks_semantic-cl.json.gz | 1588 chunks (manifest 1588); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: qasper/chunks_semantic-bp.json.gz | 8628 chunks (manifest 8628); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 pilot: qasper/chunks_semantic-cl.json.gz | 5313 chunks (manifest 5313); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: run validation (CONFIRMATORY) | 4 datasets, 20 NPZ files; legacy: 4 note(s) |
| NOTE | E3 confirmatory: legacy limitation | covidqa: manifest has no 'error' field |
| NOTE | E3 confirmatory: legacy limitation | cuad: manifest has no 'error' field |
| NOTE | E3 confirmatory: legacy limitation | qasper: manifest has no 'error' field |
| NOTE | E3 confirmatory: legacy limitation | squad2: manifest has no 'error' field |
| PASS | E3 confirmatory: squad2/chunks_semantic-bp.json.gz | 521 chunks (manifest 521); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: squad2/chunks_semantic-cl.json.gz | 334 chunks (manifest 334); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: covidqa/chunks_semantic-bp.json.gz | 2060 chunks (manifest 2060); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: covidqa/chunks_semantic-cl.json.gz | 1299 chunks (manifest 1299); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: cuad/chunks_semantic-bp.json.gz | 2274 chunks (manifest 2274); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: cuad/chunks_semantic-cl.json.gz | 1588 chunks (manifest 1588); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: qasper/chunks_semantic-bp.json.gz | 8628 chunks (manifest 8628); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | E3 confirmatory: qasper/chunks_semantic-cl.json.gz | 5313 chunks (manifest 5313); 0 invalid chunks; 0 gaps/overlaps in the per-document word partition |
| PASS | query lists identical: E1 confirmatory vs E3 confirmatory | qids and doc_idx, all datasets |
| PASS | query lists identical: E1 pilot vs E3 pilot | qids and doc_idx, all datasets |
| PASS | no cross-split leakage: squad2 | 1184 exploratory / 4744 confirmatory queries; documents disjoint |
| PASS | no cross-split leakage: covidqa | 248 exploratory / 1771 confirmatory queries; documents disjoint |
| PASS | no cross-split leakage: cuad | 248 exploratory / 996 confirmatory queries; documents disjoint |
| PASS | no cross-split leakage: qasper | 460 exploratory / 1742 confirmatory queries; documents disjoint |
| PASS | E2 gemini36flash-20261019/squad2: generations log | 13 lines, 13 ok, 13 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 gemini36flash-20261019/covidqa: generations log | 2 lines, 2 ok, 2 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 gemini36flash-20261019/cuad: generations log | 6 lines, 6 ok, 6 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 gemini36flash-20261019/qasper: generations log | 0 lines, 0 ok, 0 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 qwen3-4b-20261019/squad2: generations log | 198 lines, 198 ok, 198 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 qwen3-4b-kaggle-gpu/squad2: generations log | 400 lines, 400 ok, 400 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 qwen3-4b-kaggle-gpu/covidqa: generations log | 400 lines, 400 ok, 400 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 qwen3-4b-kaggle-gpu/cuad: generations log | 400 lines, 400 ok, 400 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | E2 qwen3-4b-kaggle-gpu/qasper: generations log | 400 lines, 400 ok, 400 accepted, 0 superseded, 0 duplicate ok; sample of 50 confirmatory queries: yes |
| PASS | experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/UPLOAD_SHA256 | one SHA-256 of an upload archive that is not in the repository (cannot be re-verified here) |
| PASS | experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/UPLOAD_SHA256 | one SHA-256 of an upload archive that is not in the repository (cannot be re-verified here) |
| PASS | experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/UPLOAD_SHA256 | one SHA-256 of an upload archive that is not in the repository (cannot be re-verified here) |
| PASS | experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/build_gpu.log.gz: gzip | 995 lines |
| PASS | experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json: parses | label: CONFIRMATORY |
| PASS | experiments/E1_retrieval_multiverse/analysis/pilot-exploratory-20261018/results.json: parses | label: EXPLORATORY |
| PASS | experiments/E2_generation/analysis/qwen3-4b-kaggle-gpu/results.json: parses | label: EXPLORATORY (Tier 2; pre-specified plan, not part of the fro |
| PASS | experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu/results.json: parses | label: CONFIRMATORY |
| PASS | experiments/E3_semantic_dense/analysis/exploratory-kaggle-gpu/results.json: parses | label: EXPLORATORY |
| NOTE | experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/covidqa.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/cuad.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/qasper.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/squad2.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/covidqa.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/cuad.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/qasper.log | 1 line(s) |
| NOTE | experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/squad2.log | 1 line(s) |
| NOTE | experiments/E2_generation/runs/gemini36flash-20261019/covidqa.log | 0 line(s) |
| NOTE | experiments/E2_generation/runs/gemini36flash-20261019/cuad.log | 0 line(s) |
| NOTE | experiments/E2_generation/runs/gemini36flash-20261019/qasper.log | 0 line(s) |
| NOTE | experiments/E2_generation/runs/gemini36flash-20261019/squad2.log | 0 line(s) |
| NOTE | experiments/E2_generation/runs/qwen3-4b-20261019/squad2.log | 0 line(s) |
| PASS | protected files match docs/repair/PROTECTED_SHA256.txt | 284 files; mismatches: [] |
| PASS | data: squad2 input digests | every file the loader reads matches data/MANIFEST.yaml |
| PASS | data: squad2 unique query IDs | 5928 queries, 35 documents |
| PASS | data: squad2 counts match manifests | documents 35, exploratory docs 7, confirmatory queries 4744 |
| PASS | data: squad2 deterministic split reproduces E1 pilot query list | 1184 queries |
| PASS | data: squad2 deterministic split reproduces E1 confirmatory query list | 4744 queries |
| PASS | data: squad2 gold spans inside documents | 10119 word spans |
| PASS | data: E3 pilot squad2 semantic-bp covers every word of every document | 35 documents |
| PASS | data: E3 pilot squad2 semantic-cl covers every word of every document | 35 documents |
| PASS | data: E3 confirmatory squad2 semantic-bp covers every word of every document | 35 documents |
| PASS | data: E3 confirmatory squad2 semantic-cl covers every word of every document | 35 documents |
| PASS | data: covidqa input digests | every file the loader reads matches data/MANIFEST.yaml |
| PASS | data: covidqa unique query IDs | 2019 queries, 147 documents |
| PASS | data: covidqa counts match manifests | documents 147, exploratory docs 29, confirmatory queries 1771 |
| PASS | data: covidqa deterministic split reproduces E1 pilot query list | 248 queries |
| PASS | data: covidqa deterministic split reproduces E1 confirmatory query list | 1771 queries |
| PASS | data: covidqa gold spans inside documents | 2019 word spans |
| PASS | data: E3 pilot covidqa semantic-bp covers every word of every document | 147 documents |
| PASS | data: E3 pilot covidqa semantic-cl covers every word of every document | 147 documents |
| PASS | data: E3 confirmatory covidqa semantic-bp covers every word of every document | 147 documents |
| PASS | data: E3 confirmatory covidqa semantic-cl covers every word of every document | 147 documents |
| PASS | data: cuad input digests | every file the loader reads matches data/MANIFEST.yaml |
| PASS | data: cuad unique query IDs | 1244 queries, 102 documents |
| PASS | data: cuad counts match manifests | documents 102, exploratory docs 20, confirmatory queries 996 |
| PASS | data: cuad deterministic split reproduces E1 pilot query list | 248 queries |
| PASS | data: cuad deterministic split reproduces E1 confirmatory query list | 996 queries |
| PASS | data: cuad gold spans inside documents | 2641 word spans |
| PASS | data: E3 pilot cuad semantic-bp covers every word of every document | 102 documents |
| PASS | data: E3 pilot cuad semantic-cl covers every word of every document | 102 documents |
| PASS | data: E3 confirmatory cuad semantic-bp covers every word of every document | 102 documents |
| PASS | data: E3 confirmatory cuad semantic-cl covers every word of every document | 102 documents |
| PASS | data: qasper input digests | every file the loader reads matches data/MANIFEST.yaml |
| PASS | data: qasper unique query IDs | 2202 queries, 697 documents |
| PASS | data: qasper counts match manifests | documents 697, exploratory docs 139, confirmatory queries 1742 |
| PASS | data: qasper deterministic split reproduces E1 pilot query list | 460 queries |
| PASS | data: qasper deterministic split reproduces E1 confirmatory query list | 1742 queries |
| PASS | data: qasper gold spans inside documents | 5286 word spans |
| PASS | data: E3 pilot qasper semantic-bp covers every word of every document | 697 documents |
| PASS | data: E3 pilot qasper semantic-cl covers every word of every document | 697 documents |
| PASS | data: E3 confirmatory qasper semantic-bp covers every word of every document | 697 documents |
| PASS | data: E3 confirmatory qasper semantic-cl covers every word of every document | 697 documents |
| PASS | data: E2 qwen3-4b-kaggle-gpu/squad2 rebuilt from data | 400 rows; sample equals jobs_meta: True; mismatches {'prompt': 0, 'retrieval_vs_E1': 0, 'retrieval_vs_rebuilt': 0, 'em': 0, 'f1': 0, 'answers': 0} |
| PASS | data: E2 qwen3-4b-kaggle-gpu/covidqa rebuilt from data | 400 rows; sample equals jobs_meta: True; mismatches {'prompt': 0, 'retrieval_vs_E1': 0, 'retrieval_vs_rebuilt': 0, 'em': 0, 'f1': 0, 'answers': 0} |
| PASS | data: E2 qwen3-4b-kaggle-gpu/cuad rebuilt from data | 400 rows; sample equals jobs_meta: True; mismatches {'prompt': 0, 'retrieval_vs_E1': 0, 'retrieval_vs_rebuilt': 0, 'em': 0, 'f1': 0, 'answers': 0} |
| PASS | data: E2 qwen3-4b-kaggle-gpu/qasper rebuilt from data | 400 rows; sample equals jobs_meta: True; mismatches {'prompt': 0, 'retrieval_vs_E1': 0, 'retrieval_vs_rebuilt': 0, 'em': 0, 'f1': 0, 'answers': 0} |

89 passed, 0 failed, 29 notes.

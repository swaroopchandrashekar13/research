# HASH-001 — inventory and redaction of unresolvable historical Git references

*Written 2026-10-24 on branch `swaroop-fix`. The researcher reported that the project's original Git repository is
no longer available and asked for unresolvable historical commit references to be removed from active material and
from historical metadata. History was **not** rewritten; this file records what was changed and why. It deliberately
contains **no** commit identifiers.*

## 1. Scan scope and method
- **Scope:** every file tracked on this branch (365 files at the baseline), including the decompressed contents of all
  `.gz` members (`build_gpu.log.gz`, 32 `chunks_semantic-*.json.gz`). Binary `.npz`, `.png` and `.pdf` files were
  excluded from the text scan; `.npz` members are numeric arrays (validated in `docs/repair/ARTIFACT_VALIDATION.md`).
- **Pattern:** any token of 7–64 lowercase hexadecimal characters containing at least one digit and one letter,
  bounded by non-alphanumerics. Every distinct token was classified by its context (field name, file, surrounding
  text). Tool used for the scan: a throw-away script (equivalent: `git grep -nE '[0-9a-f]{7,64}'`); the redaction
  itself is reproducible with `python -I tools/redact_git_refs.py --check`.
- **Local objects:** the eight project commit identifiers found were looked up with `git cat-file -t`; none exists in
  the local object database (the clone holds a single commit). No bundles, mirrors or backups exist in the workspace,
  so there was nothing to remove or recover. Absence from the local clone alone does not prove an identifier was
  invalid; it is the researcher's statement that the original repository is gone that makes them unresolvable.

## 2. Classification (baseline counts)
| Class | Where | Count (distinct) | Action |
|---|---|---:|---|
| **Project Git commits (unresolvable)** | `"git"` fields of 16 run manifests, 9 `jobs_meta.json`, 4 `results.json` (`source_manifests`); prose in 2 pilot memos, 3 results summaries, the Zenodo guide and the Study 1b pre-registration | 8 | **Removed** (§3) |
| Project commit *pointer without identifier* | Study 1b pre-registration ("the commit that introduces this line") | 1 | **Removed** (replaced by a bracketed note) |
| Hugging Face model revisions | `src/ragmv/dense.py`, `src/ragmv/generate.py`, `jobs_meta.json`, `generations.jsonl` `model_version`, manifests' `encoder`, docs | 3 | Kept (model identity) |
| Model-file SHA-256 | `generate.py`, `jobs_meta.json`, manuscript | 2 | Kept (content digest) |
| Dataset archive SHA-256 | `data/MANIFEST.yaml` | 5 | Kept; re-verified 2026-10-24 against fresh downloads |
| Configuration SHA-256 (`config_sha256`) | manifests, `results.json` | 16 | Kept (run identity) |
| Prompt SHA-256 (`prompt_sha256`) | `generations.jsonl` | 1,368 | Kept (content digest) |
| Upload-archive SHA-256 | three `UPLOAD_SHA256` files | 3 | Kept (content digest of an archive not in the repository) |
| Dataset question IDs | `queries.json`, `jobs_meta.json`, `generations.jsonl` | 5,928 SQuAD (24 hex) + 2,202 Qasper (40 hex) | Kept. Qasper IDs have the same shape as SHA-1 commit IDs; they are dataset identifiers |
| Third-party build provenance | `build_gpu.log.gz`: vendored ggml commit of llama.cpp, pip temporary directory names, PyPI file paths | many | Kept (third-party software identity, not this project's history; immutable build log) |
| Publisher URL path components | NeurIPS proceedings URLs in `bibliography.yaml`, `refs.bib` | 2 | Kept |
| Ordinary hexadecimal/other text | float mantissa fragments in `results.json`, the word `ed25519` in `.gitignore` | 5 | Not identifiers |

## 3. Files changed by the redaction
JSON files: only the value of each `"git"` field was replaced by `redacted: unresolvable historical Git commit`
(plus ` (working tree was dirty)` where the original value carried the `-dirty` suffix); the edit is textual, so all
other bytes are identical (verified: the `git diff` of each JSON file is exactly one changed line per redacted field,
41 lines in 29 files, and every file still parses). Markdown files: the sentences citing the identifiers were
rewritten and a dated provenance note was added. The pre-registration was changed only at the two places listed in §2;
its section-number errors are handled by an erratum without touching its bytes
(`research/ERRATA_preregistrations.md`).

| File | Change | SHA-256 before | SHA-256 after |
|---|---|---|---|
| `docs/guides/ZENODO.md` | commit identifier sentence(s) rewritten / annotated | `3b85e637a51c1c6549e583272fe0da69c9bec12fa0b7ac7190fc8e5de021d715` | `4a3124e378f1e217976521dcf90a886e876dbaab8ff2d640fc621f7f633a9df7` |
| `experiments/E1_retrieval_multiverse/PILOT_MEMO.md` | commit identifier sentence(s) rewritten / annotated | `5a896f1f13ceede54d58df069feec33c488fec92dc42086721271e3d47ec8e81` | `2920c58b200b9603d0810e53c6e9408b3ca098151a20aad1843962efb299bf22` |
| `experiments/E1_retrieval_multiverse/RESULTS.md` | commit identifier sentence(s) rewritten / annotated | `111ca071ac730596af08e05083de1bef990ce608fc18edd1b4705c99aa3b1d70` | `35dd5bc09e0a8fab0dd25f58e632c8a8bf12aa469cfb66520057e61d359db457` |
| `experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json` | `git` field value(s) replaced by marker | `27ae2708e8dcdf812d325d8a5d462455f58edfb8563fa3068aa73a5338721073` | `3055aef921ffcd34f962f7067d4bf29eb233d253b15fd4467187c53b3f062fd6` |
| `experiments/E1_retrieval_multiverse/analysis/pilot-exploratory-20261018/results.json` | `git` field value(s) replaced by marker | `370684ad34086a43ef84ac4d53d571cc98db1f81f68934358938d58df4709ba5` | `8d30163c863d071ba73e284f3e23f212f32256dd9babfd655c8f2077443c6081` |
| `experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/covidqa/manifest.json` | `git` field value(s) replaced by marker | `35d5d43665bf5e3c00daefa8e249038e56f8ed11435808e10641bb3b26aeb292` | `c3219946084f26f061f215b1da80fb2ddaa49aff615e489b23363cea9126b131` |
| `experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/cuad/manifest.json` | `git` field value(s) replaced by marker | `186a359b1accafdc8a1e31ce0594eddc84b77ac73d495089694e1fd29e0cce90` | `181268e5c8cba22ec4fa1b3196adbe83a427d4610a632ae94a910012c333e38e` |
| `experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/qasper/manifest.json` | `git` field value(s) replaced by marker | `a09b7bbcc4227e54a4bc7a89b61ed66b9deb8e164920b19401ed32c5da11645a` | `88d8bf286b077dab6ae54f5c89f06bd61dabce22221ddcb9651f88f1fe84a4b1` |
| `experiments/E1_retrieval_multiverse/runs/confirmatory-20261018/squad2/manifest.json` | `git` field value(s) replaced by marker | `c164dc6709585fd5ebf1ad2e25aaa07f8d9bfd2141fe06a42fb6be06f96f2193` | `8223ed71df816b4c71c98690234407c0813954c9de7a9c39011b0ba198a3cfd6` |
| `experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/covidqa/manifest.json` | `git` field value(s) replaced by marker | `b3fc37af1abd223453aa61f09cc8887ad47945deedbcf52b30312694ebae246b` | `d7807029d659433d01d264fbab000f050d590cf9961a8323a0b279320da07484` |
| `experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/cuad/manifest.json` | `git` field value(s) replaced by marker | `7c692cd6c9ba39981f5f1c15bf8fe8290ca76c3c7ee794e884bd9d5243d54076` | `193b59a5a3e7bf39352e25e054ef3cfaad6ee3e087ed0fa7c44c3a79774cca04` |
| `experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/qasper/manifest.json` | `git` field value(s) replaced by marker | `b7255481ef1897a2f805bd0702d9b907bde785d8b15aaf2f62be4881e1d45651` | `9185269e5e7ad5d5ab54c1547f01bee2271207a0159b65a1f55e4329cf6cad2f` |
| `experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018/squad2/manifest.json` | `git` field value(s) replaced by marker | `96c8595bd235233992a4a7b931a7c842d2a34263ad9d5903f79425ccf6bfb3ae` | `bc6839108571ad50fcfd9e51989dcab34e11be20076f6d558457af13e04e8573` |
| `experiments/E2_generation/RESULTS.md` | commit identifier sentence(s) rewritten / annotated | `24eb5d10c73fae2c66196ca94115035cb0a0fd812302201caa21d1f4d96daad9` | `f52c63acfe50502ebdbb73d449ee21e3f0628d5d14180aae6a29527e3ff3ba0e` |
| `experiments/E2_generation/runs/gemini36flash-20261019/covidqa/jobs_meta.json` | `git` field value(s) replaced by marker | `ff87a29f13a856caaef5eb537bcdc977ee6b5c96aa54118fefec1ddbf296c963` | `d6c62384ff2721832361e7ba9d0ff9d6ad3716ad84500330b0260916cc6078f5` |
| `experiments/E2_generation/runs/gemini36flash-20261019/cuad/jobs_meta.json` | `git` field value(s) replaced by marker | `8b5905e98d1fdaa23e9f8f63d8be981598dd3941a45971d1561da0e5c2041c1b` | `fef83a659f419b190e5998dfbb8f1a2a64e6a1719088e816b8c2110fb9327f59` |
| `experiments/E2_generation/runs/gemini36flash-20261019/qasper/jobs_meta.json` | `git` field value(s) replaced by marker | `b13002edc7c147eaaf7fe846f97a1c90151d36f9ad54a7e8411fad61d6ee5913` | `26eb61fddbbb44e7396bd2a2497b9ef02f785a1b13e1e97f6a843d9fdd26d626` |
| `experiments/E2_generation/runs/gemini36flash-20261019/squad2/jobs_meta.json` | `git` field value(s) replaced by marker | `9c1bf17be1ebe56199ccf9ee7d76ff35bd50b96dcd4aa759c0d6dedf35fae51b` | `953196e3e7eeeca4eac3e5488d682d0f369da542bf31451bf4c0ed3687a12097` |
| `experiments/E2_generation/runs/qwen3-4b-20261019/squad2/jobs_meta.json` | `git` field value(s) replaced by marker | `a6653a8fdfbb6dc29b6f55b5b59f226d6d7dba7d8e5d5e5d8b5baf6a3f368fe0` | `40aeaa081bd0f10170bd65b8b0022dd3776268f88329b515cb09f752face5c60` |
| `experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/covidqa/jobs_meta.json` | `git` field value(s) replaced by marker | `2ff04cf4043c43ed0a334778e0e5de05bf1a8ff5a65ce580fffc64952a6a50d4` | `01acf27d01458dd1af6f1f057a41615ba6264ec3c76e1b071f8d157fc0e9cbd9` |
| `experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/cuad/jobs_meta.json` | `git` field value(s) replaced by marker | `a9d061407fd02d7b894b5451bdc82d64aef8e2a134e7c8700133452bac9919f6` | `667d08f1b8b1192170efbac972619ed4cc59435889ba75f3124e5dc267b2e66b` |
| `experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/qasper/jobs_meta.json` | `git` field value(s) replaced by marker | `6d7d37bd4481967555963de66c760fda5d43eb7f1ba7b5ed8a261c39bb928882` | `ccf0274408bd030e57e4ab87f0b423607f42631bf92975ab5c612d778624ba56` |
| `experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/squad2/jobs_meta.json` | `git` field value(s) replaced by marker | `b7c235b82a100bb348c6d95827dce688093f7721739fa2fcb4a7f000ee510e91` | `4563e6af1cb60e952d422925415813deac360992d932cbba20a9b741251094a9` |
| `experiments/E3_semantic_dense/PILOT_MEMO.md` | commit identifier sentence(s) rewritten / annotated | `707d339f101e1d228be715aa242602d6faa57797a32fc8a50449a388f47dee56` | `950cea0bd4fc357f59571383253a73becd8eea9aae52dde4d8bfb414b72aac86` |
| `experiments/E3_semantic_dense/RESULTS.md` | commit identifier sentence(s) rewritten / annotated | `a8d19f26ab0cea797cc3c3a921c2cdb8500c1c12b3bc9a06a9d28bc244fdfa81` | `3ac9af1fd8dd968f2409438ba7ac8e02f550eaf37da787e794ec8a387d9425aa` |
| `experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu/results.json` | `git` field value(s) replaced by marker | `0b242064360d11773f88b748f744d8c04221bb5d40a8ff8ea40933b221ac427c` | `0ec923c0b55695273ee2ae71af1c47e877a836ec71984ca10313e69606d61412` |
| `experiments/E3_semantic_dense/analysis/exploratory-kaggle-gpu/results.json` | `git` field value(s) replaced by marker | `71decc0b8551912166d94d9b197ea91283d8edab4c4a73a58d19f1550fa2882b` | `fbad5e3f8f03475885dbda9acca533702e40d382581b58f04a63cb8c07506ab8` |
| `experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/covidqa/manifest.json` | `git` field value(s) replaced by marker | `0ecce0c59b1022da78215a14846d9eda9eb0347aa6e1ae1ded5725ba4ac7bd68` | `07d147a63e4cc7a41bed40c76f9e6cc694e4484c49cde8aa91ce8dd4cf6952c5` |
| `experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/cuad/manifest.json` | `git` field value(s) replaced by marker | `9af76a8413a112613cb5f364bf81d3c87ee3450566f07c3710199b716301264d` | `dd2f45d36113478a1a1270b47684465e162cf2150e5c43f92f35ac90d4f42815` |
| `experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/qasper/manifest.json` | `git` field value(s) replaced by marker | `143d56458a370baf092635e1adc363f55e164d6307d8409fc680836213b7dfbb` | `2d915bef2e4067dedda46ac2eeca1f527e94fd70a93b1622b037904e70fdb174` |
| `experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/squad2/manifest.json` | `git` field value(s) replaced by marker | `82c52c4901f4e2634ab08716cadb719b1f02312d2cc8aaecf76b956cbae313fa` | `d70ff59a8b27a7f282976f74273eee2faf45b3e25cd33b236a20e6fcb27d7629` |
| `experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/covidqa/manifest.json` | `git` field value(s) replaced by marker | `bb9989c4b0db19303685636e7baf17c5fa7bfab6bbbdfaad0de81d8322166137` | `f7cb4c9052038424a31e4c4b21e4439c2fd0f5eda5edbfc5915809f405c1cc4a` |
| `experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/cuad/manifest.json` | `git` field value(s) replaced by marker | `e199138dd65d5c5056f4495be0d0de3944fc5ef408dc61b6ada55260de27b103` | `cb232bb95fca5f60c7e84c79d93585d59c2e881c9abd4eb17b5c4970a00a768e` |
| `experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/qasper/manifest.json` | `git` field value(s) replaced by marker | `6b0a3103fc7aedeed0cd7877e4f8ac9c19544411a724ab6a942606fd6c78f2ab` | `742bcba72aab884dca0261440ef7016496619f01c53f306e7982aa999a9f5ba2` |
| `experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/squad2/manifest.json` | `git` field value(s) replaced by marker | `9704db6e922979c6a571c6d06d09bf372b6f4e9090863fe7661acd5f74c6a3cd` | `d56ee61e3f0c08f48e0ab91e7904cd946c483ce5adb8fd57c105b056bf85f17f` |
| `research/preregistration_study1b.md` | commit identifier sentence(s) rewritten / annotated | `8a1115e43b59ee816c876a841ee8d3123195b5602e158478159a0d348be00ece` | `ac70c5d1d08e15552dd18ada0338a438e78b3b36f25482ee1bee5c19a3b9bd04` |

The *before* digests let anyone holding a copy of the original files confirm that these are the same files; the
original bytes also remain in this repository's own history (no history was rewritten).

## 4. New work
New runs, analyses and reports record a **code-content digest** (`ragmv.integrity.source_digest`: SHA-256 over the
sorted relative paths and bytes of `src/ragmv/*.py`) and, for uncommitted trees, a patch digest, instead of Git
commit identifiers. `run.py`, `run1b.py` and `generate.py` no longer call `git`.

## 5. Final scan (to repeat before any release)
```
python -I tools/redact_git_refs.py --check          # 0 commit-valued "git" fields
python -I tools/scan_hex_refs.py                      # lists every remaining hex token by class; fails on an unclassified commit-like token in active material
```

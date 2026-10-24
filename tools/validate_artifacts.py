"""Validate every stored research artefact without modifying it.

Offline checks (always): run manifests, configuration fingerprints, query lists, NPZ arrays (no pickle), semantic
chunk files, generation logs (strict JSONL), jobs metadata, gzip members, upload digests, analysis results, query
consistency across studies and absence of cross-split leakage, and (if present) the protected-file digest list.
With --data-root (datasets verified against data/MANIFEST.yaml): document/query counts, deterministic splits,
duplicate IDs, gold spans, exact partition of every document by the stored semantic chunks, and Tier 2 prompts,
retrieval values and EM/F1 rebuilt from the data and compared with every stored row.

Usage: python -I tools/validate_artifacts.py [--data-root DIR] [--report FILE]   (exit 1 if any check fails)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from ragmv import analyze as A  # noqa: E402
from ragmv import analyze1b as A1b  # noqa: E402
from ragmv import generate as G  # noqa: E402

DATASETS = ("squad2", "covidqa", "cuad", "qasper")
RUNS = {
    "E1 pilot": ("experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018", "1", "EXPLORATORY"),
    "E1 confirmatory": ("experiments/E1_retrieval_multiverse/runs/confirmatory-20261018", "1", "CONFIRMATORY"),
    "E3 pilot": ("experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu", "1b", "EXPLORATORY"),
    "E3 confirmatory": ("experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu", "1b", "CONFIRMATORY"),
}
E2_RUNS = "experiments/E2_generation/runs"
ANALYSED_E2 = "qwen3-4b-kaggle-gpu"


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append(("PASS" if ok else "FAIL", name, detail))
        return ok

    def note(self, name: str, detail: str) -> None:
        self.rows.append(("NOTE", name, detail))

    @property
    def failed(self) -> int:
        return sum(r[0] == "FAIL" for r in self.rows)

    def markdown(self) -> str:
        lines = ["| Status | Check | Detail |", "|---|---|---|"]
        lines += [f"| {s} | {n} | {d.replace('|', '/')} |" for s, n, d in self.rows]
        counts = {k: sum(r[0] == k for r in self.rows) for k in ("PASS", "FAIL", "NOTE")}
        return "\n".join(lines) + f"\n\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['NOTE']} notes.\n"


def check_runs(rep: Report) -> dict:
    qsets = {}
    for name, (rel, study, label) in RUNS.items():
        path = ROOT / rel
        try:
            run = A.Run(path, study=study)
            if study == "1":
                run.validate(label, sorted({x for c in A.preregistered_claims() for x in (c.a, c.b)}),
                                 A.full_design_study1())
                for d in run.datasets:  # every stored chunking, not only those the claims use
                    for c in run.meta[d]["manifest"]["config"]["chunkings"]:
                        run.scores(d, c)
            else:
                run.validate(label, list(A1b.CHUNKINGS), {"chunkings": list(A1b.CHUNKINGS),
                                                              "retrievers": list(A1b.RETRIEVERS)})
            n_npz = sum(1 for _ in path.glob("*/*.npz"))
            rep.check(f"{name}: run validation ({label})", True,
                      f"{len(run.datasets)} datasets, {n_npz} NPZ files; legacy: {len(run.legacy)} note(s)")
            for x in sorted(set(run.legacy)):
                rep.note(f"{name}: legacy limitation", x)
        except Exception as exc:  # noqa: BLE001
            rep.check(f"{name}: run validation ({label})", False, str(exc)[:400])
            continue
        qsets[name] = {d: (run.meta[d]["qids"], run.meta[d]["doc_idx"].tolist()) for d in run.datasets}
        if study == "1b":
            check_semantic_chunks(rep, name, path, run)
    for a, b in (("E1 confirmatory", "E3 confirmatory"), ("E1 pilot", "E3 pilot")):
        if a in qsets and b in qsets:
            same = all(qsets[a][d] == qsets[b][d] for d in DATASETS)
            rep.check(f"query lists identical: {a} vs {b}", same, "qids and doc_idx, all datasets")
    if "E1 pilot" in qsets and "E1 confirmatory" in qsets:
        for d in DATASETS:
            qa, da = qsets["E1 pilot"][d]
            qb, db = qsets["E1 confirmatory"][d]
            rep.check(f"no cross-split leakage: {d}", not (set(qa) & set(qb)) and not (set(da) & set(db)),
                      f"{len(qa)} exploratory / {len(qb)} confirmatory queries; documents disjoint")
    return qsets


def check_semantic_chunks(rep: Report, name: str, path: Path, run) -> None:
    for d in run.datasets:
        stats = {s["chunking"]: s for s in run.meta[d]["manifest"]["chunk_stats"]}
        for c in ("semantic-bp", "semantic-cl"):
            f = path / d / f"chunks_{c}.json.gz"
            try:
                obj = json.loads(gzip.decompress(f.read_bytes()))
                docs, ivs = obj["doc"], obj["intervals"]
                per_doc = defaultdict(list)
                bad = 0
                for doc, chunk in zip(docs, ivs):
                    words = sum(e - s for s, e in chunk)
                    if words <= 0 or words > 512 or any(e <= s for s, e in chunk) or chunk != sorted(chunk):
                        bad += 1
                    per_doc[doc].extend(tuple(x) for x in chunk)
                gaps = 0
                for doc, lst in per_doc.items():
                    lst.sort()
                    gaps += int(lst[0][0] != 0) + sum(1 for x, y in zip(lst, lst[1:]) if x[1] != y[0])
                ok = len(docs) == len(ivs) == stats[c]["n_chunks"] and bad == 0 and gaps == 0
                rep.check(f"{name}: {d}/{f.name}", ok, f"{len(ivs)} chunks (manifest {stats[c]['n_chunks']}); "
                          f"{bad} invalid chunks; {gaps} gaps/overlaps in the per-document word partition")
            except Exception as exc:  # noqa: BLE001
                rep.check(f"{name}: {d}/{f.name}", False, str(exc)[:300])


def check_generations(rep: Report, qsets: dict) -> None:
    conf = {d: set(qsets.get("E1 confirmatory", {}).get(d, ([], []))[0]) for d in DATASETS}
    for run in sorted((ROOT / E2_RUNS).iterdir()):
        if not run.is_dir():
            continue
        for d in DATASETS:
            ds = run / d
            if not ds.exists():
                continue
            try:
                scan = G.scan_run(ds, recover_tail=False)
                summ = G.summarize_rows(scan.rows, str(ds))
                meta = json.loads((ds / "jobs_meta.json").read_text())
                sample_ok = set(meta["qids"]) <= conf[d] and len(meta["qids"]) == len(set(meta["qids"]))
                c = summ["counts"]
                detail = (f"{scan.raw_lines} lines, {c['complete']} ok, {c['accepted']} accepted, {c['superseded']} "
                          f"superseded, {c['duplicate_ok']} duplicate ok; sample of {len(meta['qids'])} confirmatory "
                          f"queries: {'yes' if sample_ok else 'NO'}")
                ok = sample_ok and c["duplicate_ok"] == 0
                if run.name == ANALYSED_E2:
                    ok = ok and c["accepted"] == meta["n_jobs"] == 400
                rep.check(f"E2 {run.name}/{d}: generations log", ok, detail)
            except Exception as exc:  # noqa: BLE001
                rep.check(f"E2 {run.name}/{d}: generations log", False, str(exc)[:300])


def check_misc(rep: Report) -> None:
    for f in sorted(ROOT.glob("experiments/**/UPLOAD_SHA256")):
        txt = f.read_text().strip()
        rep.check(f"{f.relative_to(ROOT)}", bool(re.fullmatch(r"[0-9a-f]{64}", txt)),
                  "one SHA-256 of an upload archive that is not in the repository (cannot be re-verified here)")
    for f in sorted(ROOT.glob("experiments/**/*.log.gz")):
        try:
            n = len(gzip.decompress(f.read_bytes()).splitlines())
            rep.check(f"{f.relative_to(ROOT)}: gzip", True, f"{n} lines")
        except Exception as exc:  # noqa: BLE001
            rep.check(f"{f.relative_to(ROOT)}: gzip", False, str(exc))
    for f in sorted(ROOT.glob("experiments/*/analysis/*/results.json")):
        try:
            res = json.loads(f.read_text())
            rep.check(f"{f.relative_to(ROOT)}: parses", True, f"label: {str(res.get('label'))[:60]}")
        except Exception as exc:  # noqa: BLE001
            rep.check(f"{f.relative_to(ROOT)}: parses", False, str(exc))
    for f in sorted(ROOT.glob("experiments/**/*.log")):
        rep.note(f"{f.relative_to(ROOT)}", f"{len(f.read_text().splitlines())} line(s)")
    prot = ROOT / "docs" / "repair" / "PROTECTED_SHA256.txt"
    if prot.exists():
        bad = []
        n = 0
        for line in prot.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            digest, rel = line.split(None, 1)
            n += 1
            p = ROOT / rel.strip()
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                bad.append(rel.strip())
        rep.check("protected files match docs/repair/PROTECTED_SHA256.txt", not bad,
                  f"{n} files; mismatches: {bad[:5]}")


def check_with_data(rep: Report, data_root: Path, qsets: dict) -> None:
    from ragmv import data as D
    from ragmv.fetch import verify_consumed

    for d in DATASETS:
        try:
            verify_consumed(d, data_root)
            rep.check(f"data: {d} input digests", True, "every file the loader reads matches data/MANIFEST.yaml")
        except Exception as exc:  # noqa: BLE001
            rep.check(f"data: {d} input digests", False, str(exc)[:300])
            continue
        docs, queries = D.load(d, data_root)
        ids = [q.qid for q in queries]
        mask = D.split_documents(len(docs))
        rep.check(f"data: {d} unique query IDs", len(ids) == len(set(ids)), f"{len(ids)} queries, {len(docs)} documents")
        m = json.loads((ROOT / RUNS["E1 confirmatory"][0] / d / "manifest.json").read_text())
        exp = [q for q in queries if mask[q.doc_idx]]
        con = [q for q in queries if not mask[q.doc_idx]]
        rep.check(f"data: {d} counts match manifests", m["n_documents"] == len(docs) and m["n_queries"] == len(con)
                  and m["n_documents_exploratory"] == int(mask.sum()),
                  f"documents {len(docs)}, exploratory docs {int(mask.sum())}, confirmatory queries {len(con)}")
        for name, sel in (("E1 pilot", exp), ("E1 confirmatory", con)):
            if name in qsets:
                rep.check(f"data: {d} deterministic split reproduces {name} query list",
                          qsets[name][d] == ([q.qid for q in sel], [q.doc_idx for q in sel]), f"{len(sel)} queries")
        bad = sum(1 for q in queries for s, e in q.gold if not (0 <= s < e <= docs[q.doc_idx].n_words))
        rep.check(f"data: {d} gold spans inside documents", bad == 0 and all(q.gold for q in queries),
                  f"{sum(len(q.gold) for q in queries)} word spans")
        for name in ("E3 pilot", "E3 confirmatory"):
            for c in ("semantic-bp", "semantic-cl"):
                f = ROOT / RUNS[name][0] / d / f"chunks_{c}.json.gz"
                obj = json.loads(gzip.decompress(f.read_bytes()))
                ends = defaultdict(int)
                for doc, chunk in zip(obj["doc"], obj["intervals"]):
                    ends[doc] = max(ends[doc], max(e for _, e in chunk))
                full = all(ends.get(i, 0) == doc.n_words for i, doc in enumerate(docs) if doc.n_words)
                rep.check(f"data: {name} {d} {c} covers every word of every document", full, f"{len(docs)} documents")
    check_tier2_against_data(rep, data_root)


def check_tier2_against_data(rep: Report, data_root: Path) -> None:
    from ragmv import data as D

    run = ROOT / E2_RUNS / ANALYSED_E2
    e1 = ROOT / RUNS["E1 confirmatory"][0]
    for d in DATASETS:
        docs, queries = D.load(d, data_root)
        sample = G.sample_queries(queries, D.split_documents(len(docs)), 50)
        jobs = {j["job_id"]: j for j in G.build_jobs(docs, sample)}
        rows = G.summarize_rows(G.scan_run(run / d).rows)["accepted_rows"]
        meta = json.loads((run / d / "jobs_meta.json").read_text())
        cfg = json.loads((e1 / d / "manifest.json").read_text())["config"]
        qids = json.loads((e1 / d / "queries.json").read_text())["qids"]
        r_idx = cfg["retrievers"].index(G.RETRIEVER)
        op_idx = {"count5": cfg["ops"].index("k5"), "budget1024": cfg["ops"].index("B1024")}
        arrays = {c: np.load(e1 / d / f"{c}.npz", allow_pickle=False)["scores"] for c in G.CHUNKINGS}
        mism = {"prompt": 0, "retrieval_vs_E1": 0, "retrieval_vs_rebuilt": 0, "em": 0, "f1": 0, "answers": 0}
        for r in rows:
            j = jobs[r["job_id"]]
            mism["prompt"] += r["prompt_sha256"] != j["prompt_sha256"]
            mism["answers"] += r["answers"] != j["answers"]
            stored = arrays[r["chunking"]][r_idx, qids.index(r["qid"]), op_idx[r["op"]]]
            mism["retrieval_vs_E1"] += not np.allclose([float(x) for x in stored], list(r["retrieval"].values()), atol=1e-3)
            mism["retrieval_vs_rebuilt"] += r["retrieval"] != j["retrieval"]
            mism["em"] += G.exact_match(r["response"], r["answers"]) != r["em"]
            mism["f1"] += abs(G.token_f1(r["response"], r["answers"]) - r["f1"]) > 1e-12
        ok = not any(mism.values()) and [q.qid for q in sample] == meta["qids"] and len(rows) == len(jobs)
        rep.check(f"data: E2 {ANALYSED_E2}/{d} rebuilt from data", ok,
                  f"{len(rows)} rows; sample equals jobs_meta: {[q.qid for q in sample] == meta['qids']}; mismatches {mism}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root")
    ap.add_argument("--report")
    args = ap.parse_args(argv)
    rep = Report()
    qsets = check_runs(rep)
    check_generations(rep, qsets)
    check_misc(rep)
    if args.data_root:
        check_with_data(rep, Path(args.data_root), qsets)
    else:
        rep.note("data-dependent checks", "not run (no --data-root)")
    md = rep.markdown()
    if args.report:
        Path(args.report).write_text(md)
    print(md)
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
